class Shape:
    def __init__(self, shape_row):
        self.id = shape_row["id"]
        self.parent_id = shape_row["parent_id"]
        self.width = shape_row["width"]
        self.height = shape_row["height"]

        # Bitmap (used by renderer)
        self.bits = shape_row["bits"]

        # Direct occurrence count
        self.usage_count = 0

        # Subtree occurrence count
        self.subtree_count = 0

        # Tree
        self.children = []
        self.depth = 0

        # Occurrences
        self.occurrences = []


class Occurrence:
    def __init__(self, blit_row):
        self.shape_id = blit_row["shape_id"]
        self.page_number = blit_row["page_number"]
        self.b_left = blit_row["b_left"]
        self.b_bottom = blit_row["b_bottom"]


class ShapeModel:
    def __init__(self, shapes_rows, blits_rows):
        self.shapes = {}

        for row in shapes_rows:
            shape = Shape(row)
            self.shapes[shape.id] = shape

        for row in blits_rows:
            occ = Occurrence(row)
            shape = self.shapes.get(occ.shape_id)
            if shape:
                shape.occurrences.append(occ)
                shape.usage_count += 1

        self.root_shapes = []
        self._build_tree()
        self._compute_depths()
        self._compute_subtree_counts()

    # -------------------------------------------------

    def _build_tree(self):
        for shape in self.shapes.values():
            if shape.parent_id and shape.parent_id in self.shapes:
                parent = self.shapes[shape.parent_id]
                parent.children.append(shape)
            else:
                self.root_shapes.append(shape)

    # -------------------------------------------------

    def _compute_depths(self):
        for root in self.root_shapes:
            self._set_depth(root, 0)

    def _set_depth(self, shape, depth):
        shape.depth = depth
        for child in shape.children:
            self._set_depth(child, depth + 1)

    # -------------------------------------------------

    def _compute_subtree_counts(self):
        for root in self.root_shapes:
            self._compute_subtree(root)

    def _compute_subtree(self, shape):
        total = shape.usage_count
        for child in shape.children:
            total += self._compute_subtree(child)
        shape.subtree_count = total
        return total

    # -------------------------------------------------

    def get_root_shapes(self):
        return self.root_shapes
