import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.orm import Session
from app.models.models import EvaluationRun, TestCase, EvaluationResult
from app.services.llm_client import call_target_model
from app.evaluators import get_evaluator
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)

def run_benchmark(run_id: str, db: Session):
    """
    Executes a benchmark run in parallel using a thread pool.
    Calls models, runs evaluators, and writes results concurrently.
    """
    logger.info(f"Starting concurrent benchmark run: {run_id}")
    
    # 1. Fetch Run information
    run = db.query(EvaluationRun).filter(EvaluationRun.id == run_id).first()
    if not run:
        logger.error(f"Run {run_id} not found in database.")
        return
        
    run.status = "RUNNING"
    db.commit()

    try:
        project = run.project
        model_config = run.model_config
        
        # 2. Fetch all test case IDs
        test_cases = db.query(TestCase).filter(TestCase.project_id == project.id).all()
        if not test_cases:
            raise ValueError("No test cases found in this project to evaluate.")

        # 3. Instantiate appropriate evaluator
        evaluator = get_evaluator(project.benchmark_type)
        logger.info(f"Using evaluator: {evaluator.__class__.__name__} for type: {project.benchmark_type}")

        # Extract IDs to process in parallel
        case_ids = [c.id for c in test_cases]

        # 4. Define Thread Worker Function
        def process_case(case_id: str):
            thread_db = SessionLocal()
            try:
                # Fetch case inside thread session
                case = thread_db.query(TestCase).filter(TestCase.id == case_id).first()
                if not case:
                    return None

                prompt = case.input_query
                system_prompt = model_config.system_prompt
                
                # Execute target model call
                response = call_target_model(
                    model_name=model_config.model_name,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=model_config.temperature,
                    parameters=model_config.parameters
                )

                if response.error_message:
                    result = EvaluationResult(
                        run_id=run_id,
                        test_case_id=case_id,
                        generated_output=None,
                        latency_seconds=response.latency_seconds,
                        error_message=response.error_message,
                        metric_scores={}
                    )
                    thread_db.add(result)
                    thread_db.commit()
                    return {
                        "latency": response.latency_seconds,
                        "cost": 0.0,
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "scores": {},
                        "success": False
                    }

                # Run evaluator
                scores = evaluator.evaluate(
                    input_query=case.input_query,
                    generated_output=response.text,
                    expected_output=case.expected_output,
                    context_references=case.context_references,
                    metadata=case.test_metadata
                )

                # Save individual result
                result = EvaluationResult(
                    run_id=run_id,
                    test_case_id=case_id,
                    generated_output=response.text,
                    latency_seconds=response.latency_seconds,
                    token_usage={
                        "prompt_tokens": response.prompt_tokens,
                        "completion_tokens": response.completion_tokens,
                        "total_cost": response.cost_usd
                    },
                    metric_scores=scores
                )
                thread_db.add(result)
                thread_db.commit()

                return {
                    "latency": response.latency_seconds,
                    "cost": response.cost_usd,
                    "prompt_tokens": response.prompt_tokens,
                    "completion_tokens": response.completion_tokens,
                    "scores": scores,
                    "success": True
                }

            except Exception as case_err:
                logger.error(f"Error evaluating test case {case_id}: {str(case_err)}", exc_info=True)
                try:
                    result = EvaluationResult(
                        run_id=run_id,
                        test_case_id=case_id,
                        error_message=str(case_err),
                        metric_scores={}
                    )
                    thread_db.add(result)
                    thread_db.commit()
                except Exception:
                    pass
                return None
            finally:
                thread_db.close()

        # 5. Run parallel thread pool (e.g. max 10 concurrent requests to prevent rate limit issues)
        max_workers = min(10, len(case_ids))
        logger.info(f"Executing {len(case_ids)} test cases concurrently with {max_workers} threads.")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            thread_results = list(executor.map(process_case, case_ids))

        # 6. Aggregate results in main thread
        total_latency = 0.0
        total_cost = 0.0
        total_prompt_tokens = 0
        total_completion_tokens = 0
        metric_sums = {}
        metric_counts = {}
        success_count = 0
        total_count = 0

        for res in thread_results:
            if not res:
                continue
            total_count += 1
            total_latency += res["latency"]
            total_cost += res["cost"]
            total_prompt_tokens += res["prompt_tokens"]
            total_completion_tokens += res["completion_tokens"]
            
            if res["success"]:
                success_count += 1
                for metric, val in res["scores"].items():
                    metric_sums[metric] = metric_sums.get(metric, 0.0) + val
                    metric_counts[metric] = metric_counts.get(metric, 0) + 1

        # Compute averages
        avg_scores = {}
        for metric, total_val in metric_sums.items():
            count = metric_counts[metric]
            avg_scores[metric] = round(total_val / count, 4) if count > 0 else 0.0

        avg_latency = round(total_latency / total_count, 4) if total_count > 0 else 0.0
        
        run.summary_stats = {
            "avg_latency": avg_latency,
            "total_cost": round(total_cost, 6),
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "avg_scores": avg_scores,
            "success_rate": round(success_count / len(test_cases), 4) if len(test_cases) > 0 else 0.0
        }
        run.status = "COMPLETED"
        db.commit()
        logger.info(f"Concurrent benchmark run {run_id} completed successfully.")

    except Exception as e:
        logger.error(f"Benchmark run {run_id} failed: {str(e)}", exc_info=True)
        run.status = "FAILED"
        run.error_message = str(e)
        db.commit()
