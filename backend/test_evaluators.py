import os
import sys

# Setup path to import backend app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.evaluators.sql_eval import SQLEvaluator
from app.evaluators.code_eval import CodeEvaluator
from app.evaluators.judge_eval import JudgeEvaluator
from app.evaluators.rag_eval import RAGEvaluator

def test_sql_evaluator():
    print("Running SQLEvaluator tests...")
    evaluator = SQLEvaluator()
    
    schema = """
    CREATE TABLE employees (id INT, name TEXT, salary INT);
    INSERT INTO employees VALUES (1, 'Alice', 90000), (2, 'Bob', 80000);
    """
    
    expected = "SELECT name FROM employees WHERE salary > 85000;"
    
    # 1. Test exact correct query
    gen_correct = "SELECT name FROM employees WHERE salary > 85000"
    res1 = evaluator.evaluate(
        input_query="Get employees earning > 85k",
        generated_output=gen_correct,
        expected_output=expected,
        metadata={"schema_ddl": schema}
    )
    assert res1["sql_valid"] == 1.0, f"Expected valid SQL, got: {res1}"
    assert res1["execution_correctness"] == 1.0, f"Expected correctness to be 1.0, got: {res1}"
    print("  - Correct query test: PASSED")

    # 2. Test invalid syntax
    gen_invalid = "SELECT name FROM employees WHERE salary >>> 85000"
    res2 = evaluator.evaluate(
        input_query="Get employees earning > 85k",
        generated_output=gen_invalid,
        expected_output=expected,
        metadata={"schema_ddl": schema}
    )
    assert res2["sql_valid"] == 0.0, f"Expected invalid SQL, got: {res2}"
    assert res2["execution_correctness"] == 0.0, f"Expected correctness to be 0.0, got: {res2}"
    print("  - Invalid query test: PASSED")

    # 3. Test valid syntax but wrong data return
    gen_wrong_data = "SELECT name FROM employees WHERE salary < 85000"
    res3 = evaluator.evaluate(
        input_query="Get employees earning > 85k",
        generated_output=gen_wrong_data,
        expected_output=expected,
        metadata={"schema_ddl": schema}
    )
    assert res3["sql_valid"] == 1.0, f"Expected valid SQL, got: {res3}"
    assert res3["execution_correctness"] == 0.0, f"Expected correctness to be 0.0, got: {res3}"
    print("  - Incorrect result test: PASSED")

def test_code_evaluator():
    print("Running CodeEvaluator tests...")
    evaluator = CodeEvaluator()
    
    meta = {
        "entrypoint": "calculate_fizzbuzz",
        "unit_tests": [
            {"input": [3], "output": "Fizz"},
            {"input": [5], "output": "Buzz"},
            {"input": [15], "output": "FizzBuzz"},
            {"input": [7], "output": "7"}
        ]
    }
    
    # 1. Test correct implementation
    correct_code = """
def calculate_fizzbuzz(n):
    if n % 15 == 0:
        return "FizzBuzz"
    elif n % 3 == 0:
        return "Fizz"
    elif n % 5 == 0:
        return "Buzz"
    return str(n)
"""
    res1 = evaluator.evaluate(
        input_query="Write FizzBuzz",
        generated_output=correct_code,
        metadata=meta
    )
    assert res1["syntax_valid"] == 1.0, f"Expected syntax valid, got {res1}"
    assert res1["unit_tests_pass_rate"] == 1.0, f"Expected pass rate 1.0, got {res1}"
    print("  - Correct code implementation test: PASSED")

    # 2. Test syntax error
    bad_syntax_code = """
def calculate_fizzbuzz(n)
    return "Fizz"
"""
    res2 = evaluator.evaluate(
        input_query="Write FizzBuzz",
        generated_output=bad_syntax_code,
        metadata=meta
    )
    assert res2["syntax_valid"] == 0.0
    assert res2["unit_tests_pass_rate"] == 0.0
    print("  - Syntax error test: PASSED")

    # 3. Test partial pass (only 2 out of 4 passing)
    partial_code = """
def calculate_fizzbuzz(n):
    if n == 3: return "Fizz"
    if n == 5: return "Buzz"
    return "Something else"
"""
    res3 = evaluator.evaluate(
        input_query="Write FizzBuzz",
        generated_output=partial_code,
        metadata=meta
    )
    assert res3["syntax_valid"] == 1.0
    # 3 should return Fizz (pass), 5 returns Buzz (pass), 15 returns Something else (fail), 7 returns Something else (fail)
    assert res3["unit_tests_pass_rate"] == 0.5, f"Expected 0.5 pass rate, got {res3}"
    print("  - Partially correct code test: PASSED")

def test_judge_evaluator():
    print("Running JudgeEvaluator deterministic tests...")
    evaluator = JudgeEvaluator()
    
    # Test Exact Match normalization
    res = evaluator.evaluate(
        input_query="test query",
        generated_output="   Hello World!  ",
        expected_output="hello world!"
    )
    assert res["exact_match"] == 1.0, f"Expected exact match 1.0, got {res}"
    
    res2 = evaluator.evaluate(
        input_query="test query",
        generated_output="Hello World! different",
        expected_output="hello world!"
    )
    assert res2["exact_match"] == 0.0, f"Expected exact match 0.0, got {res2}"
    print("  - Exact match normalization test: PASSED")

if __name__ == "__main__":
    print("Starting LLM Eval Framework Unit Tests...")
    test_sql_evaluator()
    test_code_evaluator()
    test_judge_evaluator()
    print("All local unit tests completed successfully!")
