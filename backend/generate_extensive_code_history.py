import os
import sys
from datetime import datetime, timedelta

# Setup path to import backend app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure SQLite database file
os.environ["DATABASE_URL"] = "sqlite:///./llm_eval.db"

from app.core.database import SessionLocal, engine, Base
from app.models.models import Project, TestCase, ModelConfiguration, EvaluationRun, EvaluationResult

def generate_code_history():
    print("Initializing SQLite database connection...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        print("Creating project 'Python Code Generation Benchmarks'...")
        # 1. Create CODE Project
        project = Project(
            name="Python Code Generation Benchmarks",
            description="Evaluating syntactic correctness and functional unit test pass rates for python helper scripts.",
            benchmark_type="CODE"
        )
        db.add(project)
        db.commit()
        db.refresh(project)

        # 2. Define 10 Coding Problems with Unit Tests in test_metadata
        print("Inserting 10 extensive coding test cases...")
        problems = [
            ("Write a function add_numbers(a, b) that returns the sum.", "def add_numbers(a, b):\n    return a + b", "add_numbers", [{"input": [1, 2], "output": 3}, {"input": [5, -5], "output": 0}]),
            ("Write a function is_palindrome(s) that checks if a string is a palindrome.", "def is_palindrome(s):\n    clean = ''.join(c.lower() for c in s if c.isalnum())\n    return clean == clean[::-1]", "is_palindrome", [{"input": ["racecar"], "output": True}, {"input": ["hello"], "output": False}]),
            ("Write a function fizzbuzz(n) that returns 'Fizz' if divisible by 3, 'Buzz' if by 5, 'FizzBuzz' if by 15, else string n.", "def fizzbuzz(n):\n    if n % 15 == 0: return 'FizzBuzz'\n    if n % 3 == 0: return 'Fizz'\n    if n % 5 == 0: return 'Buzz'\n    return str(n)", "fizzbuzz", [{"input": [3], "output": "Fizz"}, {"input": [5], "output": "Buzz"}, {"input": [15], "output": "FizzBuzz"}, {"input": [7], "output": "7"}]),
            ("Write a function reverse_string(s) that reverses a string.", "def reverse_string(s):\n    return s[::-1]", "reverse_string", [{"input": ["cat"], "output": "tac"}, {"input": ["abcd"], "output": "dcba"}]),
            ("Write a function is_even(n) that returns True if even, else False.", "def is_even(n):\n    return n % 2 == 0", "is_even", [{"input": [4], "output": True}, {"input": [7], "output": False}]),
            ("Write a function get_max(arr) that returns the maximum number in a list.", "def get_max(arr):\n    return max(arr) if arr else None", "get_max", [{"input": [[1, 5, 3]], "output": 5}, {"input": [[-2, -5]], "output": -2}]),
            ("Write a function count_vowels(s) that returns count of vowels in string s.", "def count_vowels(s):\n    return sum(1 for c in s.lower() if c in 'aeiou')", "count_vowels", [{"input": ["Hello"], "output": 2}, {"input": ["Sky"], "output": 0}]),
            ("Write a function factorial(n) that returns n factorial.", "def factorial(n):\n    if n <= 1: return 1\n    return n * factorial(n - 1)", "factorial", [{"input": [4], "output": 24}, {"input": [0], "output": 1}]),
            ("Write a function sum_list(arr) that returns the sum of array values.", "def sum_list(arr):\n    return sum(arr)", "sum_list", [{"input": [[1, 2, 3]], "output": 6}, {"input": [[]], "output": 0}]),
            ("Write a function is_prime(n) that returns True if prime, else False.", "def is_prime(n):\n    if n <= 1: return False\n    for i in range(2, int(n**0.5) + 1):\n        if n % i == 0: return False\n    return True", "is_prime", [{"input": [5], "output": True}, {"input": [4], "output": False}])
        ]

        test_cases = []
        for q, exp, entry, tests in problems:
            tc = TestCase(
                project_id=project.id,
                input_query=q,
                expected_output=exp,
                test_metadata={
                    "entrypoint": entry,
                    "unit_tests": tests
                }
            )
            db.add(tc)
            test_cases.append(tc)
        db.commit()

        for tc in test_cases:
            db.refresh(tc)

        # 3. Define 5 Completed Runs over the last 5 days
        print("Generating 5 completed code evaluation runs...")
        run_configs = [
            ("openai/gpt-3.5-turbo", 0.2, 5, {
                "syntax_valid": [1.0, 0.0, 1.0, 1.0, 1.0, 1.0, 0.0, 1.0, 1.0, 1.0], # 2 failed syntax compile
                "unit_tests_pass_rate": [1.0, 0.0, 0.5, 1.0, 1.0, 0.5, 0.0, 1.0, 1.0, 0.5],
                "latency": 1.1, "cost": 0.0015, "prompt_tok": 110, "comp_tok": 45
            }),
            ("ollama/llama3-8b", 0.0, 4, {
                "syntax_valid": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 1.0, 1.0, 1.0],
                "unit_tests_pass_rate": [1.0, 0.5, 0.75, 1.0, 1.0, 0.5, 0.0, 1.0, 1.0, 0.0],
                "latency": 0.8, "cost": 0.0, "prompt_tok": 110, "comp_tok": 48
            }),
            ("gemini/gemini-1.5-flash", 0.0, 3, {
                "syntax_valid": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
                "unit_tests_pass_rate": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.5, 1.0, 1.0, 0.5],
                "latency": 0.7, "cost": 0.0003, "prompt_tok": 110, "comp_tok": 40
            }),
            ("openai/gpt-4o", 0.0, 2, {
                "syntax_valid": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
                "unit_tests_pass_rate": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0], # 100% pass!
                "latency": 1.3, "cost": 0.006, "prompt_tok": 110, "comp_tok": 50
            }),
            # The latest code runner has a regression on factorial (recursion error) and is_prime (incorrect logic)!
            ("anthropic/claude-3-5-sonnet", 0.1, 1, {
                "syntax_valid": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
                "unit_tests_pass_rate": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 1.0, 0.0], # Factorial and IsPrime failed!
                "latency": 1.6, "cost": 0.010, "prompt_tok": 115, "comp_tok": 52
            })
        ]

        for model, temp, days_ago, scores in run_configs:
            # Create ModelConfig
            mc = ModelConfiguration(
                model_name=model,
                temperature=temp,
                system_prompt="Implement the requested python function. Only return python code in blocks."
            )
            db.add(mc)
            db.commit()
            db.refresh(mc)

            # Create Run
            run_date = datetime.utcnow() - timedelta(days=days_ago)
            run = EvaluationRun(
                project_id=project.id,
                model_config_id=mc.id,
                status="COMPLETED",
                created_at=run_date
            )
            db.add(run)
            db.commit()
            db.refresh(run)

            # Insert Results
            run_prompt_tokens = 0
            run_completion_tokens = 0
            run_cost = 0.0
            run_latency = 0.0

            syntax_list = scores["syntax_valid"]
            pass_list = scores["unit_tests_pass_rate"]

            for idx, tc in enumerate(test_cases):
                s_score = syntax_list[idx]
                p_score = pass_list[idx]

                # Generate mock response
                mock_out = f"```python\n{tc.expected_output}\n```"
                if s_score < 0.5:
                    mock_out = f"```python\ndef {tc.test_metadata['entrypoint']}(" # truncated syntax error
                elif p_score < 0.5:
                    mock_out = f"```python\ndef {tc.test_metadata['entrypoint']}(*args):\n    return 'wrong answer'\n```"

                res = EvaluationResult(
                    run_id=run.id,
                    test_case_id=tc.id,
                    generated_output=mock_out,
                    latency_seconds=scores["latency"],
                    token_usage={
                        "prompt_tokens": scores["prompt_tok"],
                        "completion_tokens": scores["comp_tok"],
                        "total_cost": scores["cost"]
                    },
                    metric_scores={
                        "syntax_valid": s_score,
                        "unit_tests_pass_rate": p_score
                    },
                    created_at=run_date
                )
                db.add(res)
                
                run_prompt_tokens += scores["prompt_tok"]
                run_completion_tokens += scores["comp_tok"]
                run_cost += scores["cost"]
                run_latency += scores["latency"]

            db.commit()

            # Update run summary statistics
            avg_syntax = round(sum(syntax_list) / len(syntax_list), 4)
            avg_pass = round(sum(pass_list) / len(pass_list), 4)
            avg_latency = round(run_latency / len(test_cases), 4)

            run.summary_stats = {
                "avg_latency": avg_latency,
                "total_cost": round(run_cost, 6),
                "total_prompt_tokens": run_prompt_tokens,
                "total_completion_tokens": run_completion_tokens,
                "avg_scores": {
                    "syntax_valid": avg_syntax,
                    "unit_tests_pass_rate": avg_pass
                },
                "success_rate": 1.0
            }
            db.commit()

        print("\nSeed script execution: ALL HISTORICAL CODE DATA POPULATED SUCCESSFULLY!")
        print(f"Project ID: {project.id}")
        print("Navigate to http://localhost:8000/dashboard to see the complete trend analysis!")

    except Exception as e:
        print(f"Error during seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    generate_code_history()
