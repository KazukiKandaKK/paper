from __future__ import annotations

from paper2exp.core.utils import truncate_text


class EvidenceBuilder:
    def __init__(self) -> None:
        self._items: list[dict] = []
        self._counter = 1

    def add(self, source: str, locator: str, quote: str) -> None:
        quote = truncate_text(str(quote).strip(), max_chars=500)
        if not quote:
            return
        self._items.append(
            {
                "id": f"E{self._counter}",
                "source": source,
                "locator": truncate_text(locator, max_chars=200),
                "quote": quote,
            }
        )
        self._counter += 1

    def items(self) -> list[dict]:
        return list(self._items)
