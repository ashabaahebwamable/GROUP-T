from pathlib import Path

from src.ingestion.loader import load_knowledge_base


def chunk_policy(document: dict) -> list[dict]:
    """
    Split the procurement policy into meaningful sections.

    Each Markdown heading becomes the beginning of a semantic chunk.
    """

    content = document["content"]
    lines = content.splitlines()

    chunks = []
    current_title = None
    current_lines = []

    for line in lines:

        # Detect level-2 Markdown headings
        if line.startswith("## "):

            # Save the previous section
            if current_title is not None:
                chunks.append({
                    "content": "\n".join(current_lines).strip(),
                    "source": document["source"],
                    "document_type": document["document_type"],
                    "metadata": {
                        **document["metadata"],
                        "section": current_title,
                    },
                })

            current_title = line.replace("## ", "").strip()
            current_lines = [line]

        else:
            current_lines.append(line)

    # Save final section
    if current_title is not None:
        chunks.append({
            "content": "\n".join(current_lines).strip(),
            "source": document["source"],
            "document_type": document["document_type"],
            "metadata": {
                **document["metadata"],
                "section": current_title,
            },
        })

    return chunks


def chunk_markdown_document(document: dict) -> list[dict]:
    """
    Apply the appropriate chunking strategy to a Markdown document.
    """

    if document["document_type"] == "policy":
        return chunk_policy(document)

    # Small quotation letters and source register remain intact.
    return [{
        "content": document["content"],
        "source": document["source"],
        "document_type": document["document_type"],
        "metadata": document["metadata"],
    }]


def chunk_document(document: dict) -> list[dict]:
    """
    Convert a normalized knowledge record into retrieval-ready chunks.
    """

    # CSV records are already appropriately sized structured units.
    if document["document_type"] in {
        "inventory",
        "supplier",
        "quotation_record",
        "requisition",
    }:
        return [{
            "content": document["content"],
            "source": document["source"],
            "document_type": document["document_type"],
            "metadata": document["metadata"],
        }]

    # Markdown documents
    return chunk_markdown_document(document)


def build_chunks() -> list[dict]:
    """
    Load the knowledge base and convert all records into chunks.
    """

    documents = load_knowledge_base()

    chunks = []

    for document in documents:
        chunks.extend(chunk_document(document))

    return chunks


if __name__ == "__main__":
    chunks = build_chunks()

    print(f"Created {len(chunks)} retrieval chunks.")

    for index, chunk in enumerate(chunks[:15], start=1):
        print("\n---")
        print("Chunk:", index)
        print("Source:", chunk["source"])
        print("Type:", chunk["document_type"])
        print("Metadata:", chunk["metadata"])
        print("Content preview:", str(chunk["content"])[:300])