from sentence_transformers import CrossEncoder, SentenceTransformer

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def main() -> None:
    embedding_model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
    vector = embedding_model.encode("测试文本")
    print({"embedding_shape": getattr(vector, "shape", None)})

    reranker = CrossEncoder("BAAI/bge-reranker-base")
    score = reranker.predict([("查询", "候选文本")])
    print({"reranker_score": score.tolist() if hasattr(score, "tolist") else score})


if __name__ == "__main__":
    main()
