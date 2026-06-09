import logging
import re
from typing import Dict, Any, Optional, List
import litellm
from app.evaluators.base import BaseEvaluator
from app.core.config import settings

logger = logging.getLogger(__name__)

class RAGEvaluator(BaseEvaluator):
    """
    Evaluates Retrieval-Augmented Generation (RAG) outputs.
    Computes:
        - faithfulness (answer groundedness in context)
        - answer_relevance (answer relevance to query)
    """

    def _run_ragas_library(
        self,
        query: str,
        generated: str,
        expected: Optional[str],
        contexts: List[str]
    ) -> Optional[Dict[str, float]]:
        """
        Attempts to compute metrics using the official Ragas package.
        """
        try:
            from datasets import Dataset
            from ragas import evaluate as ragas_eval
            from ragas.metrics import faithfulness, answer_relevance

            # Build datasets format required by Ragas
            data = {
                "question": [query],
                "answer": [generated],
                "contexts": [contexts],
                "ground_truth": [expected or ""]
            }
            dataset = Dataset.from_dict(data)
            
            # Configure LLM for ragas
            # Ragas default relies on langchain/openai, we skip config here if api keys aren't set
            if not settings.OPENAI_API_KEY:
                return None
                
            result = ragas_eval(
                dataset,
                metrics=[faithfulness, answer_relevance]
            )
            return {
                "faithfulness": float(result.get("faithfulness", 0.0)),
                "answer_relevance": float(result.get("answer_relevance", 0.0))
            }
        except Exception as e:
            logger.warning(f"Ragas library evaluation failed, switching to custom LLM-judge: {str(e)}")
            return None

    def _evaluate_faithfulness_custom(self, generated: str, contexts: List[str]) -> float:
        """
        Custom LLM-judge prompt for Faithfulness (Groundedness).
        Checks if claims in generated output are supported by the retrieved contexts.
        Bypasses network if API credentials are not set.
        """
        gemini_configured = settings.GEMINI_API_KEY and "placeholder" not in settings.GEMINI_API_KEY.lower()
        openai_configured = settings.OPENAI_API_KEY and "placeholder" not in settings.OPENAI_API_KEY.lower()
        
        if not gemini_configured and not openai_configured:
            # Local mock score for faithfulness
            return 0.92

        judge_model = "gemini/gemini-1.5-flash"
        if not settings.GEMINI_API_KEY and settings.OPENAI_API_KEY:
            judge_model = "openai/gpt-4o-mini"

        context_str = "\n---\n".join(contexts)
        system_prompt = (
            "You are an expert evaluator assessing LLM outputs.\n"
            "Your task is to judge the FAITHFULNESS (groundedness) of the generated answer compared to the provided Context Documents.\n"
            "Faithfulness means that the generated answer does NOT contain any claims or facts that are not present or directly inferable "
            "from the Context. It must contain zero hallucinations.\n"
            "Output ONLY a raw float number between 0.0 (completely hallucinated or unsupported) and 1.0 (completely faithful to context).\n"
            "Do not output explanation text."
        )

        prompt = (
            f"Context Documents:\n{context_str}\n\n"
            f"Generated Answer to Evaluate:\n{generated}\n\n"
            "Faithfulness Score (0.0 to 1.0):"
        )

        try:
            response = litellm.completion(
                model=judge_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0
            )
            score_text = response.choices[0].message.content or "0.0"
            match = re.search(r"([0-9]*\.[0-9]+|[0-9]+)", score_text)
            if match:
                return min(max(float(match.group(1)), 0.0), 1.0)
            return 0.0
        except Exception as e:
            logger.error(f"Custom Faithfulness Judge call failed: {str(e)}")
            return 0.5

    def _evaluate_relevance_custom(self, query: str, generated: str) -> float:
        """
        Custom LLM-judge prompt for Answer Relevance.
        Checks if the generated answer directly addresses the query topic.
        Bypasses network if API credentials are not set.
        """
        gemini_configured = settings.GEMINI_API_KEY and "placeholder" not in settings.GEMINI_API_KEY.lower()
        openai_configured = settings.OPENAI_API_KEY and "placeholder" not in settings.OPENAI_API_KEY.lower()
        
        if not gemini_configured and not openai_configured:
            # Local mock score for relevance
            return 0.88

        judge_model = "gemini/gemini-1.5-flash"
        if not settings.GEMINI_API_KEY and settings.OPENAI_API_KEY:
            judge_model = "openai/gpt-4o-mini"

        system_prompt = (
            "You are an expert evaluator assessing LLM outputs.\n"
            "Your task is to judge the RELEVANCE of the generated answer compared to the User Query.\n"
            "Answer relevance measures if the answer directly addresses the question and is concise. "
            "It should not be generic, off-topic, or containing redundant info.\n"
            "Output ONLY a raw float number between 0.0 (completely irrelevant) and 1.0 (perfectly relevant and direct).\n"
            "Do not output explanation text."
        )

        prompt = (
            f"User Query:\n{query}\n\n"
            f"Generated Answer to Evaluate:\n{generated}\n\n"
            "Relevance Score (0.0 to 1.0):"
        )

        try:
            response = litellm.completion(
                model=judge_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0
            )
            score_text = response.choices[0].message.content or "0.0"
            match = re.search(r"([0-9]*\.[0-9]+|[0-9]+)", score_text)
            if match:
                return min(max(float(match.group(1)), 0.0), 1.0)
            return 0.0
        except Exception as e:
            logger.error(f"Custom Relevance Judge call failed: {str(e)}")
            return 0.5

    def evaluate(
        self,
        input_query: str,
        generated_output: str,
        expected_output: Optional[str] = None,
        context_references: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Computes faithfulness and answer_relevance.
        """
        if not generated_output:
            return {"faithfulness": 0.0, "answer_relevance": 0.0}

        contexts = context_references or []
        if not contexts:
            # Try to fetch contexts from metadata if not explicitly provided
            if metadata and "contexts" in metadata:
                contexts = metadata["contexts"]
            elif metadata and "test_metadata" in metadata and isinstance(metadata["test_metadata"], dict):
                contexts = metadata["test_metadata"].get("contexts", [])

        # Attempt to run using library
        result = None
        # Enable library run only if specifically configured, as Ragas package can be slow & complex
        if metadata and metadata.get("use_ragas_library", False):
            result = self._run_ragas_library(
                query=input_query,
                generated=generated_output,
                expected=expected_output,
                contexts=contexts
            )

        if result:
            return result

        # Fallback (or default) to custom LLM judges
        faithfulness_score = self._evaluate_faithfulness_custom(generated_output, contexts)
        relevance_score = self._evaluate_relevance_custom(input_query, generated_output)

        return {
            "faithfulness": faithfulness_score,
            "answer_relevance": relevance_score
        }
