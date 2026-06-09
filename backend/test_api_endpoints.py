import os
import sys
from fastapi.testclient import TestClient

# Setup path to import backend app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Force SQLite test database in environment
os.environ["DATABASE_URL"] = "sqlite:///./test_api_endpoints.db"

from app.main import app
from app.core.database import Base, engine

client = TestClient(app)

def setup_database():
    print("Recreating database tables for API tests...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

def test_api_workflow():
    setup_database()

    print("\n--- Testing API Endpoints Workflow ---")
    
    # 1. Create a Project
    print("1. Testing POST /projects...")
    proj_payload = {
        "name": "API Test Project",
        "description": "Integration test check",
        "benchmark_type": "SQL"
    }
    response = client.post("/projects", json=proj_payload)
    assert response.status_code == 201, f"Failed: {response.text}"
    project = response.json()
    project_id = project["id"]
    print(f"   Project created: {project_id}")
    assert project["name"] == "API Test Project"
    assert project["benchmark_type"] == "SQL"

    # 2. Get Projects List
    print("2. Testing GET /projects...")
    response = client.get("/projects")
    assert response.status_code == 200
    projects = response.json()
    assert len(projects) >= 1
    print(f"   Found {len(projects)} projects.")

    # 3. Batch Create Test Cases
    print("3. Testing POST /projects/{id}/testcases/batch...")
    ddl = "CREATE TABLE employees (id INT, name TEXT);"
    test_cases_payload = [
        {
            "input_query": "Select Alice",
            "expected_output": "SELECT * FROM employees WHERE name = 'Alice';",
            "test_metadata": {"schema_ddl": ddl}
        },
        {
            "input_query": "Select all employees",
            "expected_output": "SELECT * FROM employees;",
            "test_metadata": {"schema_ddl": ddl}
        }
    ]
    response = client.post(f"/projects/{project_id}/testcases/batch", json=test_cases_payload)
    assert response.status_code == 201, f"Failed: {response.text}"
    cases = response.json()
    assert len(cases) == 2
    print(f"   Successfully uploaded {len(cases)} test cases.")

    # 4. Trigger an Evaluation Run
    print("4. Testing POST /projects/{id}/runs...")
    run_payload = {
        "model_config": {
            "model_name": "mock/gpt-4o",
            "temperature": 0.0,
            "system_prompt": "You are a SQL writer.",
            "parameters": {}
        }
    }
    response = client.post(f"/projects/{project_id}/runs", json=run_payload)
    assert response.status_code == 202, f"Failed: {response.text}"
    run = response.json()
    run_id = run["id"]
    print(f"   Run triggered: {run_id} (Status: {run['status']})")
    assert run["status"] == "PENDING"
    # Verify the nested model configuration was correctly returned in the alias 'model_config'
    assert "model_config" in run, "Alias 'model_config' should be present in response JSON"
    assert run["model_config"]["model_name"] == "mock/gpt-4o"

    # 5. Get Runs List
    print("5. Testing GET /projects/{id}/runs...")
    response = client.get(f"/projects/{project_id}/runs")
    assert response.status_code == 200
    runs = response.json()
    assert len(runs) >= 1
    print(f"   Found {len(runs)} runs for project.")
    assert runs[0]["id"] == run_id

    # 6. Fetch Specific Run Detail
    print("6. Testing GET /runs/{run_id}...")
    response = client.get(f"/runs/{run_id}")
    assert response.status_code == 200
    run_detail = response.json()
    assert run_detail["id"] == run_id
    assert run_detail["model_config"]["model_name"] == "mock/gpt-4o"

    # 7. Fetch Drift Stats (should return empty list since run has not finished or no COMPLETED runs exist yet)
    print("7. Testing GET /projects/{id}/drift...")
    response = client.get(f"/projects/{project_id}/drift")
    assert response.status_code == 200
    drift = response.json()
    print(f"   Drift records found: {len(drift)}")

    # 8. Fetch Regressions (should return empty list since no baseline run exists)
    print("8. Testing GET /projects/{id}/regressions...")
    response = client.get(f"/projects/{project_id}/regressions?run_id={run_id}")
    assert response.status_code == 200
    regressions = response.json()
    print(f"   Regression alerts found: {len(regressions)}")

    print("\n--- ALL API ENDPOINTS VERIFIED & STABLE ---")

if __name__ == "__main__":
    try:
        test_api_workflow()
    except AssertionError as e:
        print(f"\nAssertion Error occurred: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected Error occurred: {e}")
        sys.exit(1)
