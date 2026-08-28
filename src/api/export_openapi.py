"""Export the deterministic OpenAPI v1 contract artifact."""

from __future__ import annotations

import json
from pathlib import Path

from src.api.app import app


def main(output: str = "docs/openapi-v1.json") -> None:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
