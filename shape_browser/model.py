class Shape:
    def __init__(self, row):
        self.id = int(row["id"])
        self.dictionary_id = int(row["dictionary_id"])
        self.parent_id = row["parent_id"]
        self.parent_id = int(self.parent_id) if self.parent_id is not None else None

        self.width = int(row["width"])
        self.height = int(row["height"])

        self.depth = int(row.get("depth", 0))
        self.sibling_index = int(row.get("sibling_index", 0))

        self.usage_count = int(row.get("usage_count", 0))
        self.subtree_count = int(row.get("subtree_usage", 0))

        self.ratio_hw = float(row.get("ratio_hw", 0.0))

        # Filled later (on-demand) for rendering
        self.bits = None

        # Filled later (on-demand) for occurrences panel
        self.occurrences = None


class Occurrence:
    def __init__(self, row):
        self.shape_id = int(row["shape_id"])
        self.page_number = int(row["page_number"])
        self.x = int(row["b_left"])
        self.y = int(row["b_bottom"])


class ShapeModel:
    """
    Thin model: holds current result page and fetches occurrences lazily.
    """

    def __init__(self, repo, document_id):
        self.repo = repo
        self.document_id = int(document_id)

        self.current_shapes = []          # list[Shape]
        self.shape_by_id = {}             # id -> Shape

    def set_current_page(self, rows):
        self.current_shapes = []
        self.shape_by_id = {}

        for r in rows:
            s = Shape(r)
            self.current_shapes.append(s)
            self.shape_by_id[s.id] = s

    def ensure_bits_loaded(self, shape_ids):
        missing = [sid for sid in shape_ids if self.shape_by_id[sid].bits is None]
        if not missing:
            return
        bits_map = self.repo.fetch_bits_for_shape_ids(missing)
        for sid, bits in bits_map.items():
            if sid in self.shape_by_id:
                self.shape_by_id[sid].bits = bits

    def get_occurrences(self, shape):
        if shape.occurrences is not None:
            return shape.occurrences
        rows = self.repo.fetch_occurrences(self.document_id, shape.id)
        shape.occurrences = [Occurrence(r) for r in rows]
        return shape.occurrences
    
