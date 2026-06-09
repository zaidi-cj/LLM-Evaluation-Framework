from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# ================= Project Schemas =================
class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    benchmark_type: str = Field(..., description="RAG, SQL, CODE, SUMMARIZATION, or GENERAL")

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class ProjectResponse(ProjectBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True

# ================= TestCase Schemas =================
class TestCaseBase(BaseModel):
    input_query: str
    expected_output: Optional[str] = None
    context_references: Optional[List[str]] = None
    test_metadata: Optional[Dict[str, Any]] = None

class TestCaseCreate(TestCaseBase):
    pass

class TestCaseUpdate(BaseModel):
    input_query: Optional[str] = None
    expected_output: Optional[str] = None
    context_references: Optional[List[str]] = None
    test_metadata: Optional[Dict[str, Any]] = None

class TestCaseResponse(TestCaseBase):
    id: str
    project_id: str
    created_at: datetime

    class Config:
        from_attributes = True

# ================= ModelConfiguration Schemas =================
class ModelConfigurationBase(BaseModel):
    model_name: str
    temperature: float = 0.0
    system_prompt: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None

class ModelConfigurationCreate(ModelConfigurationBase):
    pass

class ModelConfigurationResponse(ModelConfigurationBase):
    id: str
    created_at: datetime

    model_config = {
        "from_attributes": True
    }

# ================= EvaluationRun Schemas =================
class EvaluationRunCreate(BaseModel):
    model_configuration: ModelConfigurationCreate = Field(..., alias="model_config")

    model_config = {
        "populate_by_name": True
    }

class EvaluationRunResponse(BaseModel):
    id: str
    project_id: str
    model_configuration: ModelConfigurationResponse = Field(..., alias="model_config")
    status: str
    summary_stats: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }

# ================= EvaluationResult Schemas =================
class EvaluationResultResponse(BaseModel):
    id: str
    run_id: str
    test_case_id: str
    generated_output: Optional[str] = None
    latency_seconds: Optional[float] = None
    token_usage: Optional[Dict[str, Any]] = None
    metric_scores: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    test_case: Optional[TestCaseResponse] = None

    class Config:
        from_attributes = True

# ================= Custom Analytics Schemas =================
class RegressionAlert(BaseModel):
    metric_name: str
    previous_score: float
    current_score: float
    drop_percentage: float
    test_case_id: Optional[str] = None
    input_query: Optional[str] = None

class DriftStats(BaseModel):
    run_id: str
    created_at: datetime
    model_name: str
    avg_latency: float
    avg_cost: float
    avg_scores: Dict[str, float]
