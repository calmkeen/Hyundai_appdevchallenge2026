"""Run the real local-model backend without a paid API key or fallback."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.local_provider import OllamaProvider
from app.main import create_app
import uvicorn


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="qwen3:4b")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--evidence-dir", required=True, help="New ignored output/qa directory for database and sanitized provider audit")
    args = parser.parse_args()
    out = Path(args.evidence_dir).resolve()
    out.relative_to(ROOT / "output" / "qa")
    out.mkdir(parents=True, exist_ok=False)
    audit_file = (out / "provider-events.jsonl").open("x")

    def audit(event):
        audit_file.write(json.dumps(event, ensure_ascii=False) + "\n")
        audit_file.flush()

    provider = OllamaProvider(model=args.model, base_url=args.ollama_url, audit=audit)
    app = create_app(mode="LIVE", db_path=str(out / "sessions.sqlite3"), provider=provider)
    # No key loading or paid provider construction; only loopback model HTTP.
    try:
        uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False)
    finally:
        audit_file.close()


if __name__ == "__main__":
    main()
