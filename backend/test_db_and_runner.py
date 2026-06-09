import os
import sys

# Setup path to import backend app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal, engine, Base
from app.models.models import Project, TestCase, ModelConfiguration, EvaluationRun, EvaluationResult
from app.services.runner import run_benchmark

def test_full_pipeline_mock():
    print("Initializing sandbox database tables...")
    # Clean recreate database for testing
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        print("Creating mock benchmark project, test cases, and model config...")
        # 1. Create SQL Project
        project = Project(
            name="SQL Data Retrieval Test",
            description="Testing employee lookup queries",
            benchmark_type="SQL"
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        
        # 2. Add Test Cases
        ddl = """
        CREATE TABLE users (id INT, name TEXT, role TEXT);
        INSERT INTO users VALUES (1, 'Alice', 'Admin'), (2, 'Bob', 'Member');
        """
        
        case1 = TestCase(
            project_id=project.id,
            input_query="Select name of admin users",
            expected_output="SELECT name FROM users WHERE role = 'Admin';",
            test_metadata={"schema_ddl": ddl}
        )
        case2 = TestCase(
            project_id=project.id,
            input_query="Select all user names",
            expected_output="SELECT name FROM users;",
            test_metadata={"schema_ddl": ddl}
        )
        db.add_all([case1, case2])
        db.commit()
        
        # 3. Create Model Configuration
        # We will configure a mock local model or mock response
        # Since LiteLLM might error out on real call if no key, let's mock call_target_model
        # using Python mock so we don't hit external APIs.
        from unittest.mock import patch
        from app.services.llm_client import LLMCallResponse
        
        model_conf = ModelConfiguration(
            model_name="mock/gpt-4o",
            temperature=0.0,
            system_prompt="Return queries."
        )
        db.add(model_conf)
        db.commit()
        db.refresh(model_conf)
        
        # 4. Create Evaluation Run
        run = EvaluationRun(
            project_id=project.id,
            model_config_id=model_conf.id,
            status="PENDING"
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        
        print(f"Mocking LLM client calls and triggering runner for Run ID: {run.id}...")
        
        # We mock target model response. For case 1, return a CORRECT query. For case 2, return an INCORRECT query.
        mock_calls = 0
        def mock_call_target(*args, **kwargs):
            nonlocal mock_calls
            mock_calls += 1
            if mock_calls == 1:
                # Correct response for Case 1
                return LLMCallResponse(
                    text="SELECT name FROM users WHERE role = 'Admin'",
                    latency_seconds=0.8,
                    prompt_tokens=15,
                    completion_tokens=10,
                    cost_usd=0.0001
                )
            else:
                # Incorrect response for Case 2 (returns salary column instead of name column, etc.)
                return LLMCallResponse(
                    text="SELECT id, role FROM users",
                    latency_seconds=1.2,
                    prompt_tokens=12,
                    completion_tokens=8,
                    cost_usd=0.00008
                )

        with patch("app.services.runner.call_target_model", side_effect=mock_call_target):
            run_benchmark(run.id, db)
            
        # 5. Verify database entries
        db.refresh(run)
        print("Verifying run outputs...")
        assert run.status == "COMPLETED", f"Expected COMPLETED, got {run.status}"
        assert run.summary_stats is not None, "Summary stats should be generated"
        
        stats = run.summary_stats
        print(f"  Summary stats generated: {stats}")
        assert stats["success_rate"] == 1.0  # both calls returned outputs (success counts)
        assert stats["total_prompt_tokens"] == 27
        assert stats["total_completion_tokens"] == 18
        assert abs(stats["avg_latency"] - 1.0) < 0.1  # (0.8 + 1.2) / 2 = 1.0s
        
        # Fetch results
        results = db.query(EvaluationResult).filter(EvaluationResult.run_id == run.id).all()
        assert len(results) == 2, f"Expected 2 results, got {len(results)}"
        
        # Index results by testcase id
        results_by_case = {res.test_case_id: res for res in results}
        
        # Check scores
        r1 = results_by_case.get(case1.id)  # Case 1 (Correct query)
        assert r1 is not None
        assert r1.metric_scores["sql_valid"] == 1.0
        assert r1.metric_scores["execution_correctness"] == 1.0
        print("  - Case 1 Correct SQL: Verification PASSED")
        
        r2 = results_by_case.get(case2.id)  # Case 2 (Incorrect SQL columns)
        assert r2 is not None
        assert r2.metric_scores["sql_valid"] == 1.0
        assert r2.metric_scores["execution_correctness"] == 0.0
        print("  - Case 2 Incorrect SQL columns: Verification PASSED")

        print("End-to-end pipeline verification: ALL PASSED")

    finally:
        db.close()

if __name__ == "__main__":
    test_full_pipeline_mock()
