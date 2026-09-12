"""Classify the complete render audit and reject any physical-spine defect."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "tmp" / "render-audit-release" / "render-audit.json"


def main() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    pages = json.loads((ROOT / "content" / "pages.json").read_text(encoding="utf-8"))
    physical = {entry["href"].split("#", 1)[0] for entry in pages}
    physical_findings = [
        finding for finding in report["findings"]
        if finding["severity"] == "error" and finding["file"] in physical
    ]
    if physical_findings:
        raise SystemExit(f"Physical-spine render errors: {physical_findings[:5]}")

    accepted = []
    unexpected = []
    for finding in report["findings"]:
        if finding["severity"] != "error":
            continue
        message = finding.get("message", "")
        match = re.match(r"media: (https?://\S+) \(net::ERR_ABORTED\)$", message)
        compatibility = bool(re.fullmatch(r"pg\d{3}_sec00[2-9]\.html", finding["file"]))
        exists = False
        if match:
            relative = unquote(urlparse(match.group(1)).path).lstrip("/")
            exists = (ROOT / relative).is_file()
        if finding["code"] == "browser-resource-failure" and compatibility and match and exists:
            accepted.append(finding)
        else:
            unexpected.append(finding)
    if unexpected:
        raise SystemExit(f"Unexpected render errors: {unexpected[:5]}")

    rendered_physical = {
        (view["file"], view["viewport"]["width"], view["viewport"]["height"])
        for view in report["pages"] if view["file"] in physical
    }
    if len(rendered_physical) != 268:
        raise SystemExit(f"Expected 268 physical-page views, got {len(rendered_physical)}")
    print(json.dumps({
        "physical_pages": 134,
        "physical_views": 268,
        "physical_render_errors": 0,
        "accepted_unlisted_compatibility_media_cancellations": len(accepted),
        "missing_media": 0,
        "unexpected_errors": 0,
    }, indent=2))


if __name__ == "__main__":
    main()
