from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.clients.embeddings import OpenAIEmbeddingClient
from backend.config import EMBEDDING_API_KEY, EMBEDDING_BASE_URL, EMBEDDING_MODEL


def main() -> None:
    embedding_client = OpenAIEmbeddingClient(
        api_key=EMBEDDING_API_KEY,
        base_url=EMBEDDING_BASE_URL,
        model=EMBEDDING_MODEL,
    )
    vector = embedding_client.embed_query("测试文本")
    print({"embedding_base_url": EMBEDDING_BASE_URL, "embedding_model": EMBEDDING_MODEL, "embedding_dim": len(vector)})


if __name__ == "__main__":
    main()
