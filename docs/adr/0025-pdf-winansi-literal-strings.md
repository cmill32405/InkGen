# ADR-0025: PDF WinAnsi Literal Strings

## Status

Accepted.

## Context

ADR-0024 expanded `TextPDF` content from printable ASCII to defined
CP1252-backed WinAnsi bytes. Several document metadata APIs still used the
older Latin-1 validation boundary even though they emit PDF literal strings
through the same dependency-free object writer.

That mismatch rejected common fixture labels such as `Café`, `€`, smart quotes,
and en dashes in page labels, outlines, URI targets, named destinations, and
annotation contents.

## Decision

PDF literal-string metadata accepts non-empty strings that encode to defined
CP1252/WinAnsi bytes, plus CR/LF line breaks where the existing literal-string
paths already supported line breaks. Undefined WinAnsi byte slots, tabs,
controls, CJK, Greek, emoji, and other non-WinAnsi Unicode fail at the public
API boundary.

`_escape_pdf_string()` octal-escapes non-ASCII WinAnsi bytes and escapes PDF
literal-string delimiters. This keeps all generated object dictionaries
Latin-1/ASCII-safe while preserving deterministic CP1252 bytes for PDF readers.

## Consequences

- Page labels, outline titles and parents, URI link targets, named destination
  names, named-destination link targets, and annotation text fields now share
  one literal-string validation helper.
- Older ADRs that describe these fields as Latin-1 are superseded only for the
  string-encoding boundary; their geometry, ordering, serialization, and page
  mutation decisions remain active.
- Full Unicode PDF strings using UTF-16BE, rich annotation appearances, tagged
  PDF structure, and complex text shaping remain out of scope.
