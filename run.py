"""Start Custora AI:  python run.py [--port 5000]  (trains the models on first run)."""
import argparse
from backend.app import create_app

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5000)
    a = ap.parse_args()
    create_app().run(host=a.host, port=a.port, debug=False)
