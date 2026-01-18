from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TextChunk:
    chunk_id: str
    start_line: int
    end_line: int
    text: str


def chunk_text(text: str, max_chars: int = 6000, max_chunks: int = 6) -> list[TextChunk]:
    lines = (text or "").splitlines()
    chunks: list[TextChunk] = []
    current: list[str] = []
    start_line = 1
    char_count = 0

    def flush(end_line: int) -> None:
        nonlocal current, start_line, char_count
        if not current:
            return
        chunk_id = f"C{len(chunks) + 1}"
        chunks.append(
            TextChunk(
                chunk_id=chunk_id,
                start_line=start_line,
                end_line=end_line,
                text="\n".join(current),
            )
        )
        current = []
        char_count = 0

    for idx, line in enumerate(lines, start=1):
        if not current:
            start_line = idx
        line_len = len(line) + 1
        if char_count + line_len > max_chars and current:
            flush(idx - 1)
            if len(chunks) >= max_chunks:
                break
        current.append(line)
        char_count += line_len
    if current and len(chunks) < max_chunks:
        flush(len(lines))
    return chunks


def format_chunks(chunks: list[TextChunk]) -> str:
    if not chunks:
        return ""
    blocks = []
    for chunk in chunks:
        header = f"chunk:{chunk.chunk_id} lines:{chunk.start_line}-{chunk.end_line}"
        blocks.append(header)
        blocks.append(chunk.text)
        blocks.append("")
    return "\n".join(blocks).strip()
