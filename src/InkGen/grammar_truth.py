"""PDF-P3 grammar cue and construct truth annotations for InkGen documents."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from InkGen.extraction_truth import BODY_SOURCE_CHANNEL, COORDINATE_FRAME_PDF, bbox_to_pdf_points

GRAMMAR_TRUTH_KINDS = frozenset({"cue", "construct", "link", "assessment"})
_ANNOTATIONS_ATTR = "_grammar_truth_annotations"


@dataclass(frozen=True)
class GrammarTruthAnnotation:
    """Structural grammar truth attached to a rendered feature or document."""

    condition_id: str
    kind: str
    value: object | None = None
    links_to: str | None = None
    source_channel: str = BODY_SOURCE_CHANNEL
    instance_id: str | None = None

    def __post_init__(self) -> None:
        """Validate registry-agnostic grammar annotation fields."""
        if not isinstance(self.condition_id, str) or not self.condition_id:
            raise ValueError("condition_id must be a non-empty string.")
        if self.kind not in GRAMMAR_TRUTH_KINDS:
            valid = ", ".join(sorted(GRAMMAR_TRUTH_KINDS))
            raise ValueError(f"kind must be one of: {valid}.")
        if not isinstance(self.source_channel, str) or not self.source_channel:
            raise ValueError("source_channel must be a non-empty string.")
        if self.links_to is not None and not isinstance(self.links_to, str):
            raise TypeError("links_to must be a string or None.")
        if self.instance_id is not None and not isinstance(self.instance_id, str):
            raise TypeError("instance_id must be a string or None.")

    @classmethod
    def from_dict(cls, data: object) -> GrammarTruthAnnotation:
        """Recreate an annotation from serialized data."""
        payload = _annotation_payload(data)
        links_to = payload.get("links_to")
        instance_id = payload.get("instance_id")
        return cls(
            condition_id=_required_string(payload, "condition_id"),
            kind=_required_string(payload, "kind"),
            value=payload.get("value"),
            links_to=_optional_string_or_none(links_to, "links_to"),
            source_channel=_optional_string(payload, "source_channel", BODY_SOURCE_CHANNEL),
            instance_id=_optional_string_or_none(instance_id, "instance_id"),
        )

    def to_dict(self) -> dict[str, object]:
        """Serialize this annotation into a deterministic dictionary."""
        return {
            "condition_id": self.condition_id,
            "kind": self.kind,
            "value": self.value,
            "links_to": self.links_to,
            "source_channel": self.source_channel,
            "instance_id": self.instance_id,
        }


@dataclass(frozen=True)
class GrammarTruthRecord:
    """Emitted grammar-truth record consumed by downstream DocInt scoring."""

    condition_id: str
    kind: str
    page: int
    bbox: list[float] | None
    value: object | None
    links_to: str | None
    source_channel: str
    instance_id: str | None
    coordinate_frame: str = COORDINATE_FRAME_PDF

    @classmethod
    def from_annotation(
        cls,
        annotation: GrammarTruthAnnotation,
        *,
        page: int,
        bbox: list[float] | None,
    ) -> GrammarTruthRecord:
        """Create an emitted record from an annotation and rendered geometry."""
        return cls(
            condition_id=annotation.condition_id,
            kind=annotation.kind,
            page=page,
            bbox=bbox,
            value=annotation.value,
            links_to=annotation.links_to,
            source_channel=annotation.source_channel,
            instance_id=annotation.instance_id,
        )

    def to_dict(self) -> dict[str, object]:
        """Serialize this record into the public grammar-truth schema."""
        return {
            "condition_id": self.condition_id,
            "kind": self.kind,
            "page": self.page,
            "bbox": self.bbox,
            "value": self.value,
            "links_to": self.links_to,
            "source_channel": self.source_channel,
            "instance_id": self.instance_id,
            "coordinate_frame": self.coordinate_frame,
        }


def annotate_grammar_truth(
    target: object,
    condition_id: str,
    kind: str,
    *,
    value: object | None = None,
    links_to: str | None = None,
    source_channel: str = BODY_SOURCE_CHANNEL,
    instance_id: str | None = None,
) -> GrammarTruthAnnotation:
    """Attach structural grammar truth to an InkGen target object."""
    annotation = GrammarTruthAnnotation(
        condition_id=condition_id,
        kind=kind,
        value=value,
        links_to=links_to,
        source_channel=source_channel,
        instance_id=instance_id,
    )
    annotations = list(get_grammar_truth_annotations(target))
    annotations.append(annotation)
    set_grammar_truth_annotations(target, annotations)
    return annotation


def copy_grammar_truth_annotations(source: object, target: object) -> None:
    """Copy grammar-truth annotations from one object to another."""
    annotations = get_grammar_truth_annotations(source)
    if annotations:
        set_grammar_truth_annotations(target, annotations)


def get_grammar_truth_annotations(target: object) -> tuple[GrammarTruthAnnotation, ...]:
    """Return grammar annotations attached to a target object."""
    annotations = getattr(target, _ANNOTATIONS_ATTR, ())
    return tuple(_coerce_annotation(annotation) for annotation in annotations)


def set_grammar_truth_annotations(
    target: object,
    annotations: Iterable[GrammarTruthAnnotation | dict[str, object]],
) -> None:
    """Replace all grammar annotations attached to a target object."""
    object.__setattr__(target, _ANNOTATIONS_ATTR, [_coerce_annotation(annotation) for annotation in annotations])


def serialize_grammar_truth_annotations(target: object) -> list[dict[str, object]]:
    """Serialize annotations attached to a target object."""
    return [annotation.to_dict() for annotation in get_grammar_truth_annotations(target)]


def restore_grammar_truth_annotations(target: object, annotations: Iterable[dict[str, object]]) -> None:
    """Restore serialized annotations onto a target object."""
    set_grammar_truth_annotations(
        target,
        [GrammarTruthAnnotation.from_dict(annotation) for annotation in annotations],
    )


def records_for_annotated_target(
    target: object,
    *,
    page: int,
    canvas_height: float,
) -> list[GrammarTruthRecord]:
    """Build emitted grammar records for one annotated target."""
    records: list[GrammarTruthRecord] = []
    for annotation in get_grammar_truth_annotations(target):
        record_page = page if annotation.source_channel == BODY_SOURCE_CHANNEL else 0
        bbox = None
        if annotation.source_channel == BODY_SOURCE_CHANNEL:
            bbox = bbox_to_pdf_points(getattr(target, "bbox", None), canvas_height)
        records.append(GrammarTruthRecord.from_annotation(annotation, page=record_page, bbox=bbox))
    return records


def sort_grammar_truth_records(records: Iterable[GrammarTruthRecord]) -> list[GrammarTruthRecord]:
    """Sort grammar-truth records deterministically."""
    return sorted(
        records,
        key=lambda record: (
            record.page,
            record.source_channel,
            record.kind,
            record.condition_id,
            "" if record.instance_id is None else record.instance_id,
            "" if record.links_to is None else record.links_to,
            _stable_value(record.value),
            "" if record.bbox is None else ",".join(f"{value:.6f}" for value in record.bbox),
        ),
    )


def grammar_truth_json(records: Iterable[GrammarTruthRecord | dict[str, object]]) -> str:
    """Serialize grammar-truth records to deterministic JSON."""
    payload = [record.to_dict() if isinstance(record, GrammarTruthRecord) else dict(record) for record in records]
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _coerce_annotation(annotation: GrammarTruthAnnotation | dict[str, object]) -> GrammarTruthAnnotation:
    if isinstance(annotation, GrammarTruthAnnotation):
        return annotation
    return GrammarTruthAnnotation.from_dict(annotation)


def _annotation_payload(data: object) -> Mapping[str, object]:
    if not isinstance(data, Mapping):
        raise TypeError("grammar truth annotation data must be a mapping")
    return data


def _required_string(payload: Mapping[str, object], name: str) -> str:
    if name not in payload:
        raise ValueError(f"{name} is required.")
    value = payload[name]
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string.")
    return value


def _optional_string(payload: Mapping[str, object], name: str, default: str) -> str:
    value = payload.get(name, default)
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string.")
    return value


def _optional_string_or_none(value: object, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string or None.")
    return value


def _stable_value(value: object | None) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
