"""PDF-P3 render-contract guards for proof-critical PDF paths."""

from __future__ import annotations

from InkGen.component import Component


def ensure_builtin_pdf_component(
    component: Component,
    allowed_types: tuple[type[Component], ...],
    *,
    message: str,
) -> None:
    """Reject components outside the closed built-in PDF renderer domain."""
    if type(component) not in allowed_types:
        raise TypeError(message)


def ensure_pdf_group(group: object, group_type: type[object], *, message: str) -> None:
    """Reject non-PDF component groups before PDF rendering."""
    if not isinstance(group, group_type):
        raise TypeError(message)
