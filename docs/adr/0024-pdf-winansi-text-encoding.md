# ADR-0024: PDF WinAnsi Text Encoding

## Status

Accepted.

## Context

ADR-0023 made the PDF text boundary fail fast at printable ASCII because that
was the only byte range with an explicit `/ToUnicode` map. That prevented
silent extraction failures but still left common Windows punctuation and
Western-language characters unusable in synthetic drawing fixtures.

The PDF backend already emits `/WinAnsiEncoding` font dictionaries. Supporting
the full CP1252-backed WinAnsi character set is therefore the smallest useful
text-encoding expansion before Type0/CID font support.

## Decision

InkGen PDF text accepts characters that encode in CP1252 to defined WinAnsi
bytes 32 through 255, excluding undefined/control byte slots. Text literals
emit ASCII-safe PDF syntax by octal-escaping non-ASCII bytes. The generated
`/ToUnicode` CMap maps each defined WinAnsi byte to its Unicode code point in
chunks of at most 100 `beginbfchar` entries.

Embedded TrueType/OpenType font widths now cover `/FirstChar 32` through
`/LastChar 255`; undefined WinAnsi slots have zero width. Tabs, control
characters, Greek/CJK/emoji, and other non-WinAnsi Unicode still fail before
PDF bytes are emitted.

## Consequences

- Common CP1252 text such as `Café`, `€`, smart quotes, and en dashes can be
  emitted and extracted from generated PDFs.
- The PDF output remains dependency-free and uses the existing fonttools edge.
- Full Unicode/CID text, shaping, glyph subsetting, and complex-script support
  remain future work.
