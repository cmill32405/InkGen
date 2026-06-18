""" CAD Generation Classes for Generating the Major components of a CAD drawing
"""
from InkGen.boundary import Canvas
from InkGen.component import ComponentGroup, TextComponent
from InkGen.style import DrawingStyle, TextStyle
from InkGen.svg_generator import LineSVG, RectangleSVG, TextSVG


class Zoning:
    """
        Class to create automatically generate the zoning components for a CAD drawing.
    """
    def __init__(self, canvas: Canvas, line_style: DrawingStyle, text_style: TextStyle, **kwargs):
        """ Create new zoning class with Canvas, Drawing Style, Text Style, and optional kwargs:
        Args:
            canvas (Canvas): Canvas for drawing
            line_style (DrawingStyle): Drawing style of the zoning lines
            text_style (TextStyle): Text style used for the zoning characters.

        Kwargs:
            Margins (float):
                Like CSS margins come in multiple flavors with more specific values overriding
                less specific.  Default is 5 units for all margins.  Order of specificity is:
                - left_margin, top_margin, right_margin, bottom_margin - enables setting separately
                - h_margins, v_margins - enables setting horizontal separate of vertical margins
                - margins - enables setting all margins at once

                If margins is set and left_margin is set also, the margins will be:
                [left_margin, margin, margin, margin]

            Zone Widths (float):
                Like CSS zone widths come in multiple flavors with more specific values overriding
                less specific. Default adjust to the size of font's largest characters + 4 units.
                Order of specificity is:
                - left_zone_width, top_zone_width, right_zone_width, bottom_zone_width
                - h_zone_width, v_zone_width
                - zone_width

                if zone_width is set and left_zone_width is set also, the zone widths will be:
                [left_zone_width, zone_width, zone_width, zone_width]

            Radii (float):
                The zoning have rounded corners on both the inner and outer boundary.
                Default is zero for both values.
                - inner_radius - Inside line will be rounded per the radius
                - outer_radius - Outer line will be rounded per the radius

            Zones (int):
                The zoning section will be divided up in an even number of zones for the
                horizontal and vertical sections.  Odd numbers don't work here because
                the zones must be symmetric around the microfiche guide arrows.
                Defaults are based on the canvas widths and heights.  For a landscape A4
                they are 10 horizontal and 8 vertical zones.
                - horizontal_zones - Number of zones for the top and bottom of the drawing
                - vertical_zones - Number of zones for the left and right of the drawing

            Zone Characters (int):
                ASCII number associated with an alphanumeric sequence to indicate if the
                zoning sections are represented by letters or numbers.  Usually set
                to either 49 for '1' or 65 for 'A'
                - first_horizontal_char - Default '1' in the right most zone
                - first_vertical_char - Default 'A' in the lowest vertical zone

        """

        if not isinstance(canvas, Canvas):
            raise TypeError("canvas argument must be a Canvas object")

        if not isinstance(line_style, DrawingStyle):
            raise TypeError("line_style argument must be a DrawingStyle object")

        if not isinstance(text_style, TextStyle):
            raise TypeError("text_style argument must be a TextStyle object")

        self._canvas = canvas
        self._line_style = line_style
        self._text_style = text_style
        self._group = ComponentGroup("Zoning")
        self._parameters = {"margins": None, "h_margins": None, "v_margins": None,
                           "left_margin": None, "right_margin": None,
                           "top_margin": None, "bottom_margin": None,
                           "zone_width": None, "h_zone_width": None, "v_zone_width": None,
                           "left_zone_width": None, "right_zone_width": None,
                           "top_zone_width": None, "bottom_zone_width": None,
                           "inner_radius": None, "outer_radius": None,
                           "horizontal_zones": None, "vertical_zones": None,
                           "first_horizontal_char": None, "first_vertical_char": None}
        self._margins = []
        self._widths = []
        self._sizes = {}

        positive_reals = ["margins", "h_margins", "v_margins", "left_margin",
                          "right_margin","top_margin", "bottom_margin","zone_width",
                          "h_zone_width", "v_zone_width","left_zone_width",
                          "right_zone_width","top_zone_width", "bottom_zone_width",
                           "inner_radius", "outer_radius"]

        ints = ["horizontal_zones", "vertical_zones"]

        letter_chars = ["first_horizontal_char", "first_vertical_char"]
        letters = list(range(65, 91))
        letters.extend(list(range(97, 123)))
        letters.extend(list(range(48, 58)))

        self._set_defaults()

        for k, v in kwargs.items():
            if k in self._parameters:
                if k in positive_reals and (v is not None) and \
                    (not isinstance(v, (float, int)) or v < 0):
                    raise ValueError(f"{k} should be a positive floating point number or integer")
                if k in ints and (v is not None) and \
                    (not isinstance(v, int) or v % 2 != 0  or v <= 0):
                    raise ValueError(f"{k} should be an even integer")
                if k in letter_chars and (v is not None) and \
                    (not isinstance(v, int) or v not in letters):
                    raise ValueError(f"{k} should be an int between 65 and 90 or 97 \
                                     and 123 or between 48 and 57")
                self._parameters[k] = v
            else:
                raise KeyError(f"{k} is not a valid parameter.")

        self._set_margins()
        self._get_character_sizes()
        self._set_zoning_widths()
        self._create_zoning()

    def _set_defaults(self) -> None:
        self._parameters['inner_radius'] = 0.0
        self._parameters['outer_radius'] = 0.0

        horizontal_zones = self._canvas.width / 25
        horizontal_zones = int(horizontal_zones - (horizontal_zones % 2))
        self._parameters['horizontal_zones'] = horizontal_zones
        vertical_zones = self._canvas.height / 25
        vertical_zones = int(vertical_zones - (vertical_zones % 2))
        self._parameters['vertical_zones'] = vertical_zones

        self._parameters['first_horizontal_char'] = 49 # 1
        self._parameters['first_vertical_char'] = 65 # A

    def _get_character_sizes(self) -> None:
        text_comp = TextComponent("_", (0, 0), self._text_style)
        for i in range(32, 255):
            character = chr(i)
            text_comp.text = character
            width = text_comp.bbox[1][0] - text_comp.bbox[0][0]
            height = text_comp.bbox[1][1] - text_comp.bbox[0][1]
            baseline_offset = -0.5 * (text_comp.bbox[0][1] + text_comp.bbox[1][1])
            self._sizes[character] = (width, height, baseline_offset)

    def _set_margins(self) -> None:

        self._margins = [5, 5, 5, 5]

        priority = [['left_margin', 'v_margins','margins'],
                    ['top_margin', 'h_margins', 'margins'],
                    ['right_margin', 'v_margins','margins'],
                    ['bottom_margin', 'h_margins', 'margins']]

        for i in range(4):
            for j in range(3):
                if self._parameters[priority[i][j]] is not None:
                    self._margins[i] = self._parameters[priority[i][j]]
                    break

        self._parameters['left_margin'] = self._margins[0]
        self._parameters['top_margin'] = self._margins[1]
        self._parameters['right_margin'] = self._margins[2]
        self._parameters['bottom_margin'] = self._margins[3]

    def _set_zoning_widths(self) -> None:

        char_widths = max(self._sizes['A'][0], self._sizes['W'][0], self._sizes['Y'][0])

        self._widths = [char_widths+4, char_widths+4, char_widths+4, char_widths+4]

        priority = [['left_zone_width', 'v_zone_width', 'zone_width'],
                    ['top_zone_width', 'h_zone_width', 'zone_width'],
                    ['right_zone_width', 'v_zone_width', 'zone_width'],
                    ['bottom_zone_width', 'h_zone_width', 'zone_width']]

        for i in range(4):
            for j in range(3):
                if self._parameters[priority[i][j]] is not None:
                    self._widths[i] = self._parameters[priority[i][j]]
                    break

        self._parameters['left_zone_width'] = self._widths[0]
        self._parameters['top_zone_width'] = self._widths[1]
        self._parameters['right_zone_width'] = self._widths[2]
        self._parameters['bottom_zone_width'] = self._widths[3]

    def _create_zoning(self) -> None:
        self._group.add_component(RectangleSVG(position=(self._margins[0], self._margins[1]),
                                               width=self._canvas.width-self._margins[2]-
                                               self._margins[0],
                                               height=self._canvas.height-self._margins[1]-
                                               self._margins[3],
                                               corner_radii=self._parameters['outer_radius'],
                                               style=self._line_style))

        inner_width = self._canvas.width - self._margins[0]
        inner_width = inner_width - self._widths[0] - self._margins[2] - self._widths[2]
        inner_height = self._canvas.height - self._margins[1]
        inner_height = inner_height - self._widths[1] - self._margins[3] - self._widths[3]
        self._group.add_component(RectangleSVG(position=(self._margins[0]+self._widths[0],
                                                         self._margins[1]+self._widths[1]),
                                               width=inner_width,
                                               height=inner_height,
                                               corner_radii=self._parameters['inner_radius'],
                                               style=self._line_style))

        vertical_mid_point = self._canvas.height-self._margins[3]-self._widths[3]
        vertical_mid_point = vertical_mid_point-self._margins[1]-self._widths[1]
        vertical_mid_point = vertical_mid_point/2
        vertical_mid_point = vertical_mid_point+self._margins[1]+self._widths[1]

        self._group.add_component(LineSVG((self._margins[0], vertical_mid_point),
                                          (self._margins[0]+self._widths[0], vertical_mid_point),
                                          self._line_style))
        self._group.add_component(LineSVG((self._canvas.width-self._margins[2]-self._widths[2],
                                           vertical_mid_point),
                                          (self._canvas.width-self._margins[2],
                                           vertical_mid_point),
                                          self._line_style))

        # offset = self._canvas.height-self._margins[1]-self._margins[3]
        offset = inner_height
        offset = offset / self._parameters['vertical_zones']
        for multiplier in range(1, int(self._parameters['vertical_zones']/2)):
            self._group.add_component(LineSVG((self._margins[0],
                                               vertical_mid_point+offset*multiplier),
                                               (self._margins[0]+self._widths[0],
                                                vertical_mid_point+offset*multiplier),
                                               self._line_style))
            self._group.add_component(LineSVG((self._canvas.width-self._margins[2]-self._widths[2],
                                               vertical_mid_point+offset*multiplier),
                                               (self._canvas.width-self._margins[2],
                                                vertical_mid_point+offset*multiplier),
                                               self._line_style))
            self._group.add_component(LineSVG((self._margins[0],
                                               vertical_mid_point-offset*multiplier),
                                               (self._margins[0]+self._widths[0],
                                                vertical_mid_point-offset*multiplier),
                                               self._line_style))
            self._group.add_component(LineSVG((self._canvas.width-self._margins[2]-self._widths[2],
                                               vertical_mid_point-offset*multiplier),
                                               (self._canvas.width-self._margins[2],
                                                vertical_mid_point-offset*multiplier),
                                               self._line_style))

        left_letter_horizontal = self._margins[0]+self._widths[0]/2
        right_letter_horizontal = self._canvas.width - self._margins[2]-self._widths[2]/2
        baseline_offset = self._sizes[chr(self._parameters['first_vertical_char'])][2]
        zone_center = self._canvas.height - self._margins[1] - self._widths[1] - offset/2
        first_letter_vertical = zone_center + baseline_offset

        for multiplier in range(self._parameters['vertical_zones']):
            character = chr(self._parameters['first_vertical_char'] + multiplier)
            y_pos = float(first_letter_vertical - offset*multiplier)
            self._group.add_component(TextSVG(character,
                                               (float(left_letter_horizontal), y_pos),
                                               self._text_style))
            character = chr(self._parameters['first_vertical_char'] + multiplier)
            self._group.add_component(TextSVG(character,
                                               (float(right_letter_horizontal), y_pos),
                                               self._text_style))

        horizontal_mid_point = self._canvas.width-self._margins[2]-self._widths[2]
        horizontal_mid_point = horizontal_mid_point-self._margins[0]-self._widths[0]
        horizontal_mid_point = horizontal_mid_point/2
        horizontal_mid_point = horizontal_mid_point+self._margins[0]+self._widths[0]

        self._group.add_component(LineSVG((horizontal_mid_point, self._margins[1]),
                                          (horizontal_mid_point, self._margins[1]+self._widths[1]),
                                          self._line_style))
        self._group.add_component(LineSVG((horizontal_mid_point,
                                           self._canvas.height-self._margins[3]-self._widths[3]),
                                          (horizontal_mid_point,
                                           self._canvas.height-self._margins[3]),
                                          self._line_style))

        #offset = self._canvas.width-self._margins[0]-self._margins[2]
        offset = inner_width
        offset = offset / self._parameters['horizontal_zones']
        for multiplier in range(1, int(self._parameters['horizontal_zones']/2)):
            self._group.add_component(LineSVG((horizontal_mid_point+offset*multiplier,
                                               self._margins[1]),
                                               (horizontal_mid_point+offset*multiplier,
                                                self._margins[1]+self._widths[1]),
                                               self._line_style))
            self._group.add_component(LineSVG((horizontal_mid_point+offset*multiplier,
                                               self._canvas.height-self._margins[3]-
                                               self._widths[3]),
                                               (horizontal_mid_point+offset*multiplier,
                                                self._canvas.height-self._margins[3]),
                                               self._line_style))
            self._group.add_component(LineSVG((horizontal_mid_point-offset*multiplier,
                                               self._margins[1]),
                                               (horizontal_mid_point-offset*multiplier,
                                                self._margins[1]+self._widths[1]),
                                               self._line_style))
            self._group.add_component(LineSVG((horizontal_mid_point-offset*multiplier,
                                               self._canvas.height-self._margins[3]-
                                               self._widths[3]),
                                               (horizontal_mid_point-offset*multiplier,
                                                self._canvas.height-self._margins[3]),
                                               self._line_style))

        baseline_offset = self._sizes[chr(self._parameters['first_horizontal_char'])][2]
        top_zone_center = self._margins[1] + self._widths[1] / 2
        bottom_zone_center = self._canvas.height - self._margins[3] - self._widths[3] / 2
        top_number_vertical = top_zone_center + baseline_offset
        bottom_number_vertical = bottom_zone_center + baseline_offset
        first_number_horizontal = self._canvas.width-self._margins[2]-self._widths[2]-offset/2

        for multiplier in range(self._parameters['horizontal_zones']):
            character = chr(multiplier+self._parameters['first_horizontal_char'])
            x_pos = float(first_number_horizontal-offset*multiplier)
            self._group.add_component(TextSVG(character,
                                              (x_pos, float(top_number_vertical)),
                                              self._text_style))
            character = chr(multiplier+self._parameters['first_horizontal_char'])
            self._group.add_component(TextSVG(character,
                                              (x_pos, float(bottom_number_vertical)),
                                              self._text_style))

    @property
    def component_group(self) -> ComponentGroup:
        """ Read-only property to get the component group object for the zoning class.

        Returns:
            ComponentGroup: Component Group with all objects in the drawing zoning
        """
        return self._group

    @property
    def parameters(self) -> dict:
        """ Parameters for the object as a dictionary for serialization.

        Returns:
            dict: dictionary with class name as top level key, that
            includes a dictionary with each parameter name as key and
            value as value.
        """
        valid_parameters = {}
        for k, v in self._parameters.items():
            if v is not None:
                valid_parameters[k] = v

        parameter_dict = {"Zoning":
                       {'canvas': self._canvas.parameters,
                       "line_style": self._line_style.parameters,
                       "text_style": self._text_style.parameters,
                       "parameters": valid_parameters}}
        return parameter_dict

    @classmethod
    def create_from_dict(cls, data: dict, styles: dict=None) -> object:
        """ Class method to recreate the object from its serialization dict.

        Args:
            data (dict): Dictionary created via obj.parameters property.

        Returns:
            object: instance of the class.
        """
        if styles is None:
            styles = {}

        line_style_name = data['Zoning']['line_style']['DrawingStyle']['name']
        text_style_name = data['Zoning']['text_style']['TextStyle']['name']
        style_names = list(styles.keys())
        if line_style_name not in style_names:
            line_style = DrawingStyle.create_from_dict(data['Zoning']['line_style'])
        else:
            line_style = styles[line_style_name]

        if text_style_name not in style_names:
            text_style = TextStyle.create_from_dict(data['Zoning']['text_style'])
        else:
            text_style = styles[text_style_name]

        zoning = cls(Canvas.create_from_dict(data=data['Zoning']['canvas']),
                     line_style=line_style, text_style=text_style,
                     **data['Zoning']['parameters'])

        return zoning
