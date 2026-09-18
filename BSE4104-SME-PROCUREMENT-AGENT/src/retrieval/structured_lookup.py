from src.ingestion.loader import load_knowledge_base


class StructuredLookup:
    """Deterministic lookup over structured procurement records."""

    def __init__(self):
        documents = load_knowledge_base()

        self.inventory = {}
        self.suppliers = {}
        self.quotations = {}
        self.requisitions = {}

        for document in documents:

            document_type = document["document_type"]
            metadata = document["metadata"]
            content = document["content"]

            if document_type == "inventory":
                item_id = metadata.get("item_id")

                if item_id:
                    self.inventory[item_id] = document

            elif document_type == "supplier":
                supplier_id = metadata.get("supplier_id")

                if supplier_id:
                    self.suppliers[supplier_id] = document

            elif document_type == "quotation_record":
                quotation_id = metadata.get("quotation_id")

                if quotation_id:
                    self.quotations[quotation_id] = document

            elif document_type == "requisition":
                requisition_id = metadata.get("requisition_id")

                if requisition_id:
                    self.requisitions[requisition_id] = document

    def get_inventory_item(self, item_id: str):
        """Return an inventory record by item ID."""
        return self.inventory.get(item_id)

    def get_supplier(self, supplier_id: str):
        """Return a supplier record by supplier ID."""
        return self.suppliers.get(supplier_id)

    def get_quotation(self, quotation_id: str):
        """Return a quotation record by quotation ID."""
        return self.quotations.get(quotation_id)

    def get_requisition(self, requisition_id: str):
        """Return a requisition record by requisition ID."""
        return self.requisitions.get(requisition_id)


if __name__ == "__main__":

    lookup = StructuredLookup()

    print("Inventory records:", len(lookup.inventory))
    print("Supplier records:", len(lookup.suppliers))
    print("Quotation records:", len(lookup.quotations))
    print("Requisition records:", len(lookup.requisitions))

    print("\nINV-001:")
    print(lookup.get_inventory_item("INV-001"))

    print("\nSUP-05:")
    print(lookup.get_supplier("SUP-05"))

    print("\nQUO-1001:")
    print(lookup.get_quotation("QUO-1001"))