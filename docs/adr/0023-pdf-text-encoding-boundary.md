# ADR-0023: PDF Text Encoding Boundary

## Status

Superseded by ADR-0024.

## Context

InkGen's dependency-free PDF renderer currently writes PDF text as single-byte
literal strings and emits deterministic `/ToUnicode` CMaps for bytes 32 through
126. That subset is enough for synthetic drawing labels, BOM headers, part
numbers, and many parser fixtures, but it is not full WinAnsi, UTF-16BE, or CID
font support.

Allowing text outside the mapped byte domain creates two bad outcomes:

- non-ASCII Latin-1 bytes can render but lack a matching extraction map;
- non-Latin text can fail late when the page content stream is encoded.

Both outcomes are harmful for Document Intelligence because generated fixtures
must be explicit about whether text extraction is expected to work.

## Decision

`TextPDF` validates text at construction and again during `generate_pdf()`.
The accepted PDF text-object domain is printable ASCII characters 32 through
126 plus CR/LF line breaks, which are normalized before emitting `Tj`
operators. Tabs, control characters, non-ASCII Latin-1, and Unicode characters
outside that range fail with `ValueError` before PDF bytes are emitted.

This is a boundary-hardening decision, not a full Unicode/CID implementation.
Future Unicode PDF support must add an explicit encoding policy, font resource
model, width model, and `/ToUnicode` mapping for the expanded domain.

## Consequences

- PDF text output can no longer silently emit bytes outside its proven
  extraction-map domain. ADR-0024 expands that domain from printable ASCII to
  defined CP1252/WinAnsi bytes.
- `TextPDF.create_from_dict()` and mutated `TextPDF.text` values share the same
  render boundary.
- Existing ASCII drawing, BOM, and parser-stress fixtures continue to render.
- Full Unicode/CID text remains a separately tracked PDF roadmap gap.
