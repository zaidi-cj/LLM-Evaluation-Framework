from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.models import TestCase, Project
from app.schemas.schemas import TestCaseCreate, TestCaseResponse

router = APIRouter(prefix="/projects/{project_id}/testcases", tags=["Test Cases"])

@router.get("", response_model=List[TestCaseResponse])
def list_test_cases(project_id: str, db: Session = Depends(get_db)):
    # Verify project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    return db.query(TestCase).filter(TestCase.project_id == project_id).all()

@router.post("", response_model=TestCaseResponse, status_code=status.HTTP_201_CREATED)
def create_test_case(project_id: str, test_case: TestCaseCreate, db: Session = Depends(get_db)):
    # Verify project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_444_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
        
    db_case = TestCase(
        project_id=project_id,
        input_query=test_case.input_query,
        expected_output=test_case.expected_output,
        context_references=test_case.context_references,
        test_metadata=test_case.test_metadata
    )
    db.add(db_case)
    db.commit()
    db.refresh(db_case)
    return db_case

@router.post("/batch", response_model=List[TestCaseResponse], status_code=status.HTTP_201_CREATED)
def batch_create_test_cases(project_id: str, test_cases: List[TestCaseCreate], db: Session = Depends(get_db)):
    """
    Uploads a batch of test cases for a project. Highly efficient for bulk benchmark sets.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
        
    db_cases = []
    for tc in test_cases:
        db_case = TestCase(
            project_id=project_id,
            input_query=tc.input_query,
            expected_output=tc.expected_output,
            context_references=tc.context_references,
            test_metadata=tc.test_metadata
        )
        db.add(db_case)
        db_cases.append(db_case)
        
    db.commit()
    for db_case in db_cases:
        db.refresh(db_case)
        
    return db_cases
