import numpy as np
from sentence_transformers import SentenceTransformer

from src.ingestion.chunker import build_chunks


MODEL_NAME = "all-MiniLM-L6-v2"


class SemanticRetriever:
    """Simple in-memory semantic retrieval system."""

    def __init__(self):
        self.model = SentenceTransformer(MODEL_NAME)
        self.chunks = build_chunks()

        self.texts = [
            self._content_to_text(chunk["content"])
            for chunk in self.chunks
        ]

        self.embeddings = self.model.encode(
            self.texts,
            normalize_embeddings=True
        )

    @staticmethod
    def _content_to_text(content) -> str:
        """Convert structured records into searchable text."""

        if isinstance(content, dict):
            return " | ".join(
                f"{key}: {value}"
                for key, value in content.items()
            )

        return str(content)

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """Return the most semantically similar chunks."""

        query_embedding = self.model.encode(
            [query],
            normalize_embeddings=True
        )[0]

        scores = np.dot(
            self.embeddings,
            query_embedding
        )

        ranked_indices = np.argsort(scores)[::-1][:top_k]

        results = []

        for index in ranked_indices:
            chunk = self.chunks[index].copy()

            chunk["score"] = float(scores[index])

            results.append(chunk)

        return results


if __name__ == "__main__":

    retriever = SemanticRetriever()

    test_queries = [
        "How many quotations are required for a large purchase?",
        "What did Nakawa quote for Portland cement?",
        "Which supplier is excluded?",
        "How much Portland cement is currently in stock?",
    ]

    for query in test_queries:

        print("\n" + "=" * 70)
        print("QUERY:", query)
        print("=" * 70)

        results = retriever.search(query, top_k=3)

        for rank, result in enumerate(results, start=1):

            print(f"\nRank {rank}")
            print("Score:", round(result["score"], 4))
            print("Source:", result["source"])
            print("Type:", result["document_type"])
            print("Metadata:", result["metadata"])

            preview = str(result["content"]).replace("\n", " ")

            print("Content:", preview[:500])