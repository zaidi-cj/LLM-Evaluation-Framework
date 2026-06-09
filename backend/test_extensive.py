import os
import sys
import time
from fastapi.testclient import TestClient

# Setup path to import backend app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Force separate SQLite database in environment for extensive testing
os.environ["DATABASE_URL"] = "sqlite:///./test_extensive.db"

from app.main import app
from app.core.database import Base, engine, SessionLocal
from app.evaluators.code_eval import CodeEvaluator
from app.evaluators.sql_eval import SQLEvaluator
from app.evaluators.judge_eval import JudgeEvaluator
from app.evaluators.rag_eval import RAGEvaluator
from app.models.models import Project, TestCase, ModelConfiguration, EvaluationRun, EvaluationResult
from app.services.runner import run_benchmark
from unittest.mock import patch
from app.services.llm_client import LLMCallResponse

def test_code_evaluator_edge_cases():
    print("\n--- Testing CodeEvaluator Subprocess Sandboxing & Edge Cases ---")
    evaluator = CodeEvaluator()
    
    meta = {
        "entrypoint": "add",
        "unit_tests": [
            {"input": [1, 2], "output": 3},
            {"input": [5, -5], "output": 0}
        ]
    }

    # 1. Correct code execution
    print("1. Running correct python code...")
    res = evaluator.evaluate(
        input_query="add numbers",
        generated_output="def add(a, b):\n    return a + b",
        metadata=meta
    )
    print(f"   Result: {res}")
    assert res["syntax_valid"] == 1.0
    assert res["unit_tests_pass_rate"] == 1.0

    # 2. Infinite Loop isolation & timeout validation
    print("2. Running code with an infinite loop (should timeout in ~2s)...")
    start_time = time.time()
    res = evaluator.evaluate(
        input_query="add numbers",
        generated_output="def add(a, b):\n    while True:\n        pass\n    return a + b",
        metadata=meta
    )
    elapsed = time.time() - start_time
    print(f"   Result: {res} (elapsed: {elapsed:.2f}s)")
    assert res["syntax_valid"] == 1.0
    assert res["unit_tests_pass_rate"] == 0.0
    assert "timed out" in res.get("error", "").lower() or "timeout" in res.get("error", "").lower()
    assert elapsed < 3.0, f"Expected timeout to interrupt run under 3 seconds, took {elapsed:.2f}s"

    # 3. Syntax error validation
    print("3. Running code with syntax error...")
    res = evaluator.evaluate(
        input_query="add numbers",
        generated_output="def add(a, b)\n    return a + b", # missing colon
        metadata=meta
    )
    print(f"   Result: {res}")
    assert res["syntax_valid"] == 0.0
    assert res["unit_tests_pass_rate"] == 0.0

    # 4. Definition runtime crash validation
    print("4. Running code that crashes on import/definition...")
    res = evaluator.evaluate(
        input_query="add numbers",
        generated_output="raise ValueError('Definition crash!')\ndef add(a, b):\n    return a + b",
        metadata=meta
    )
    print(f"   Result: {res}")
    assert res["syntax_valid"] == 1.0
    assert res["unit_tests_pass_rate"] == 0.0
    assert "definition crash" in res.get("error", "").lower()

    # 5. Invalid entrypoint check
    print("5. Running code with mismatched entrypoint name...")
    res = evaluator.evaluate(
        input_query="add numbers",
        generated_output="def subtract(a, b):\n    return a - b",
        metadata=meta
    )
    print(f"   Result: {res}")
    assert res["syntax_valid"] == 1.0
    assert res["unit_tests_pass_rate"] == 0.0
    assert "entrypoint" in res.get("error", "").lower()

def test_sql_evaluator_edge_cases():
    print("\n--- Testing SQLEvaluator Sandbox & Edge Cases ---")
    evaluator = SQLEvaluator()
    
    schema = """
    CREATE TABLE products (id INT, name TEXT, price INT);
    INSERT INTO products VALUES (1, 'Laptop', 1200), (2, 'Mouse', 20), (3, 'Keyboard', 80);
    """

    # 1. Standard sorting comparison
    print("1. Testing correct SQL results (order-independent)...")
    res = evaluator.evaluate(
        input_query="Get products",
        generated_output="SELECT name FROM products WHERE price > 50;",
        expected_output="SELECT name FROM products WHERE price > 50;",
        metadata={"schema_ddl": schema}
    )
    print(f"   Result: {res}")
    assert res["sql_valid"] == 1.0
    assert res["execution_correctness"] == 1.0

    # 2. SQL Syntax error compilation validation
    print("2. Testing malformed SQL query...")
    res = evaluator.evaluate(
        input_query="Get products",
        generated_output="SELECT name FROM FROM products WHERE price > 50;",
        expected_output="SELECT name FROM products WHERE price > 50;",
        metadata={"schema_ddl": schema}
    )
    print(f"   Result: {res}")
    assert res["sql_valid"] == 0.0
    assert res["execution_correctness"] == 0.0

    # 3. Column/Data mismatch
    print("3. Testing SQL query returning different column counts...")
    res = evaluator.evaluate(
        input_query="Get products",
        generated_output="SELECT id, name FROM products WHERE price > 50;",
        expected_output="SELECT name FROM products WHERE price > 50;",
        metadata={"schema_ddl": schema}
    )
    print(f"   Result: {res}")
    assert res["sql_valid"] == 1.0
    assert res["execution_correctness"] == 0.0

    # 4. Strict sorting with ORDER BY clause
    print("4. Testing ORDER BY strict ordering (correct order)...")
    res = evaluator.evaluate(
        input_query="Get sorted products",
        generated_output="SELECT name FROM products ORDER BY price ASC;",
        expected_output="SELECT name FROM products ORDER BY price ASC;",
        metadata={"schema_ddl": schema}
    )
    print(f"   Result: {res}")
    assert res["sql_valid"] == 1.0
    assert res["execution_correctness"] == 1.0

    print("5. Testing ORDER BY strict ordering (incorrect order)...")
    res = evaluator.evaluate(
        input_query="Get sorted products",
        generated_output="SELECT name FROM products ORDER BY price DESC;",
        expected_output="SELECT name FROM products ORDER BY price ASC;",
        metadata={"schema_ddl": schema}
    )
    print(f"   Result: {res}")
    assert res["sql_valid"] == 1.0
    assert res["execution_correctness"] == 0.0

def test_api_regression_drift_workflow():
    print("\n--- Testing API Endpoints & Regression Tracking Workflow ---")
    
    # Set up tables
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    client = TestClient(app)
    
    # 1. Create SQL Project
    proj_payload = {
        "name": "Production SQL helper",
        "description": "Enterprise db helper test",
        "benchmark_type": "SQL"
    }
    response = client.post("/projects", json=proj_payload)
    assert response.status_code == 201
    project = response.json()
    project_id = project["id"]
    print(f"   Project created: {project_id}")

    # 2. Batch Create 3 Test Cases
    schema_ddl = """
    CREATE TABLE staff (id INT, title TEXT);
    INSERT INTO staff VALUES (5, 'Manager'), (6, 'Developer');
    """
    test_cases_payload = [
        {
            "input_query": "Select managers",
            "expected_output": "SELECT id FROM staff WHERE title = 'Manager';",
            "test_metadata": {"schema_ddl": schema_ddl}
        },
        {
            "input_query": "Select all staff",
            "expected_output": "SELECT id FROM staff;",
            "test_metadata": {"schema_ddl": schema_ddl}
        },
        {
            "input_query": "Select staff by ID 5",
            "expected_output": "SELECT id FROM staff WHERE id = 5;",
            "test_metadata": {"schema_ddl": schema_ddl}
        }
    ]
    response = client.post(f"/projects/{project_id}/testcases/batch", json=test_cases_payload)
    assert response.status_code == 201
    cases = response.json()
    assert len(cases) == 3
    print(f"   Uploaded {len(cases)} test cases.")

    # We will trigger two runs: Run 1 (Baseline - 100% Correct) and Run 2 (Candidate - 33% Correct)

    # 3. Trigger Baseline Run (Run 1)
    run1_payload = {
        "model_config": {
            "model_name": "mock/gpt-4o",
            "temperature": 0.0,
            "system_prompt": "Always returns correct SQL answers"
        }
    }
    # Mock model calls to return correct SQL queries for all three cases
    def mock_baseline_responses(model_name, prompt=None, **kwargs):
        p = prompt or kwargs.get("prompt", "")
        print(f"[DEBUG mock_baseline] prompt: {p!r}")
        if "managers" in p:
            text = "SELECT id FROM staff WHERE title = 'Manager';"
        elif "all staff" in p:
            text = "SELECT id FROM staff;"
        else:
            text = "SELECT id FROM staff WHERE id = 5;"
        return LLMCallResponse(
            text=text,
            latency_seconds=0.5,
            prompt_tokens=10,
            completion_tokens=10,
            cost_usd=0.0001
        )

    with patch("app.services.runner.call_target_model", side_effect=mock_baseline_responses):
        response = client.post(f"/projects/{project_id}/runs", json=run1_payload)
    
    assert response.status_code == 202
    run1 = response.json()
    run1_id = run1["id"]
    print(f"   Baseline Run triggered: {run1_id}")

    # Verify Baseline Completed
    response = client.get(f"/runs/{run1_id}")
    assert response.status_code == 200
    run1_detail = response.json()
    assert run1_detail["status"] == "COMPLETED"
    print(f"   Baseline Run completed with stats: {run1_detail['summary_stats']}")
    assert run1_detail["summary_stats"]["avg_scores"]["execution_correctness"] == 1.0

    # 4. Trigger Candidate Run (Run 2) with a prompt regression (only 1 out of 3 correct)
    run2_payload = {
        "model_config": {
            "model_name": "mock/gpt-4o-v2",
            "temperature": 0.2,
            "system_prompt": "Always returns wrong SQL answers"
        }
    }
    # Mock model calls to return 2 INCORRECT queries and 1 CORRECT query deterministically
    def mock_candidate_responses(model_name, prompt=None, **kwargs):
        p = prompt or kwargs.get("prompt", "")
        print(f"[DEBUG mock_candidate] prompt: {p!r}")
        if "managers" in p:
            text = "SELECT id FROM staff WHERE title = 'Manager';" # Correct
        elif "all staff" in p:
            text = "SELECT name FROM staff;" # Incorrect column (sql_valid = 0)
        else:
            text = "SELECT id FROM staff WHERE id = 999;" # Incorrect ID (correctness = 0)
        return LLMCallResponse(
            text=text,
            latency_seconds=0.7,
            prompt_tokens=12,
            completion_tokens=12,
            cost_usd=0.00012
        )

    with patch("app.services.runner.call_target_model", side_effect=mock_candidate_responses):
        response = client.post(f"/projects/{project_id}/runs", json=run2_payload)
        
    assert response.status_code == 202
    run2 = response.json()
    run2_id = run2["id"]
    print(f"   Candidate Run triggered: {run2_id}")

    # Print database counts for debugging
    db = SessionLocal()
    print(f"[DEBUG DB] TestCases total: {db.query(TestCase).count()}")
    print(f"[DEBUG DB] Run 1 results: {db.query(EvaluationResult).filter(EvaluationResult.run_id == run1_id).count()}")
    print(f"[DEBUG DB] Run 2 results: {db.query(EvaluationResult).filter(EvaluationResult.run_id == run2_id).count()}")
    db.close()

    # Verify Candidate Completed
    response = client.get(f"/runs/{run2_id}")
    assert response.status_code == 200
    run2_detail = response.json()
    assert run2_detail["status"] == "COMPLETED"
    print(f"   Candidate Run completed with stats: {run2_detail['summary_stats']}")
    assert abs(run2_detail["summary_stats"]["avg_scores"]["execution_correctness"] - 0.3333) < 0.01

    # 5. Fetch Regressions - Should return 3 regression alerts:
    # - "Select all staff": sql_valid drop, execution_correctness drop
    # - "Select staff by ID 5": execution_correctness drop
    print("5. Verifying regression alerts endpoint...")
    response = client.get(f"/projects/{project_id}/regressions?run_id={run2_id}")
    assert response.status_code == 200
    regressions = response.json()
    print(f"   Regressions found: {regressions}")
    assert len(regressions) == 3, f"Expected 3 regression alerts, got {len(regressions)}"
    
    # Assert regression flags
    reg_queries = [reg["input_query"] for reg in regressions]
    assert "Select all staff" in reg_queries
    assert "Select staff by ID 5" in reg_queries
    assert "Select managers" not in reg_queries
    print("   -> Performance drop regressions successfully detected & validated!")

    # 6. Fetch Performance Drift
    print("6. Verifying performance drift endpoint...")
    response = client.get(f"/projects/{project_id}/drift")
    assert response.status_code == 200
    drift_data = response.json()
    print(f"   Drift records count: {len(drift_data)}")
    assert len(drift_data) == 2
    
    # Verify records sorted chronologically
    assert drift_data[0]["run_id"] == run1_id
    assert drift_data[1]["run_id"] == run2_id
    assert drift_data[0]["avg_scores"]["execution_correctness"] == 1.0
    assert abs(drift_data[1]["avg_scores"]["execution_correctness"] - 0.3333) < 0.01
    print("   -> Performance drift calculations successfully verified!")

if __name__ == "__main__":
    print("==================================================")
    print("   RUNNING CREATIVE & EXTENSIVE EVALUATOR TESTS   ")
    print("==================================================")
    
    # Execute Edge Cases
    test_code_evaluator_edge_cases()
    test_sql_evaluator_edge_cases()
    
    # Execute API end-to-end integration workflows
    test_api_regression_drift_workflow()
    
    print("\n==================================================")
    print("   ALL EXTENSIVE & CREATIVE TESTS PASSED! SUCCESS ")
    print("==================================================")
