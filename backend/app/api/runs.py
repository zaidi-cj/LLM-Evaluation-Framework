from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Dict, Any, Optional
from app.core.database import get_db
from app.models.models import EvaluationRun, ModelConfiguration, Project, EvaluationResult, TestCase
from app.schemas.schemas import (
    EvaluationRunCreate, EvaluationRunResponse, EvaluationResultResponse,
    RegressionAlert, DriftStats
)
from app.services.runner import run_benchmark

router = APIRouter(tags=["Runs & Analytics"])

@router.get("/projects/{project_id}/runs", response_model=List[EvaluationRunResponse])
def list_runs(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    return db.query(EvaluationRun).filter(EvaluationRun.project_id == project_id).order_by(desc(EvaluationRun.created_at)).all()

@router.post("/projects/{project_id}/runs", response_model=EvaluationRunResponse, status_code=status.HTTP_202_ACCEPTED)
def trigger_run(
    project_id: str,
    run_in: EvaluationRunCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
        
    test_cases_count = db.query(TestCase).filter(TestCase.project_id == project_id).count()
    if test_cases_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot trigger run on a project with 0 test cases."
        )

    # 1. Save Model Configuration
    model_conf = ModelConfiguration(
        model_name=run_in.model_configuration.model_name,
        temperature=run_in.model_configuration.temperature,
        system_prompt=run_in.model_configuration.system_prompt,
        parameters=run_in.model_configuration.parameters
    )
    db.add(model_conf)
    db.commit()
    db.refresh(model_conf)

    # 2. Create Evaluation Run
    eval_run = EvaluationRun(
        project_id=project_id,
        model_config_id=model_conf.id,
        status="PENDING"
    )
    db.add(eval_run)
    db.commit()
    db.refresh(eval_run)

    # 3. Queue Background Task
    background_tasks.add_task(run_benchmark, eval_run.id, db)

    return eval_run

@router.get("/runs/{run_id}", response_model=EvaluationRunResponse)
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = db.query(EvaluationRun).filter(EvaluationRun.id == run_id).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run with ID {run_id} not found"
        )
    return run

@router.get("/runs/{run_id}/results", response_model=List[EvaluationResultResponse])
def get_run_results(run_id: str, db: Session = Depends(get_db)):
    run = db.query(EvaluationRun).filter(EvaluationRun.id == run_id).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run with ID {run_id} not found"
        )
    return db.query(EvaluationResult).filter(EvaluationResult.run_id == run_id).all()

@router.get("/projects/{project_id}/drift", response_model=List[DriftStats])
def get_drift_analytics(project_id: str, db: Session = Depends(get_db)):
    """
    Returns historical summaries for successful runs to track metric performance drift.
    """
    runs = db.query(EvaluationRun).filter(
        EvaluationRun.project_id == project_id,
        EvaluationRun.status == "COMPLETED"
    ).order_by(EvaluationRun.created_at).all()
    
    analytics = []
    for r in runs:
        stats = r.summary_stats or {}
        analytics.append(DriftStats(
            run_id=r.id,
            created_at=r.created_at,
            model_name=r.model_config.model_name,
            avg_latency=stats.get("avg_latency", 0.0),
            avg_cost=stats.get("total_cost", 0.0),
            avg_scores=stats.get("avg_scores", {})
        ))
    return analytics

@router.get("/projects/{project_id}/regressions", response_model=List[RegressionAlert])
def get_run_regressions(
    project_id: str,
    run_id: str,
    compare_run_id: Optional[str] = None,
    threshold: float = 0.05,
    db: Session = Depends(get_db)
):
    """
    Identifies test cases that have suffered a metric performance drop compared to a past run.
    """
    # Verify current run exists
    current_run = db.query(EvaluationRun).filter(EvaluationRun.id == run_id).first()
    if not current_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Current Run with ID {run_id} not found"
        )
        
    # If no comparison run specified, select the immediate previous COMPLETED run in this project
    if not compare_run_id:
        prev_run = db.query(EvaluationRun).filter(
            EvaluationRun.project_id == project_id,
            EvaluationRun.status == "COMPLETED",
            EvaluationRun.created_at < current_run.created_at
        ).order_by(desc(EvaluationRun.created_at)).first()
    else:
        prev_run = db.query(EvaluationRun).filter(EvaluationRun.id == compare_run_id).first()

    if not prev_run:
        return [] # No baseline run to compare regressions against

    # Retrieve results for both runs
    curr_results = db.query(EvaluationResult).filter(EvaluationResult.run_id == current_run.id).all()
    prev_results = db.query(EvaluationResult).filter(EvaluationResult.run_id == prev_run.id).all()

    # Index baseline scores by TestCase ID
    prev_by_case = {res.test_case_id: res for res in prev_results}

    alerts = []
    for cur_res in curr_results:
        prev_res = prev_by_case.get(cur_res.test_case_id)
        if not prev_res or not cur_res.metric_scores or not prev_res.metric_scores:
            continue
            
        # Compare overlapping metric scores
        for metric, cur_val in cur_res.metric_scores.items():
            prev_val = prev_res.metric_scores.get(metric)
            if prev_val is None:
                continue
                
            diff = prev_val - cur_val
            if diff >= threshold:
                alerts.append(RegressionAlert(
                    metric_name=metric,
                    previous_score=round(prev_val, 4),
                    current_score=round(cur_val, 4),
                    drop_percentage=round(diff * 100, 2),
                    test_case_id=cur_res.test_case_id,
                    input_query=cur_res.test_case.input_query if cur_res.test_case else ""
                ))
                
    return alerts
