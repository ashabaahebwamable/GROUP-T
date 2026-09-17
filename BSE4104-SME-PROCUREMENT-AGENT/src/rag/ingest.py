"""Build a searchable SQLite index from the controlled knowledge corpus."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"
DEFAULT_INDEX_PATH = PROJECT_ROOT / ".rag" / "index.sqlite3"
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")


def _doc_id(path: Path, knowledge_dir: Path) -> str:
    """Return a stable, workspace-relative identifier for a source file."""
    return path.relative_to(knowledge_dir).as_posix()


def _markdown_chunks(path: Path, knowledge_dir: Path) -> Iterable[Dict[str, Any]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    headings: List[Tuple[int, str]] = []
    for line_number, line in enumerate(lines, start=1):
        match = HEADING_RE.match(line)
        if match:
            headings.append((line_number, match.group(2).strip()))

    boundaries = [(1, "Preamble")] + headings
    for index, (start, title) in enumerate(boundaries):
        if headings and index == 0:
            end = headings[0][0] - 1
        else:
            end = boundaries[index + 1][0] - 1 if index + 1 < len(boundaries) else len(lines)
        content = "\n".join(lines[start - 1:end]).strip()
        if not content:
            continue
        yield {
            "doc_id": _doc_id(path, knowledge_dir),
            "section_title": title,
            "line_start": start,
            "line_end": end,
            "content": content,
            "metadata": {"source_path": _doc_id(path, knowledge_dir), "file_type": "markdown"},
        }


def _csv_chunks(path: Path, knowledge_dir: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))

    source_path = _doc_id(path, knowledge_dir)
    for row_number, row in enumerate(rows, start=2):
        content = "\n".join(f"{key}: {value}" for key, value in row.items() if value is not None)
        yield {
            "doc_id": source_path,
            "section_title": "CSV row",
            "line_start": row_number,
            "line_end": row_number,
            "content": content,
            "metadata": {
                "source_path": source_path,
                "file_type": "csv",
                "row_number": row_number,
            },
        }


def _iter_chunks(knowledge_dir: Path) -> Iterable[Dict[str, Any]]:
    for path in sorted(knowledge_dir.rglob("*")):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix == ".md":
            yield from _markdown_chunks(path, knowledge_dir)
        elif suffix == ".csv":
            yield from _csv_chunks(path, knowledge_dir)


def _create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE chunks (
            id INTEGER PRIMARY KEY,
            doc_id TEXT NOT NULL,
            section_title TEXT NOT NULL,
            line_start INTEGER NOT NULL,
            line_end INTEGER NOT NULL,
            content TEXT NOT NULL,
            metadata_json TEXT NOT NULL
        );

        CREATE VIRTUAL TABLE chunks_fts USING fts5(
            content,
            doc_id,
            section_title,
            content='chunks',
            content_rowid='id'
        );
        """
    )


def ingest(
    knowledge_dir: Path | str = DEFAULT_KNOWLEDGE_DIR,
    index_path: Path | str = DEFAULT_INDEX_PATH,
) -> int:
    """Rebuild the index and return the number of indexed chunks.

    The existing index is replaced inside one transaction, so a successful run
    contains only files currently present under ``knowledge_dir``.
    """
    knowledge_path = Path(knowledge_dir).resolve()
    database_path = Path(index_path).resolve()
    if not knowledge_path.is_dir():
        raise FileNotFoundError(f"Knowledge directory does not exist: {knowledge_path}")
    database_path.parent.mkdir(parents=True, exist_ok=True)

    chunks = list(_iter_chunks(knowledge_path))
    connection = sqlite3.connect(database_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("DROP TABLE IF EXISTS chunks_fts")
        connection.execute("DROP TABLE IF EXISTS chunks")
        _create_schema(connection)
        connection.executemany(
            """
            INSERT INTO chunks
                (doc_id, section_title, line_start, line_end, content, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    chunk["doc_id"],
                    chunk["section_title"],
                    chunk["line_start"],
                    chunk["line_end"],
                    chunk["content"],
                    json.dumps(chunk["metadata"], sort_keys=True),
                )
                for chunk in chunks
            ],
        )
        connection.execute("INSERT INTO chunks_fts(chunks_fts) VALUES ('rebuild')")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    return len(chunks)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--knowledge-dir", type=Path, default=DEFAULT_KNOWLEDGE_DIR)
    parser.add_argument("--index", dest="index_path", type=Path, default=DEFAULT_INDEX_PATH)
    args = parser.parse_args(argv)
    count = ingest(args.knowledge_dir, args.index_path)
    print(f"Indexed {count} chunks into {args.index_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())