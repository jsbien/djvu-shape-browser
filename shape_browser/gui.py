import tkinter as tk
from tkinter import ttk


class ShapeBrowserGUI:
    def __init__(self, root, model, renderer):
        self.root = root
        self.model = model
        self.renderer = renderer

        self.root.title("Shape Browser")

        self._build_layout()
        self._populate_tree()

    # -------------------------
    # Layout
    # -------------------------

    def _build_layout(self):
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True)

        # Left: Tree
        self.tree = ttk.Treeview(self.main_frame)
        self.tree.pack(side="left", fill="both", expand=True)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # Right: Preview frame
        self.preview_frame = ttk.Frame(self.main_frame)
        self.preview_frame.pack(side="right", fill="both", expand=True)

        # Metadata label
        self.metadata_label = ttk.Label(
            self.preview_frame,
            text="Select a shape",
            justify="left"
        )
        self.metadata_label.pack(anchor="nw", padx=10, pady=10)

        # Image label
        self.image_label = ttk.Label(self.preview_frame)
        self.image_label.pack(anchor="center", padx=10, pady=10)

    # -------------------------
    # Tree Population
    # -------------------------

    def _populate_tree(self):
        for shape in self.model.root_shapes:
            self._insert_shape("", shape)

    def _insert_shape(self, parent_node, shape):
        label = f"[{shape.depth}] Shape {shape.id} (h={shape.height})"

        node_id = self.tree.insert(
            parent_node,
            "end",
            text=label,
            values=(shape.id,)
        )

        for child in shape.children:
            self._insert_shape(node_id, child)

    # -------------------------
    # Selection Handling
    # -------------------------

    def _on_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return

        node = selected[0]

        # Extract shape ID from label
        text = self.tree.item(node, "text")
        shape_id = int(text.split("Shape ")[1].split()[0])

        shape = self.model.get_shape(shape_id)
        self._update_preview(shape)

    # -------------------------
    # Preview Update
    # -------------------------

    def _update_preview(self, shape):
        metadata = (
            f"Shape ID: {shape.id}\n"
            f"Parent ID: {shape.parent_id}\n"
            f"Depth: {shape.depth}\n"
            f"Usage count: {shape.usage_count}\n"
            f"Children: {len(shape.children)}\n"
            f"Size: {shape.width} x {shape.height}"
        )

        self.metadata_label.config(text=metadata)

        tk_image = self.renderer.get_tk_image(shape)
        self.image_label.config(image=tk_image)
        self.image_label.image = tk_image  # keep reference
