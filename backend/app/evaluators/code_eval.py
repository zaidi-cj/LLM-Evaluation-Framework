import re
import ast
import traceback
from typing import Dict, Any, Optional, List
from app.evaluators.base import BaseEvaluator

class CodeEvaluator(BaseEvaluator):
    """
    Evaluates generated Python code by verifying syntax correctness and
    running functional unit tests specified in the test metadata.
    """

    def _clean_code(self, code: str) -> str:
        """
        Removes markdown formatting and fetches raw code.
        """
        # Find matches for ```python ... ```
        match = re.search(r"```(?:python)?\s*(.*?)\s*```", code, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return code.strip()

    def evaluate(
        self,
        input_query: str,
        generated_output: str,
        expected_output: Optional[str] = None,
        context_references: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Evaluates Python code:
            - syntax_valid: 1.0 if compiles, 0.0 otherwise.
            - unit_tests_pass_rate: percentage of passing unit tests (0.0 to 1.0).
        """
        clean_code = self._clean_code(generated_output)
        
        if not clean_code:
            return {"syntax_valid": 0.0, "unit_tests_pass_rate": 0.0}

        # Step 1: Syntax validation using AST
        try:
            ast.parse(clean_code)
            syntax_valid = 1.0
        except SyntaxError:
            return {"syntax_valid": 0.0, "unit_tests_pass_rate": 0.0}

        # Step 2: Extract unit tests from metadata
        # Expecting metadata format: { "entrypoint": "add_numbers", "unit_tests": [ {"input": [1, 2], "output": 3} ] }
        test_meta = {}
        if metadata and "entrypoint" in metadata:
            test_meta = metadata
        elif metadata and "test_metadata" in metadata and isinstance(metadata["test_metadata"], dict):
            test_meta = metadata["test_metadata"]

        entrypoint = test_meta.get("entrypoint")
        unit_tests = test_meta.get("unit_tests")

        # If no unit tests are provided, we can only evaluate syntax
        if not entrypoint or not unit_tests or not isinstance(unit_tests, list):
            return {"syntax_valid": 1.0, "unit_tests_pass_rate": 1.0}

        # Step 3: Execute in an isolated subprocess with a timeout to protect against infinite loops
        import subprocess
        import json
        import sys

        wrapper_template = """
import json
import sys

# 1. Inject the user code
try:
USER_CODE_PLACEHOLDER
except Exception as e:
    print(json.dumps({"error": f"Definition runtime exception: {type(e).__name__}: {str(e)}"}))
    sys.exit(0)

# 2. Extract and invoke target function
try:
    target_func = locals().get(ENTRYPOINT_PLACEHOLDER) or globals().get(ENTRYPOINT_PLACEHOLDER)
    if not target_func or not callable(target_func):
        print(json.dumps({"error": "Entrypoint function not found or not callable"}))
        sys.exit(0)
except Exception as e:
    print(json.dumps({"error": f"Error resolving function: {type(e).__name__}: {str(e)}"}))
    sys.exit(0)

# 3. Execute unit tests
passed_tests = 0
unit_tests = UNIT_TESTS_PLACEHOLDER
total_tests = len(unit_tests)

for test in unit_tests:
    inputs = test.get("input", [])
    expected = test.get("output")
    try:
        if isinstance(inputs, list):
            actual = target_func(*inputs)
        elif isinstance(inputs, dict):
            actual = target_func(**inputs)
        else:
            actual = target_func(inputs)
        if actual == expected:
            passed_tests += 1
    except Exception:
        continue

print(json.dumps({"passed": passed_tests, "total": total_tests}))
"""

        indented_code = "\n".join("    " + line for line in clean_code.splitlines())
        wrapper_script = (
            wrapper_template.replace("USER_CODE_PLACEHOLDER", indented_code)
            .replace("ENTRYPOINT_PLACEHOLDER", repr(entrypoint))
            .replace("UNIT_TESTS_PLACEHOLDER", repr(unit_tests))
        )

        try:
            result = subprocess.run(
                [sys.executable, "-c", wrapper_script],
                capture_output=True,
                text=True,
                timeout=2.0
            )
            
            if result.returncode != 0:
                err_msg = result.stderr.strip() or f"Process exited with code {result.returncode}"
                return {
                    "syntax_valid": syntax_valid,
                    "unit_tests_pass_rate": 0.0,
                    "error": f"Execution crashed: {err_msg}"
                }
                
            output_str = result.stdout.strip()
            if not output_str:
                err_msg = result.stderr.strip() or "No output from test execution process"
                return {
                    "syntax_valid": syntax_valid,
                    "unit_tests_pass_rate": 0.0,
                    "error": err_msg
                }

            # Parse JSON results from stdout
            lines = output_str.split("\n")
            res_dict = None
            for line in reversed(lines):
                if line.strip().startswith("{") and line.strip().endswith("}"):
                    try:
                        res_dict = json.loads(line)
                        break
                    except json.JSONDecodeError:
                        continue
                        
            if not res_dict:
                return {
                    "syntax_valid": syntax_valid,
                    "unit_tests_pass_rate": 0.0,
                    "error": f"Invalid execution output format: {output_str}"
                }
                
            if "error" in res_dict:
                return {
                    "syntax_valid": syntax_valid,
                    "unit_tests_pass_rate": 0.0,
                    "error": res_dict["error"]
                }
                
            passed = res_dict.get("passed", 0)
            total = res_dict.get("total", 0)
            pass_rate = (passed / total) if total > 0 else 1.0
            
            return {
                "syntax_valid": syntax_valid,
                "unit_tests_pass_rate": pass_rate
            }

        except subprocess.TimeoutExpired:
            return {
                "syntax_valid": syntax_valid,
                "unit_tests_pass_rate": 0.0,
                "error": "Execution timed out (exceeded 2.0s limit)"
            }
        except Exception as e:
            return {
                "syntax_valid": syntax_valid,
                "unit_tests_pass_rate": 0.0,
                "error": f"Execution subprocess error: {str(e)}"
            }

