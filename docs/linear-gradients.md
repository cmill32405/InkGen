# Linear Gradients

InkGen supports parametric linear-gradient fills on rectangles without an
additional runtime dependency.

```python
from InkGen import DrawingStyle, LinearGradientFill, RectangleDrawing

gradient = LinearGradientFill(
    stops=[
        (0.0, "#008040"),
        (1.0, "#ffffff"),
    ],
    angle_deg=0.0,
)

panel = RectangleDrawing(
    position=(10.0, 20.0),
    width=80.0,
    height=15.0,
    corner_radii=2.0,
    style=DrawingStyle("bill-header", stroke="none", fill="none"),
    fill_gradient=gradient,
)
```

Angles are measured counter-clockwise from the visual horizontal. The gradient
axis is computed in canvas units and spans the full rectangle. SVG uses a
user-space `<linearGradient>` paint server. PDF uses an axial shading resource
clipped to the rectangle path. Overall fill opacity comes from
`DrawingStyle.fill_opacity`.

Gradient parameters use this stable serialization shape:

```json
{
  "kind": "linear",
  "stops": [
    [0.0, "#008040"],
    [1.0, "#ffffff"]
  ],
  "angle_deg": 0.0
}
```

At least two stops are required. Offsets must be finite, strictly increasing,
and between zero and one. Colors must use six-digit RGB hex notation. Stops do
not need to begin at zero or end at one; PDF extends the endpoint colors to the
domain boundaries, matching SVG pad behavior.

Annotated gradient rectangles retain their normal extraction-truth bbox and add
the gradient payload under `parameters.fill_gradient`. Solid rectangles omit
the key and retain their legacy serialization shape.

SVG and PDF are the defined gradient-rendering outputs. DXF rejects gradient
rectangles explicitly instead of flattening them to a solid fill. Radial
gradients, patterns, meshes, and per-stop opacity are not currently supported.
