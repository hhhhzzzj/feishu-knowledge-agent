from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.clients import LarkCLIClient
from backend.config import LARK_CLI_IDENTITY, LARK_CLI_PATH, RAW_DOCS_DIR
from backend.ingestion import DocumentIngestionService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("doc", help="Lark document URL or token")
    parser.add_argument("--subdirectory", default="lark_docs")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client = LarkCLIClient(cli_path=LARK_CLI_PATH, identity=LARK_CLI_IDENTITY)
    service = DocumentIngestionService(client=client, raw_docs_dir=RAW_DOCS_DIR)
    artifact = service.ingest_document(doc=args.doc, subdirectory=args.subdirectory)
    print(
        {
            "doc_id": artifact.doc_id,
            "title": artifact.title,
            "source_url": artifact.source_url,
            "markdown_path": str(artifact.markdown_path),
            "metadata_path": str(artifact.metadata_path),
        }
    )


if __name__ == "__main__":
    main()
