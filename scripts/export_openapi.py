"""Script to export OpenAPI schema to openapi.json without running the server."""
import json
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath("."))

from app.main import app

def export() -> None:
    schema = app.openapi()
    with open("openapi.json", "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
    print("✅ openapi.json successfully exported!")

if __name__ == "__main__":
    export()
