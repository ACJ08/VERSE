"""Bake the live report into the dashboard.

    python demo/build_dashboard.py

Reads `dashboard.body.html` (the single source of truth for markup), injects a
freshly generated report, and writes two files:

  demo/dashboard.html       standalone page, opened directly in a browser
  demo/dashboard.artifact.html   body-only fragment, for publishing as an Artifact

Both carry identical content; only the surrounding skeleton differs.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "continuity-engine"))
sys.path.insert(0, str(ROOT))

from demo.pipeline import export_report  # noqa: E402

_SKELETON = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}</style>
</head>
<body>
{body}
</body>
</html>
"""


def build() -> Path:
    payload = export_report(HERE / "report.json")
    body = (HERE / "dashboard.body.html").read_text(encoding="utf-8")

    # json.dumps output is embedded in a <script type="application/json">, so the
    # only sequence that can break out is a literal "</script>".
    data = json.dumps(payload, separators=(",", ":")).replace("</", "<\\/")
    body = body.replace("__DATA__", data)

    fragment = HERE / "dashboard.artifact.html"
    fragment.write_text(body, encoding="utf-8")

    standalone = HERE / "dashboard.html"
    standalone.write_text(_SKELETON.format(body=body), encoding="utf-8")

    report = payload["report"]
    print(f"score {report['overall_score']} · {len(report['issues'])} issues")
    print(f"wrote {standalone.relative_to(ROOT)} and {fragment.relative_to(ROOT)}")
    return standalone


if __name__ == "__main__":
    build()
