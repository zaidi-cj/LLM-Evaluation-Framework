from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

class BaseEvaluator(ABC):
    """
    Abstract Base Class for all LLM evaluators.
    """
    @abstractmethod
    def evaluate(
        self,
        input_query: str,
        generated_output: str,
        expected_output: Optional[str] = None,
        context_references: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Executes evaluation for a single test case.
        Returns a dictionary of metrics mapping metric name to score (usually float between 0.0 and 1.0).
        """
        pass
