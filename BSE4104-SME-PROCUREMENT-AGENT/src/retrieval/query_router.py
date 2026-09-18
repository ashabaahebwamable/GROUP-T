import re
from src.retrieval.semantic_search import SemanticRetriever
from src.retrieval.structured_lookup import StructuredLookup


class QueryRouter:
    """
    Routes procurement questions to the appropriate retrieval mechanism.

    Semantic retrieval is used for policy and document questions.
    Structured lookup is used for exact procurement records.
    """

    def __init__(self):
        self.semantic_retriever = SemanticRetriever()
        self.structured_lookup = StructuredLookup()

    def route(self, query: str) -> str:
        """
        Decide which retrieval mechanism should handle the query.
        """

        query_lower = query.lower()
        query_upper = query.upper()

        # ---------------------------------------------------------
        # 1. Explicit record IDs always use structured lookup.
        # ---------------------------------------------------------
        if any(identifier in query_upper for identifier in [
            "INV-",
            "SUP-",
            "QUO-",
            "REQ-"
        ]):
            return "structured"

        # ---------------------------------------------------------
        # 2. Questions about current records use structured lookup.
        # ---------------------------------------------------------
        structured_keywords = [
            "current stock",
            "inventory record",
            "supplier record",
            "quotation record",
            "quotation price",
            "unit price",
            "requisition record",
        ]

        if any(keyword in query_lower for keyword in structured_keywords):
            return "structured"

        # ---------------------------------------------------------
        # 3. Everything else goes to semantic retrieval.
        # ---------------------------------------------------------
        return "semantic"

    def search(self, query: str, top_k: int = 5):
        """
        Route the query and perform the appropriate retrieval.
        """

        route = self.route(query)
        query_upper = query.upper()

        # ---------------------------------------------------------
        # Semantic retrieval
        # ---------------------------------------------------------
        if route == "semantic":

            results = self.semantic_retriever.search(
                query,
                top_k=top_k
            )

            return {
                "route": "semantic",
                "results": results
            }

        # ---------------------------------------------------------
        # Structured retrieval
        # ---------------------------------------------------------

        # Inventory
        inventory_match = re.search(r"INV-\d+", query_upper)

        if inventory_match:
            item_id = inventory_match.group()

            result = self.structured_lookup.get_inventory_item(item_id)

            return {
                "route": "structured",
                "results": [result] if result else []
            }

        # Supplier
        supplier_match = re.search(r"SUP-\d+", query_upper)

        if supplier_match:
            supplier_id = supplier_match.group()

            result = self.structured_lookup.get_supplier(supplier_id)

            return {
                "route": "structured",
                "results": [result] if result else []
            }

        # Quotation
        quotation_match = re.search(r"QUO-\d+", query_upper)

        if quotation_match:
            quotation_id = quotation_match.group()

            result = self.structured_lookup.get_quotation(quotation_id)

            return {
                "route": "structured",
                "results": [result] if result else []
            }

        # Requisition
        requisition_match = re.search(r"REQ-[A-Z0-9-]+", query_upper)

        if requisition_match:
            requisition_id = requisition_match.group()

            result = self.structured_lookup.get_requisition(
                requisition_id
            )

            return {
                "route": "structured",
                "results": [result] if result else []
            }

        return {
            "route": "structured",
            "results": []
        }


if __name__ == "__main__":

    router = QueryRouter()

    test_queries = [
        "How many quotations are required for a large purchase?",
        "What is the status of SUP-05?",
        "What is the current stock of INV-001?",
        "What did QUO-1001 quote?",
        "What are the approval thresholds?",
        "What does the policy say about excluded suppliers?",
    ]

    for query in test_queries:

        print("\n" + "=" * 70)
        print("QUERY:", query)
        print("=" * 70)

        result = router.search(query)

        print("ROUTE:", result["route"])
        print("RESULT COUNT:", len(result["results"]))

        for rank, item in enumerate(result["results"], start=1):

            print(f"\nResult {rank}")
            print("Source:", item["source"])
            print("Type:", item["document_type"])
            print("Metadata:", item["metadata"])
            print("Content:", str(item["content"])[:500])