"""Create shared narrator clips for question-number labels.

These clips are intentionally shared by every page.  The read-aloud queue
selects one based on a source label such as ``12.`` so that children hear
"Question number twelve" before the question itself, without changing the
printed page.
"""

import asyncio
import sys
from pathlib import Path

import edge_tts


ONES = [
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
    "seventeen", "eighteen", "nineteen",
]
TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


def cardinal(number: int) -> str:
    if number < 20:
        return ONES[number]
    return TENS[number // 10] + (f"-{ONES[number % 10]}" if number % 10 else "")


async def main() -> None:
    output = Path("content/i18n/en-US/audio")
    output.mkdir(parents=True, exist_ok=True)
    voice = "en-US-AriaNeural"
    for number in range(1, 29):
        target = output / f"question-number-{number}.mp3"
        if target.exists() and target.stat().st_size > 500:
            continue
        await edge_tts.Communicate(f"Question number {cardinal(number)}.", voice=voice).save(str(target))
        print(target)
    end_marker = output / "end-of-page.mp3"
    if not end_marker.exists() or end_marker.stat().st_size <= 500:
        await edge_tts.Communicate("End of page.", voice=voice).save(str(end_marker))
        print(end_marker)


if __name__ == "__main__":
    asyncio.run(main())
