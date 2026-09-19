import json
import tempfile
import unittest
from pathlib import Path

from src.rag.answer import REFUSAL, answer_query, build_context
from src.rag.retrieve import retrieve


class FakeRouter:
    def search(self, query, top_k):
        return {
            "route": "semantic",
            "results": [
                {
                    "content": "Approval requires officer review.",
                    "source": "knowledge/policy/procurement-policy.md",
                    "metadata": {"category": "procurement_policy"},
                    "score": 0.91,
                },
                {
                    "content": "Unrelated low-score result.",
                    "source": "knowledge/other.md",
                    "metadata": {},
                    "score": 0.12,
                },
            ][:top_k],
        }


class Week3RagTests(unittest.TestCase):
    def test_retrieve_applies_threshold_and_writes_trace(self):
        with tempfile.TemporaryDirectory() as directory:
            trace_path = Path(directory) / "retrieval.jsonl"
            results = retrieve(
                "Who approves?",
                k=5,
                threshold=0.35,
                router=FakeRouter(),
                trace_path=trace_path,
            )

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["score"], 0.91)
            self.assertEqual(results[0]["source_id"], "knowledge/policy/procurement-policy.md")
            trace = json.loads(trace_path.read_text(encoding="utf-8"))
            self.assertEqual(trace["query"], "Who approves?")
            self.assertEqual(trace["chunks"][0]["score"], 0.91)
            self.assertEqual(trace["prompt_version"], "policy-qa/v1.0")

    def test_context_contains_source_and_score(self):
        context = build_context([{
            "source_id": "knowledge/policy/procurement-policy.md",
            "score": 0.91,
            "content": "Approval requires officer review.",
        }])
        self.assertIn("DOC_ID: knowledge/policy/procurement-policy.md", context)
        self.assertIn("SCORE: 0.9100", context)

    def test_answer_refuses_without_evidence_or_model_call(self):
        model_called = False

        def model(_prompt):
            nonlocal model_called
            model_called = True
            return {"answer": "should not be used", "citations": []}

        result = answer_query("Unknown question", retriever=lambda query, **kwargs: [], model=model)
        self.assertEqual(result["answer"], REFUSAL)
        self.assertEqual(result["citations"], [])
        self.assertFalse(model_called)

    def test_answer_returns_only_retrieved_citations(self):
        chunks = [{
            "source_id": "knowledge/policy/procurement-policy.md",
            "score": 0.91,
            "content": "Approval requires officer review.",
        }]

        result = answer_query(
            "Who approves?",
            retriever=lambda query, **kwargs: chunks,
            model=lambda prompt: {
                "answer": "An officer reviews the request.",
                "citations": ["knowledge/policy/procurement-policy.md", "made-up.md"],
            },
        )
        self.assertEqual(result["answer"], "An officer reviews the request.")
        self.assertEqual(result["citations"], ["knowledge/policy/procurement-policy.md"])


if __name__ == "__main__":
    unittest.main()