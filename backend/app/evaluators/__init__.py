from app.evaluators.base import BaseEvaluator
from app.evaluators.sql_eval import SQLEvaluator
from app.evaluators.code_eval import CodeEvaluator
from app.evaluators.rag_eval import RAGEvaluator
from app.evaluators.judge_eval import JudgeEvaluator

_evaluators = {
    "RAG": RAGEvaluator(),
    "SQL": SQLEvaluator(),
    "CODE": CodeEvaluator(),
    "SUMMARIZATION": JudgeEvaluator(),
    "GENERAL": JudgeEvaluator()
}

def get_evaluator(benchmark_type: str) -> BaseEvaluator:
    """
    Returns the appropriate evaluator instance based on the project's benchmark type.
    """
    normalized_type = benchmark_type.strip().upper()
    return _evaluators.get(normalized_type, _evaluators["GENERAL"])
