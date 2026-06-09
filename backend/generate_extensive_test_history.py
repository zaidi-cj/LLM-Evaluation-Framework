import os
import sys
import uuid
from datetime import datetime, timedelta

# Setup path to import backend app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure SQLite database file
os.environ["DATABASE_URL"] = "sqlite:///./llm_eval.db"

from app.core.database import SessionLocal, engine, Base
from app.models.models import Project, TestCase, ModelConfiguration, EvaluationRun, EvaluationResult

def generate_history():
    print("Initializing SQLite database connection...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        print("Creating project 'Enterprise RAG Benchmarks'...")
        # 1. Create RAG Project
        project = Project(
            name="Enterprise RAG Benchmarks",
            description="Evaluating customer support knowledge retrieval across prompt versions.",
            benchmark_type="RAG"
        )
        db.add(project)
        db.commit()
        db.refresh(project)

        # 2. Define 10 Test Cases
        print("Inserting 10 extensive RAG test cases...")
        queries = [
            ("How do I request a billing refund?", "To request a refund, go to Settings > Billing and click 'Request Refund'. Requests are processed in 3-5 days.", ["Refund policy states all requests under 30 days are eligible. Go to Settings > Billing.", "Refund processing takes 3 to 5 business days."]),
            ("What is the maximum upload limit?", "The maximum file upload limit is 50MB per file for free accounts, and 2GB for premium accounts.", ["Free accounts are capped at 50MB uploads.", "Premium subscribers can upload up to 2GB files."]),
            ("Does the platform support offline mode?", "Yes, the mobile app supports offline syncing, which uploads changes once a network is found.", ["Mobile app offline mode caches writes locally.", "Offline sync uploads changes automatically when reconnected."]),
            ("How do I invite teammates to my workspace?", "Go to Workspace Settings > Members and enter their email addresses to send invitations.", ["Workspace administrators can invite members via Workspace Settings > Members.", "Invitations are sent via email."]),
            ("Is multi-factor authentication (MFA) available?", "Yes, MFA can be enabled in Security Settings via Google Authenticator or SMS.", ["MFA is available for all tiers.", "MFA setup is located under Security Settings. Supports authenticator apps and SMS."]),
            ("What payment methods are supported?", "We support Visa, Mastercard, American Express, PayPal, and Apple Pay.", ["Supported payment options: credit cards (Visa/MC/Amex), Paypal, Apple Pay.", "Debit cards are accepted under credit networks."]),
            ("How do I delete my account?", "To delete your account, navigate to Account Settings > Account Management and select 'Delete Account'. This action is permanent.", ["Account deletion is permanent.", "Find 'Delete Account' under Account Settings > Account Management."]),
            ("Can I export my project data?", "Yes, you can export projects as JSON or CSV files from the Project settings page.", ["Export options: JSON, CSV.", "Go to Project settings > Export Data to generate download."]),
            ("Does the system have a REST API?", "Yes, developer documentation and API keys are available in the Developer Portal.", ["REST API is fully supported.", "Generate API keys in Developer Portal under API Keys."]),
            ("What is the SLA for enterprise support?", "Enterprise tier includes a 99.9% uptime guarantee and a 1-hour response SLA for critical tickets.", ["Enterprise SLA guarantees 99.9% uptime.", "Support tickets under Enterprise tier receive replies within 1 hour for high-priority items."])
        ]

        test_cases = []
        for i, (q, exp, ctx) in enumerate(queries):
            tc = TestCase(
                project_id=project.id,
                input_query=q,
                expected_output=exp,
                context_references=ctx
            )
            db.add(tc)
            test_cases.append(tc)
        db.commit()
        
        # Refresh test cases to get IDs
        for tc in test_cases:
            db.refresh(tc)

        # 3. Create 5 Completed Runs over the last 5 days
        print("Generating 5 completed evaluation runs...")
        run_configs = [
            ("openai/gpt-4o-mini", 0.2, 5, {
                "faithfulness": [0.80, 0.78, 0.82, 0.75, 0.80, 0.78, 0.77, 0.81, 0.79, 0.80],
                "answer_relevance": [0.82, 0.80, 0.85, 0.79, 0.81, 0.83, 0.80, 0.84, 0.82, 0.83],
                "latency": 1.2, "cost": 0.002, "prompt_tok": 120, "comp_tok": 60
            }),
            ("gemini/gemini-1.5-flash", 0.0, 4, {
                "faithfulness": [0.83, 0.81, 0.85, 0.79, 0.84, 0.82, 0.81, 0.86, 0.82, 0.83],
                "answer_relevance": [0.85, 0.83, 0.87, 0.82, 0.84, 0.86, 0.83, 0.87, 0.85, 0.86],
                "latency": 0.9, "cost": 0.0004, "prompt_tok": 120, "comp_tok": 58
            }),
            ("anthropic/claude-3-5-sonnet", 0.1, 3, {
                "faithfulness": [0.92, 0.90, 0.94, 0.88, 0.93, 0.91, 0.90, 0.95, 0.92, 0.93],
                "answer_relevance": [0.94, 0.92, 0.96, 0.90, 0.93, 0.95, 0.92, 0.97, 0.94, 0.95],
                "latency": 1.8, "cost": 0.012, "prompt_tok": 125, "comp_tok": 65
            }),
            ("openai/gpt-4o", 0.0, 2, {
                "faithfulness": [0.89, 0.87, 0.91, 0.85, 0.90, 0.88, 0.87, 0.92, 0.89, 0.90],
                "answer_relevance": [0.91, 0.89, 0.93, 0.87, 0.90, 0.92, 0.89, 0.94, 0.91, 0.92],
                "latency": 1.4, "cost": 0.008, "prompt_tok": 120, "comp_tok": 62
            }),
            # The latest run has a PROMPT REGRESSION on case 1 and case 7!
            ("openai/gpt-4o-mini-v2", 0.2, 1, {
                "faithfulness": [0.55, 0.80, 0.83, 0.78, 0.81, 0.79, 0.52, 0.82, 0.80, 0.81], # Cases 0 and 6 regressed heavily!
                "answer_relevance": [0.84, 0.82, 0.86, 0.81, 0.83, 0.85, 0.82, 0.85, 0.83, 0.84],
                "latency": 1.0, "cost": 0.0018, "prompt_tok": 122, "comp_tok": 60
            })
        ]

        for model, temp, days_ago, scores in run_configs:
            # Create ModelConfig
            mc = ModelConfiguration(
                model_name=model,
                temperature=temp,
                system_prompt="Analyze contexts and write an answer."
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

            faith_list = scores["faithfulness"]
            relev_list = scores["answer_relevance"]

            for idx, tc in enumerate(test_cases):
                f_score = faith_list[idx]
                r_score = relev_list[idx]

                # Generate mock response
                mock_out = f"Mocked answer for: '{tc.input_query}' matching expected '{tc.expected_output[:20]}...'"
                if f_score < 0.6:
                    mock_out = "This is a hallucinated response containing unrelated facts."

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
                        "faithfulness": f_score,
                        "answer_relevance": r_score
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
            avg_faith = round(sum(faith_list) / len(faith_list), 4)
            avg_relev = round(sum(relev_list) / len(relev_list), 4)
            avg_latency = round(run_latency / len(test_cases), 4)

            run.summary_stats = {
                "avg_latency": avg_latency,
                "total_cost": round(run_cost, 6),
                "total_prompt_tokens": run_prompt_tokens,
                "total_completion_tokens": run_completion_tokens,
                "avg_scores": {
                    "faithfulness": avg_faith,
                    "answer_relevance": avg_relev
                },
                "success_rate": 1.0
            }
            db.commit()

        print("\nSeed script execution: ALL HISTORICAL DATA POPULATED SUCCESSFULLY!")
        print(f"Project ID: {project.id}")
        print("Navigate to http://localhost:8000/dashboard to see the complete trend analysis!")

    except Exception as e:
        print(f"Error during seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    generate_history()
