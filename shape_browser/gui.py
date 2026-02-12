from PIL import Image, ImageTk
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

        self.selected_shape = None

        self.root.title("Shape Browser")

        self._build_layout()
        self._populate_grid()

    # -------------------------------------------------
    # Layout
    # -------------------------------------------------

    def _build_layout(self):
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True)

        # Left: scrollable canvas for grid
        self.canvas = tk.Canvas(self.main_frame)
        self.scrollbar = ttk.Scrollbar(
            self.main_frame,
            orient="vertical",
            command=self.canvas.yview,
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        # Internal frame inside canvas
        self.grid_frame = ttk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.grid_frame, anchor="nw")

        self.grid_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            ),
        )

        # Right: side panel
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
    # Grid Population
    # -------------------------------------------------

    def _populate_grid(self):
        print("Populating grid...")
        shapes = self.model.root_shapes
        columns = 6  # fixed for now

        for index, shape in enumerate(shapes):
            if index % 50 == 0:
                print(index)

            row = index // columns
            col = index % columns

            tile = self._create_tile(shape)
            tile.grid(row=row, column=col, padx=5, pady=5)

    def _create_tile(self, shape):
        frame = ttk.Frame(
            self.grid_frame,
            width=self.tile_size,
            height=self.tile_size,
        )
        frame.grid_propagate(False)

        pil_image = self.renderer.get_pil_image(shape)

        # Scale if needed
        max_size = self.tile_size - 10
        w, h = pil_image.size

        if w > max_size or h > max_size:
            scale = min(max_size / w, max_size / h)
            new_w = int(w * scale)
            new_h = int(h * scale)
            pil_image = pil_image.resize((new_w, new_h), Image.NEAREST)

        tk_image = ImageTk.PhotoImage(pil_image)

        label = ttk.Label(frame, image=tk_image)
        label.image = tk_image
        label.pack(expand=True)

        label.bind("<Button-1>", lambda e, s=shape: self._on_select(s))

        return frame
    
    def _create_tile(self, shape):
        frame = ttk.Frame(
            self.grid_frame,
            width=self.tile_size,
            height=self.tile_size,
        )
        frame.grid_propagate(False)

        pil_image = self.renderer.get_pil_image(shape)

        max_size = self.tile_size - 10
        w, h = pil_image.size

        if w > max_size or h > max_size:
            scale = min(max_size / w, max_size / h)
            new_w = max(1, int(w * scale))
            new_h = max(1, int(h * scale))
            pil_image = pil_image.resize((new_w, new_h), Image.NEAREST)

        tk_image = ImageTk.PhotoImage(pil_image)

        label = ttk.Label(frame, image=tk_image)
        label.image = tk_image
        label.pack(expand=True)

        label.bind("<Button-1>", lambda e, s=shape: self._on_select(s))

        return frame


    # -------------------------------------------------
    # Selection
    # -------------------------------------------------

    def _on_select(self, shape):
        self.selected_shape = shape
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
