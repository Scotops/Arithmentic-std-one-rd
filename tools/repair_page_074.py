"""Replace the accidental embedded table crop with individual source sticks."""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    path = ROOT / "pg074_sec001.html"
    source = path.read_text(encoding="utf-8")

    def repair(match: re.Match[str]) -> str:
        tag = match.group(0)
        tag = re.sub(r'src="images/pg074_im025\.png"', 'src="images/pg074_im016.jpg"', tag)
        tag = re.sub(r'data-id="pg074_im025"', 'data-id="pg074_im016"', tag)
        tag = re.sub(r'alt="[^"]*"', 'alt="One single counting stick."', tag)
        tag = re.sub(r'class="[^"]*"', 'class="h-auto w-20 max-w-full object-contain max-sm:w-10"', tag)
        tag = re.sub(r'style="[^"]*"', 'style="max-width: 100%; height: auto;"', tag)
        return tag

    source = re.sub(
        r'<img\b[^>]*src="images/pg074_im(?:015|016|025)(?:\.jpg|\.png)"[^>]*>',
        repair,
        source,
        flags=re.IGNORECASE,
    )
    path.write_text(source, encoding="utf-8", newline="")
    print("Repaired page 74 stick rows with individual source illustrations.")


if __name__ == "__main__":
    main()
