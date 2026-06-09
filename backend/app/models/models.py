import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    benchmark_type = Column(String(50), nullable=False)  # RAG, SQL, CODE, SUMMARIZATION, GENERAL
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    test_cases = relationship("TestCase", back_populates="project", cascade="all, delete-orphan")
    runs = relationship("EvaluationRun", back_populates="project", cascade="all, delete-orphan")

class TestCase(Base):
    __tablename__ = "test_cases"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    input_query = Column(Text, nullable=False)
    expected_output = Column(Text, nullable=True)
    context_references = Column(JSON, nullable=True)  # List of strings/contexts for RAG
    test_metadata = Column(JSON, nullable=True)  # Config like DB schema structure, inputs, unit tests, etc.
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="test_cases")
    results = relationship("EvaluationResult", back_populates="test_case", cascade="all, delete-orphan")

class ModelConfiguration(Base):
    __tablename__ = "model_configurations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    model_name = Column(String(255), nullable=False)  # e.g. openai/gpt-4o, gemini/gemini-1.5-pro, anthropic/claude-3-5-sonnet
    temperature = Column(Float, default=0.0)
    system_prompt = Column(Text, nullable=True)
    parameters = Column(JSON, nullable=True)  # max_tokens, top_p, etc.
    created_at = Column(DateTime, default=datetime.utcnow)

    runs = relationship("EvaluationRun", back_populates="model_config")

class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    model_config_id = Column(String(36), ForeignKey("model_configurations.id"), nullable=False)
    status = Column(String(50), default="PENDING")  # PENDING, RUNNING, COMPLETED, FAILED
    summary_stats = Column(JSON, nullable=True)  # { "avg_latency": 1.2, "avg_cost": 0.02, "avg_accuracy": 0.85, ... }
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="runs")
    model_config = relationship("ModelConfiguration", back_populates="runs")
    results = relationship("EvaluationResult", back_populates="run", cascade="all, delete-orphan")

class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    run_id = Column(String(36), ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False)
    test_case_id = Column(String(36), ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False)
    generated_output = Column(Text, nullable=True)
    latency_seconds = Column(Float, nullable=True)
    token_usage = Column(JSON, nullable=True)  # { "prompt_tokens": 100, "completion_tokens": 50, "total_cost": 0.003 }
    metric_scores = Column(JSON, nullable=True)  # { "faithfulness": 0.95, "accuracy": 1.0, ... }
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    run = relationship("EvaluationRun", back_populates="results")
    test_case = relationship("TestCase", back_populates="results")
