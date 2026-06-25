"""PDF-P2 semantic extraction-truth annotations for InkGen-generated documents."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

COORDINATE_FRAME_PDF = "pdf_points_bottom_left"
BODY_SOURCE_CHANNEL = "body"
_ANNOTATIONS_ATTR = "_extraction_truth_annotations"


@dataclass(frozen=True)
class ExtractionTruthAnnotation:
    """Semantic truth attached to a rendered component, group, or document."""

    field_name: str
    value: str
    role: str = "value"
    source_channel: str = BODY_SOURCE_CHANNEL
    is_truth: bool = True
    instance_id: str | None = None

    def __post_init__(self) -> None:
        """Validate required annotation fields."""
        for field, value in (
            ("field_name", self.field_name),
            ("value", self.value),
            ("role", self.role),
            ("source_channel", self.source_channel),
        ):
            if not isinstance(value, str) or value == "":
                raise ValueError(f"{field} must be a non-empty string.")
        if not isinstance(self.is_truth, bool):
            raise TypeError("is_truth must be a bool.")
        if self.instance_id is not None and not isinstance(self.instance_id, str):
            raise TypeError("instance_id must be a string or None.")

    @classmethod
    def from_dict(cls, data: object) -> ExtractionTruthAnnotation:
        """Recreate an annotation from serialized data."""
        payload = _annotation_payload(data)
        instance_id = payload.get("instance_id")
        is_truth = payload.get("is_truth", True)
        return cls(
            field_name=_required_string(payload, "field_name"),
            value=_required_string(payload, "value"),
            role=_optional_string(payload, "role", "value"),
            source_channel=_optional_string(payload, "source_channel", BODY_SOURCE_CHANNEL),
            is_truth=is_truth,
            instance_id=_optional_string_or_none(instance_id, "instance_id"),
        )

    def to_dict(self) -> dict[str, object]:
        """Serialize this annotation into a deterministic dictionary."""
        return {
            "field_name": self.field_name,
            "value": self.value,
            "role": self.role,
            "source_channel": self.source_channel,
            "is_truth": self.is_truth,
            "instance_id": self.instance_id,
        }


@dataclass(frozen=True)
class ExtractionTruthRecord:
    """Emitted extraction-truth record consumed by downstream DocInt checks."""

    field: str
    value: str
    role: str
    page: int
    bbox: list[float] | None
    source_channel: str
    is_truth: bool
    instance_id: str | None
    coordinate_frame: str = COORDINATE_FRAME_PDF

    @classmethod
    def from_annotation(
        cls,
        annotation: ExtractionTruthAnnotation,
        *,
        page: int,
        bbox: list[float] | None,
    ) -> ExtractionTruthRecord:
        """Create an emitted record from an annotation and rendered geometry."""
        return cls(
            field=annotation.field_name,
            value=annotation.value,
            role=annotation.role,
            page=page,
            bbox=bbox,
            source_channel=annotation.source_channel,
            is_truth=annotation.is_truth,
            instance_id=annotation.instance_id,
        )

    def to_dict(self) -> dict[str, object]:
        """Serialize this record into the public extraction-truth schema."""
        return {
            "field": self.field,
            "value": self.value,
            "role": self.role,
            "page": self.page,
            "bbox": self.bbox,
            "source_channel": self.source_channel,
            "is_truth": self.is_truth,
            "instance_id": self.instance_id,
            "coordinate_frame": self.coordinate_frame,
        }


def annotate_extraction_truth(
    target: object,
    field_name: str,
    value: str,
    *,
    role: str = "value",
    source_channel: str = BODY_SOURCE_CHANNEL,
    is_truth: bool = True,
    instance_id: str | None = None,
) -> ExtractionTruthAnnotation:
    """Attach semantic extraction truth to an InkGen target object."""
    annotation = ExtractionTruthAnnotation(
        field_name=field_name,
        value=value,
        role=role,
        source_channel=source_channel,
        is_truth=is_truth,
        instance_id=instance_id,
    )
    annotations = list(get_extraction_truth_annotations(target))
    annotations.append(annotation)
    setattr(target, _ANNOTATIONS_ATTR, annotations)
    return annotation


def get_extraction_truth_annotations(target: object) -> tuple[ExtractionTruthAnnotation, ...]:
    """Return semantic annotations attached to a target object."""
    annotations = getattr(target, _ANNOTATIONS_ATTR, ())
    return tuple(_coerce_annotation(annotation) for annotation in annotations)


def set_extraction_truth_annotations(
    target: object,
    annotations: Iterable[ExtractionTruthAnnotation | dict[str, object]],
) -> None:
    """Replace all semantic annotations attached to a target object."""
    setattr(target, _ANNOTATIONS_ATTR, [_coerce_annotation(annotation) for annotation in annotations])


def serialize_extraction_truth_annotations(target: object) -> list[dict[str, object]]:
    """Serialize annotations attached to a target object."""
    return [annotation.to_dict() for annotation in get_extraction_truth_annotations(target)]


def restore_extraction_truth_annotations(target: object, annotations: Iterable[dict[str, object]]) -> None:
    """Restore serialized annotations onto a target object."""
    set_extraction_truth_annotations(
        target,
        [ExtractionTruthAnnotation.from_dict(annotation) for annotation in annotations],
    )


def records_for_annotated_target(
    target: object,
    *,
    page: int,
    canvas_height: float,
) -> list[ExtractionTruthRecord]:
    """Build emitted truth records for one annotated target."""
    records: list[ExtractionTruthRecord] = []
    for annotation in get_extraction_truth_annotations(target):
        record_page = page if annotation.source_channel == BODY_SOURCE_CHANNEL else 0
        bbox = None
        if annotation.source_channel == BODY_SOURCE_CHANNEL:
            bbox = bbox_to_pdf_points(getattr(target, "bbox", None), canvas_height)
        records.append(ExtractionTruthRecord.from_annotation(annotation, page=record_page, bbox=bbox))
    return records


def bbox_to_pdf_points(bbox: object, canvas_height: float) -> list[float] | None:
    """Convert a canvas/SVG bbox into rendered PDF bottom-left point space."""
    normalized = normalize_bbox(bbox)
    if normalized is None:
        return None
    x0, y0, x1, y1 = normalized
    return [x0, float(canvas_height) - y1, x1, float(canvas_height) - y0]


def normalize_bbox(bbox: object) -> tuple[float, float, float, float] | None:
    """Normalize common InkGen bbox shapes to ``(x0, y0, x1, y1)``."""
    if bbox is None:
        return None
    if isinstance(bbox, tuple | list) and len(bbox) == 4 and all(_is_number(value) for value in bbox):
        x0, y0, x1, y1 = (float(value) for value in bbox)
        return min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)
    if not isinstance(bbox, tuple | list):
        return None

    points: list[tuple[float, float]] = []
    for point in bbox:
        if isinstance(point, tuple | list) and len(point) >= 2 and _is_number(point[0]) and _is_number(point[1]):
            points.append((float(point[0]), float(point[1])))
    if not points:
        return None
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def sort_extraction_truth_records(records: Iterable[ExtractionTruthRecord]) -> list[ExtractionTruthRecord]:
    """Sort extraction-truth records deterministically."""
    return sorted(
        records,
        key=lambda record: (
            record.page,
            record.source_channel,
            record.field,
            record.role,
            "" if record.instance_id is None else record.instance_id,
            record.value,
            "" if record.bbox is None else ",".join(f"{value:.6f}" for value in record.bbox),
            record.is_truth,
        ),
    )


def extraction_truth_json(records: Iterable[ExtractionTruthRecord | dict[str, object]]) -> str:
    """Serialize extraction-truth records to deterministic JSON."""
    payload = [record.to_dict() if isinstance(record, ExtractionTruthRecord) else dict(record) for record in records]
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _coerce_annotation(annotation: ExtractionTruthAnnotation | dict[str, object]) -> ExtractionTruthAnnotation:
    if isinstance(annotation, ExtractionTruthAnnotation):
        return annotation
    return ExtractionTruthAnnotation.from_dict(annotation)


def _annotation_payload(data: object) -> Mapping[str, object]:
    if not isinstance(data, Mapping):
        raise TypeError("extraction truth annotation data must be a mapping")
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


def _is_number(value: object) -> bool:
    return isinstance(value, int | float)
