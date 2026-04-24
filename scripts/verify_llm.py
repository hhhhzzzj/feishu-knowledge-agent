from openai import OpenAI

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL


def main() -> None:
    if not LLM_API_KEY:
        raise SystemExit("LLM_API_KEY is empty")
    if not LLM_MODEL:
        raise SystemExit("LLM_MODEL is empty")

    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": "你好，请用一句话确认你已连通。"}],
    )
    print(response.choices[0].message.content)


if __name__ == "__main__":
    main()
