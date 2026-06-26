"""Module for creating full representations of documents and
the layers they contain.
"""

from __future__ import annotations

import itertools
from collections.abc import Mapping, MutableMapping, Sequence

import yaml

from InkGen.boundary import Boundary, Canvas
from InkGen.component import ComponentGroup
from InkGen.errors import ComponentGroupCollision, ComponentGroupOffCanvas, IncompatibleCanvas, InvalidComponentGroupID


class Layer:
    """Class for storing a collection of component groups."""

    id_iter = itertools.count()

    def __init__(self, layer_name: str, canvas: Canvas, model: bool = True) -> None:
        """Initialise a new drawing layer.

        Args:
            layer_name: Human-readable layer identifier.
            canvas: Canvas describing the layer bounds.
            model: If ``True`` the layer participates in labelling/segmentation outputs.
        """
        if isinstance(layer_name, str):
            self._name = layer_name
        else:
            raise TypeError("Name attribution must be a string.")

        if isinstance(canvas, Canvas):
            self._canvas = canvas
        else:
            raise TypeError("canvas argument must be a Canvas object")

        if isinstance(model, bool):
            self._model = model
        else:
            raise TypeError("model argument must be a boolean")

        self._id = next(Layer.id_iter)
        self._group_names = {}
        self._component_groups = {}
        self._group_boundaries = {}
        self._group_collision_settings = {}

    @classmethod
    def create_from_dict(cls, data: object, styles: dict | None = None) -> Layer:
        """Recreate a layer from its serialised representation.

        Args:
            data: Serialised layer data produced by :py:meth:`parameters`.
            styles: Optional cache of already instantiated styles.

        Returns:
            Layer: Rehydrated layer instance.
        """
        styles = _style_cache(styles)
        payload = _payload_mapping(data, "Layer")
        canvas = Canvas.create_from_dict(_required_field(payload, "canvas", "Layer"))
        layer = cls(_required_field(payload, "layer_name", "Layer"), canvas, _required_field(payload, "model", "Layer"))
        collision_settings = _required_mapping(payload, "group_collision_settings", "Layer")
        for gr in _required_sequence(payload, "component_groups", "Layer"):
            group = ComponentGroup.create_from_dict(gr, styles)
            if group.group_label not in collision_settings:
                raise ValueError("Layer group_collision_settings must include every component group label")
            settings = collision_settings[group.group_label]
            if not isinstance(settings, Mapping):
                raise TypeError("Layer group collision setting entries must be mappings")
            allow_collision = _required_field(settings, "allow_collision", "Layer group collision settings")
            strict = _required_field(settings, "strict", "Layer group collision settings")
            layer.add_component_group(group, allow_collision, strict)
        return layer

    @property
    def parameters(self) -> dict:
        """Serialise the layer into a dictionary.

        Returns:
            dict: Mapping with layer metadata and component group definitions.
        """
        groups = [gr.parameters for gr in self._component_groups.values()]
        parameter_dict = {
            "Layer": {
                "layer_name": self.layer_name,
                "canvas": self.canvas.parameters,
                "model": self.model,
                "component_groups": groups,
                "group_collision_settings": self._group_collision_settings,
            }
        }
        return parameter_dict

    @property
    def layer_id(self) -> int:
        """Integer for tracking layers.

        Returns:
            int: Identifier for current object
        """
        return self._id

    @property
    def layer_name(self) -> str:
        """Read-only attribute for layer name identifier.

        Returns:
            str: name of layer.
        """
        return self._name

    @property
    def canvas(self) -> Canvas:
        """Object for storing information about
        the layers boundaries and dimensions.

        Returns:
            Canvas: canvas instance
        """
        return self._canvas

    def _create_boundary(self, group: ComponentGroup) -> None:
        """creates a new boundary object for every component group added.

        Args:
            group (ComponentGroup): new component group
        """
        self._group_boundaries[group.group_id] = Boundary(group.convex_hull, False)

    def _check_bounds(self, group: ComponentGroup, strict: bool) -> bool:
        """Verifies group argument doesn't interfere with others that
        don't allow for collisions

        Args:
            group (ComponentGroup): new ComponentGroup
            strict (bool): If true doesn't allow for touching the hull

        Returns:
            bool: True if clear, False if there is interference.
        """
        if not self._component_groups:
            return True
        for boundary in self._group_boundaries.values():
            if boundary.boundary_check(group.convex_hull, strict):
                return False
        return True

    def add_component_group(
        self,
        group: ComponentGroup,
        allow_collision: bool = True,
        strict: bool = False,
    ) -> None:
        """Attach a component group to the layer and optionally enforce collision rules.

        Args:
            group: Collection of components to attach.
            allow_collision: Skip collision checking when ``True``.
            strict: When ``True`` disallow even touching convex hulls.

        Raises:
            ComponentGroupCollision: Raised when the new group violates collision rules.
            TypeError: Raised when provided arguments have invalid types.
        """

        if not isinstance(allow_collision, bool) or not isinstance(strict, bool):
            raise TypeError("allow_collision and strict arguments must be booleans")

        if isinstance(group, ComponentGroup):
            if not self.canvas.boundary_check(group.points):
                raise ComponentGroupOffCanvas(
                    "Some points of the component \
                                              group are off the canvas"
                )

            if not self._check_bounds(group, strict):
                raise ComponentGroupCollision("New Component Group Collides with Existing")

            if not allow_collision:
                self._create_boundary(group)
            self._component_groups[group.group_id] = group
            self._group_names[group.group_label] = group.group_id
            self._group_collision_settings[group.group_label] = {"allow_collision": allow_collision, "strict": strict}
        else:
            raise TypeError("The group argument must be a ComponentGroup class")

    def remove_component_group(self, group_id: int | str) -> None:
        """Drops a component group from the layer.

        Args:
            group_id (int): ComponentGroup.group_id attribute of the desired group or
            ComponentGroup.group_label

        Raises:
            InvalidComponentGroupID: Raised if group_id is not an integer or does
            not exist in the layer's collection of ComponentGroups
        """
        if isinstance(group_id, str):
            if group_id not in self._group_names:
                raise InvalidComponentGroupID("That group_id does not exist")
            group_id = self._group_names[group_id]

        if isinstance(group_id, int) and group_id in self._component_groups:
            group_name = self._component_groups[group_id].group_label
            del self._component_groups[group_id]
            self._restore_group_name_lookup(group_name)
            if group_id in self._group_boundaries:
                del self._group_boundaries[group_id]
        else:
            raise InvalidComponentGroupID("group_id must a valid group_id in the layer")

    @property
    def component_groups(self) -> dict[str, int]:
        """Attribute with all component groups in the layer.

        Returns:
            Dict[str, int]: Dictionary with each component group name and id.
        """
        return self._group_names

    def groups(self) -> tuple[ComponentGroup, ...]:
        """Return all component groups in insertion order, including repeated labels."""
        return tuple(self._component_groups.values())

    @property
    def model(self) -> bool:
        """Read only property to indicate if the model data should be shown.

        Returns:
            bool: True means bounding boxes and segmentation mask should be included
            for this layer.
        """
        return self._model

    def group(self, group_id: int) -> ComponentGroup:
        """Get a particular component group from the layer.

        Args:
            group_id (int): id of the component group returned.

        Raises:
            ValueError: If group id doesn't exist in layer.

        Returns:
            ComponentGroup: Group of components.
        """
        if group_id in self._component_groups:
            return self._component_groups[group_id]

        raise ValueError("Invalid component group id.")

    def _restore_group_name_lookup(self, group_name: str) -> None:
        """Restore label lookup after removing one of possibly repeated labels."""
        for remaining_group_id, remaining_group in reversed(tuple(self._component_groups.items())):
            if remaining_group.group_label == group_name:
                self._group_names[group_name] = remaining_group_id
                return
        del self._group_names[group_name]
        del self._group_collision_settings[group_name]


class Layers:
    """Collection of Layer Objects for holding multiple levels of information
    such as the content to be created ("base"), bounding boxes for object detection,
    and segmentation mask with each on a different layer.
    """

    def __init__(self, canvas: Canvas, name: str | None = None, layer: Layer | None = None) -> None:
        """Create new layers container. If Layer object is passed as argument,
        it is added as the first layer and the name argument is ignored, but if
        only a name is provided a new layer with that name is added to the stack.
        If neither is provided, a new layer named "base" is created and added
        to the stack.

        Args:
            canvas (Canvas): Canvas object
            name (Optional[str], optional): Name of new layer if created.
                                            Defaults to None.
            layer (Optional[Layer], optional): Layer object to add as first layer.
                                                Defaults to None.

        Raises:
            TypeError: raised if object other than Canvas type passed to canvas
            argument.
        """

        if isinstance(canvas, Canvas):
            self._canvas = canvas
        else:
            raise TypeError("Invalid Type for canvas argument, must be a Canvas object")
        self._layers = {}
        self._layer_name_to_id_map = {}
        self.add_layer(name, layer)

    @classmethod
    def create_from_dict(cls, data: object, styles: dict | None = None) -> object:
        """Class method to recreate the object from its serialization dict.

        Args:
            data (dict): Dictionary created via obj.parameters property.

        Returns:
            object: instance of the class.
        """
        styles = _style_cache(styles)
        payload = _payload_mapping(data, "Layers")
        layers = cls(Canvas.create_from_dict(_required_field(payload, "canvas", "Layers")))
        for layer_name in list(layers.layers):
            layers.remove_layer(layer_name)
        for layer_payload in _required_mapping(payload, "layers", "Layers").values():
            layer = Layer.create_from_dict(layer_payload, styles)
            layers.add_layer(layer.layer_name, layer)
        return layers

    @property
    def parameters(self) -> dict:
        """Parameters for the object as a dictionary for serialization.

        Returns:
            dict: dictionary with class name as top level key, that
            includes a dictionary with each parameter name as key and
            value as value.
        """
        layers = {}
        sorted_layers = sorted(self.layers)
        for layer in sorted_layers:
            layers[layer] = self.layer(layer).parameters
        parameter_dict = {"Layers": {"canvas": self._canvas.parameters, "layers": layers}}
        return parameter_dict

    def _canvas_compatibility(self, layer: Layer) -> None:
        """Private method for verifying that any layer added to the class have equivalent
        Canvas attributes as the instance.

        Args:
            layer (Layer): Layer object to be compared.

        Raises:
            IncompatibleCanvas: raised if either height, width, or units do not match the
            instances Canvas object.
        """
        if (
            layer.canvas.height == self._canvas.height
            and layer.canvas.width == self._canvas.width
            and layer.canvas.units == self._canvas.units
        ):
            return
        raise IncompatibleCanvas("Layer does have match the same canvas attributes.")

    def _layer_identification_lookup(self, identifier: int | str) -> tuple[str, int]:
        """Private method to lookup the name and id of a Layer object if either the
        name or id is provided.

        Args:
            identifier (Union[int, str]): Either the name or layer_id of the Layer object
            being accessed.

        Raises:
            TypeError: If either a str or int is not provided for the identifier argument.
            ValueError: If the identifier doesn't correspond to a Layer object in the stack.

        Returns:
            Tuple[str, int]: tuple with name and layer_id.
        """
        if isinstance(identifier, str) and identifier in self._layer_name_to_id_map:
            layer_id = self._layer_name_to_id_map[identifier]
            layer_name = identifier
        elif isinstance(identifier, int) and identifier in self._layers:
            layer_id = identifier
            layer_name = self._layers[layer_id].layer_name
        elif not isinstance(identifier, int) and not isinstance(identifier, str):
            raise TypeError("Invalid identifier, must be either the name or the layer_id.")
        else:
            raise ValueError("Invalid identifier, must be either the name or the layer_id.")
        return layer_name, layer_id

    def add_layer(self, name: str | None = None, layer: Layer | None = None):
        """Add a new layer to the stack by either adding an existing Layer object
        or by creating a new layer object with the name provided.  If Layer object
        is passed as an argument the name argument is ignored as the Layer object
        already has a name which cannot be edited.

        If no name or Layer object provided will create a new layer automatically,
        with the name as "unamed_{layer_id}".

        Args:
            name (Optional[str], optional): Name which the layer can be looked up with.
                                            Defaults to None.
            layer (Optional[Layer], optional): Layer object. Defaults to None.

        Raises:
            TypeError: if name argument is not string or None.
            TypeError: if layer argument is not Layer or None.
        """
        if layer:
            if isinstance(layer, Layer):
                self._canvas_compatibility(layer)
                self._layers[layer.layer_id] = layer
                self._layer_name_to_id_map[layer.layer_name] = layer.layer_id
            else:
                raise TypeError("Invalid type for layer argument, must be Layer or None.")
        else:
            if name:
                if isinstance(name, str):
                    layer = Layer(name, self._canvas)
                else:
                    raise TypeError("Invalid type for name argument, must be string or None")
            else:
                if len(list(self._layers.keys())) == 0:
                    layer = Layer("base", self._canvas)
                else:
                    last_id = max(list(self._layers.keys()))
                    layer = Layer("unamed_" + str(last_id + 1), self._canvas)
            self._layers[layer.layer_id] = layer
            self._layer_name_to_id_map[layer.layer_name] = layer.layer_id

    def remove_layer(self, identifier: int | str) -> None:
        """Removes layer from the stack.

        Args:
            identifier (Union[int, str]): layer_name or layer_id

        Raises:
            TypeError: raised if identifier is not str or int
            ValueError: raised if identifier does not exist in layers.
        """
        layer_name, layer_id = self._layer_identification_lookup(identifier)

        del self._layer_name_to_id_map[layer_name]
        del self._layers[layer_id]

    def layer(self, identifier: str | int) -> Layer:
        """Lookup Layer in stack based on either layer name or id and return
        instance.

        Args:
            identifier (Union[str, int]): layer name or id

        Returns:
            Layer: Layer object corresponding to either name or id.
        """
        _, layer_id = self._layer_identification_lookup(identifier)
        return self._layers[layer_id]

    @property
    def layers(self) -> list[str]:
        """Return a list of all layer names in the collection

        Returns:
            List[str]: List of layer names.
        """
        return list(self._layer_name_to_id_map.keys())


class Document:
    """Class for containing numerous Layers objects as pages in a document.  Has the ability
    to add and remove pages, select the Layers object as a page number.  Also, provides
    a means of loading and saving document recipes as a YAML file.
    """

    def __init__(self, canvas: Canvas) -> None:
        """Instanciate a new document with no pages

        Args:
            canvas (Canvas): Canvas object for default pages added to the document.

        Raises:
            TypeError: Raised if Canvas object is not passed to canvas argument.
        """

        if isinstance(canvas, Canvas):
            self._canvas = canvas
        else:
            raise TypeError("Invalid Type for canvas argument, must be a Canvas object")

        self._pages = {}

    @classmethod
    def create_from_dict(cls, data: object, styles: dict | None = None) -> object:
        """Class method to recreate the object from its serialization dict.

        Args:
            data (dict): Dictionary created via obj.parameters property.

        Returns:
            object: instance of the class.
        """
        styles = _style_cache(styles)
        payload = _payload_mapping(data, "Document")
        document = cls(Canvas.create_from_dict(_required_field(payload, "canvas", "Document")))
        for page_payload in _required_sequence(payload, "pages", "Document"):
            page = Layers.create_from_dict(page_payload, styles)
            document.add_page(position=-1, page=page)
        return document

    @property
    def parameters(self) -> dict:
        """Parameters for the object as a dictionary for serialization.

        Returns:
            dict: dictionary with class name as top level key, that
            includes a dictionary with each parameter name as key and
            value as value.
        """
        pages = []
        for page in list(self._pages.keys()):
            pages.append(self.page(page).parameters)
        parameter_dict = {"Document": {"canvas": self._canvas.parameters, "pages": pages}}
        return parameter_dict

    def save(self, filepath: str) -> None:
        """Saves all parameters of the Document object as YAML file.

        Args:
            filepath (str): File to save with Document information.
        """
        with open(filepath, "w+", encoding="UTF-8") as file:
            yaml.safe_dump(self.parameters, file, allow_unicode=True, default_flow_style=False)

    @classmethod
    def load(cls, filepath: str, styles: dict | None = None):
        """Creates a Document object from a saved YAML file.

        Args:
            filepath (str): filepath of YAML file that describes a Document object.

        Returns:
            Document: Document object with all data loaded from YAML file.
            Dict[str, Style]: Dictionary of all the styles in the Document.
        """
        document_data = {}
        with open(filepath, encoding="UTF-8") as file:
            document_data = yaml.safe_load(file)

        styles = _style_cache(styles)
        document = Document.create_from_dict(document_data, styles)

        return document, styles

    def add_page(self, position: int = -1, page: Layers | None = None) -> None:
        """Add a page to the document at an optional position using the optional page
        argument to incorporate an existing Layers object.

        Args:
            position (int, optional): Location to add the new page with the default being
                                      the end of the document. Defaults to -1.
            page (Layers, optional): Layers object for the page information. Defaults to None.

        Raises:
            ValueError: Invalid position chosen for the position argument
            TypeError: Must use Layers objects for the page argument
        """
        page_number = self._validate_insert_position(position)
        if page_number == -1:
            page_number = self.pages + 1
        else:
            p = self.pages
            while p >= page_number:
                self._pages[p + 1] = self._pages[p]
                p -= 1

        if page is not None:
            if isinstance(page, Layers):
                self._page_canvas_compatibility(page)
                self._pages[page_number] = page
            else:
                raise TypeError("page argument take a Layers object")
        else:
            self._pages[page_number] = Layers(self._canvas)

    def remove_page(self, position: int) -> None:
        """Drops a page from the document and shuffles the other pages to
           fill in the gap.

        Args:
            position (int): Number for the page that will be removed.

        Raises:
            ValueError: If a page number that doesn't exist is passed
                        to the position argument.
        """
        position = self._validate_existing_position(position)
        pages = self.pages
        for p in range(position, pages):
            self._pages[p] = self._pages[p + 1]
        del self._pages[pages]

    def page(self, position: int) -> Layers:
        """Returns the layer object at the current position.

        Args:
            position (int): Position in the document.

        Returns:
            Layers: Layers object.
        """
        position = self._validate_existing_position(position)
        return self._pages[position]

    @property
    def pages(self) -> int:
        """Number of pages currently in the document.

        Returns:
            int: number of Layers objects in the document.
        """
        return len(list(self._pages.keys()))

    def _validate_insert_position(self, position: int) -> int:
        """Validate a page insertion position."""
        if isinstance(position, bool) or not isinstance(position, int):
            raise TypeError("position must be an integer page number")
        if position == -1:
            return -1
        if 1 <= position <= self.pages:
            return position
        raise ValueError("Invalid position, should be either a value between 1 and self.pages or -1 for last page.")

    def _validate_existing_position(self, position: int) -> int:
        """Validate a page position that must already exist."""
        if isinstance(position, bool) or not isinstance(position, int):
            raise TypeError("position must be an integer page number")
        if 1 <= position <= self.pages:
            return position
        raise ValueError("Position must correlate to an existing page.")

    def _page_canvas_compatibility(self, page: Layers) -> None:
        """Verify an inserted page uses the document canvas contract."""
        canvas = page._canvas
        if (canvas.height, canvas.width, canvas.units) == (self._canvas.height, self._canvas.width, self._canvas.units):
            return
        raise IncompatibleCanvas("Page must have the same canvas attributes as the document.")


def _payload_mapping(data: object, key: str) -> Mapping[str, object]:
    if not isinstance(data, Mapping):
        raise TypeError(f"{key} data must be a mapping")
    if key not in data:
        raise ValueError(f"{key} data must include {key}")
    payload = data[key]
    if not isinstance(payload, Mapping):
        raise TypeError(f"{key} payload must be a mapping")
    return payload


def _required_field(payload: Mapping[str, object], name: str, owner: str) -> object:
    if name not in payload:
        raise ValueError(f"{owner} payload must include {name}")
    return payload[name]


def _required_mapping(payload: Mapping[str, object], name: str, owner: str) -> Mapping[str, object]:
    value = _required_field(payload, name, owner)
    if not isinstance(value, Mapping):
        raise TypeError(f"{owner} {name} must be a mapping")
    return value


def _required_sequence(payload: Mapping[str, object], name: str, owner: str) -> Sequence[object]:
    value = _required_field(payload, name, owner)
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError(f"{owner} {name} must be a sequence")
    return value


def _style_cache(styles: object) -> MutableMapping[str, object]:
    """Return a mutable style cache for document-model hydration."""
    if styles is None:
        return {}
    if not isinstance(styles, MutableMapping):
        raise TypeError("styles must be a mutable mapping or None")
    return styles
