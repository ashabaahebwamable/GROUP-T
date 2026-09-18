from pathlib import Path
import csv


KNOWLEDGE_DIR = Path("knowledge")


def load_markdown_file(path: Path) -> dict:
    """Load one Markdown document into a normalized dictionary."""

    content = path.read_text(encoding="utf-8")

    document = {
        "content": content,
        "source": str(path),
        "document_type": "markdown",
        "metadata": {},
    }

    # Policy document
    if path.name == "procurement-policy.md":
        document["document_type"] = "policy"
        document["metadata"]["category"] = "procurement_policy"

    # Source register
    elif path.name == "SOURCE-REGISTER.md":
        document["document_type"] = "source_register"
        document["metadata"]["category"] = "provenance"

    # Quotation letters
    elif path.parent.name == "quotations":
        document["document_type"] = "quotation"

        # Extract quotation ID from filename
        quotation_id = path.name.split("-")[0:2]

        if len(quotation_id) == 2:
            document["metadata"]["quotation_id"] = "-".join(quotation_id)

    return document


def load_csv_file(path: Path) -> list[dict]:
    """Load a CSV file as structured records."""

    records = []

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:

            metadata = {
                "source_file": str(path),
            }

            document_type = "csv"

            # Inventory records
            if path.name == "inventory.csv":
                document_type = "inventory"

                if "item_id" in row:
                    metadata["item_id"] = row["item_id"]

            # Supplier records
            elif path.name == "suppliers.csv":
                document_type = "supplier"

                if "supplier_id" in row:
                    metadata["supplier_id"] = row["supplier_id"]

            # Quotation records
            elif path.name == "quotations.csv":
                document_type = "quotation_record"

                if "quotation_id" in row:
                    metadata["quotation_id"] = row["quotation_id"]

                if "supplier_id" in row:
                    metadata["supplier_id"] = row["supplier_id"]

                if "item_id" in row:
                    metadata["item_id"] = row["item_id"]

            # Requisition records
            elif path.name == "requisitions.csv":
                document_type = "requisition"

                if "requisition_id" in row:
                    metadata["requisition_id"] = row["requisition_id"]

            records.append({
                "content": row,
                "source": str(path),
                "document_type": document_type,
                "metadata": metadata,
            })

    return records


def load_knowledge_base() -> list[dict]:
    """Load all supported documents from the knowledge directory."""

    documents = []

    # Load Markdown documents
    for path in KNOWLEDGE_DIR.rglob("*.md"):
        documents.append(load_markdown_file(path))

    # Load CSV documents
    for path in KNOWLEDGE_DIR.rglob("*.csv"):
        documents.extend(load_csv_file(path))

    return documents


if __name__ == "__main__":
    documents = load_knowledge_base()

    print(f"Loaded {len(documents)} knowledge records.")

    for document in documents[:10]:
        print("\n---")
        print("Source:", document["source"])
        print("Type:", document["document_type"])
        print("Metadata:", document["metadata"])
        print("Content:", document["content"])