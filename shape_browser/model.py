from collections import defaultdict


class Occurrence:
    """
    Represents one placement of a shape on a page.
    """

    def __init__(self, page_number, x, y):
        self.page_number = page_number
        self.x = x
        self.y = y

    def __repr__(self):
        return f"<Occurrence page={self.page_number} x={self.x} y={self.y}>"



class Shape:
    """
    Represents a canonical glyph shape.
    """

    def __init__(self, shape_id, parent_id, width, height, bits):
        self.id = shape_id
        self.parent_id = parent_id
        self.width = width
        self.height = height
        self.bits = bits

        self.children = []
        self.occurrences = []

    def add_child(self, child):
        self.children.append(child)

    def add_occurrence(self, occurrence):
        self.occurrences.append(occurrence)

    @property
    def usage_count(self):
        return len(self.occurrences)

    def __repr__(self):
        return f"<Shape id={self.id} parent={self.parent_id} children={len(self.children)} occurrences={len(self.occurrences)}>"


class ShapeModel:
    """
    Builds in-memory structure of shapes and their relationships.
    """

    def __init__(self, shape_rows, blit_rows):
        self.shapes = {}          # shape_id -> Shape
        self.root_shapes = []     # shapes without parent

        self._build_shapes(shape_rows)
        self._build_hierarchy()
        self._attach_occurrences(blit_rows)

    # -------------------------
    # Internal Build Steps
    # -------------------------

    def _build_shapes(self, shape_rows):
        for row in shape_rows:
            shape = Shape(
                shape_id=row["id"],
                parent_id=row["parent_id"],
                width=row["width"],
                height=row["height"],
                bits=row["bits"],
            )
            self.shapes[shape.id] = shape

    def _build_hierarchy(self):
    # First initialize depth to 0 for all
          for shape in self.shapes.values():
            shape.depth = 0

    # Assign children and compute depth
          for shape in self.shapes.values():
              if shape.parent_id and shape.parent_id in self.shapes:
                  parent = self.shapes[shape.parent_id]
                  shape.depth = parent.depth + 1
                  parent.add_child(shape)
              else:
                  self.root_shapes.append(shape)

    # Sort roots by height descending
    self.root_shapes.sort(key=lambda s: s.height, reverse=True)

    def _attach_occurrences(self, blit_rows):
        for row in blit_rows:
            shape_id = row["shape_id"]
            if shape_id in self.shapes:
                occurrence = Occurrence(
                    page_number=row["page_number"],
                    x=row["b_left"],
                    y=row["b_bottom"],
                )
                self.shapes[shape_id].add_occurrence(occurrence)

    # -------------------------
    # Public API
    # -------------------------

    def get_shape(self, shape_id):
        return self.shapes.get(shape_id)

    def all_shapes(self):
        return list(self.shapes.values())
