import tkinter as tk
from tkinter import ttk


class ShapeBrowserGUI:
    def __init__(
        self,
        root,
        model,
        renderer,
        tile_size,
        database_name,
        version,
    ):
        self.root = root
        self.model = model
        self.renderer = renderer
        self.tile_size = tile_size
        self.database_name = database_name
        self.version = version

        self.shapes = self.model.root_shapes
        self.columns = 6

        self.root.title("Shape Browser")

        self._build_layout()
        self._draw_all_shapes()

    # -------------------------------------------------
    # Layout
    # -------------------------------------------------

    def _build_layout(self):
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True)

        # Canvas
        self.canvas = tk.Canvas(self.main_frame)
        self.scrollbar = ttk.Scrollbar(
            self.main_frame,
            orient="vertical",
            command=self.canvas.yview,
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        # Side panel
        self.side_panel = ttk.Frame(self.root, width=300)
        self.side_panel.pack(side="right", fill="y")

        self.metadata_label = ttk.Label(
            self.side_panel,
            text="Select a shape",
            justify="left",
        )
        self.metadata_label.pack(anchor="nw", padx=10, pady=10)

        self.occurrence_label = ttk.Label(
            self.side_panel,
            text="",
            justify="left",
        )
        self.occurrence_label.pack(anchor="nw", padx=10, pady=10)

    # -------------------------------------------------
    # Canvas Drawing
    # -------------------------------------------------

    def _draw_all_shapes(self):
        tile = self.tile_size
        columns = self.columns

        for index, shape in enumerate(self.shapes):
            row = index // columns
            col = index % columns

            x = col * tile + tile // 2
            y = row * tile + tile // 2

            tk_image = self.renderer.get_tk_image(shape, tile)

            item = self.canvas.create_image(x, y, image=tk_image)
            self.canvas.tag_bind(
                item,
                "<Button-1>",
                lambda e, s=shape: self._on_select(s),
            )

        total_rows = (len(self.shapes) + columns - 1) // columns
        total_height = total_rows * tile

        self.canvas.configure(
            scrollregion=(0, 0, columns * tile, total_height)
        )

    # -------------------------------------------------
    # Selection
    # -------------------------------------------------

    def _on_select(self, shape):
        self._update_side_panel(shape)

    def _update_side_panel(self, shape):
        metadata = (
            f"Shape ID: {shape.id}\n"
            f"Size: {shape.width} x {shape.height}\n"
            f"Depth: {shape.depth}\n"
            f"Usage count: {shape.usage_count}\n"
            f"Children: {len(shape.children)}\n"
            f"Parent ID: {shape.parent_id}\n"
        )

        self.metadata_label.config(text=metadata)

        occurrences = "\n".join(
            f"Page {occ.page_number}"
            for occ in shape.occurrences[:50]
        )

        self.occurrence_label.config(text=occurrences)
