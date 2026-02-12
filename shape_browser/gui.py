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

        # Selection state
        self.shape_positions = {}
        self.index_by_shape_id = {}
        self.current_index = None
        self.current_highlight = None

        # Panel state
        self.panel_visible = True

        self.root.title("Shape Browser")

        self._build_layout()
        self._draw_all_shapes()
        self._bind_keys()

        self.root.focus_set()

    # -------------------------------------------------
    # Layout
    # -------------------------------------------------

    def _build_layout(self):
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True)

        # Toggle button
        self.toggle_button = ttk.Button(
            self.main_frame,
            text="Hide panel",
            command=self._toggle_panel,
        )
        self.toggle_button.pack(side="top", anchor="ne", padx=5, pady=5)

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
    # Drawing
    # -------------------------------------------------

    def _draw_all_shapes(self):
        tile = self.tile_size
        columns = self.columns

        for index, shape in enumerate(self.shapes):
            row = index // columns
            col = index % columns

            self.shape_positions[shape.id] = (row, col)
            self.index_by_shape_id[shape.id] = index

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
        self.current_index = self.index_by_shape_id[shape.id]
        self._highlight_shape(shape)
        self._update_side_panel(shape)

    def _highlight_shape(self, shape):
        tile = self.tile_size

        if self.current_highlight is not None:
            self.canvas.delete(self.current_highlight)

        row, col = self.shape_positions[shape.id]

        left = col * tile
        top = row * tile
        right = left + tile
        bottom = top + tile

        self.current_highlight = self.canvas.create_rectangle(
            left,
            top,
            right,
            bottom,
            outline="red",
            width=2,
        )

    # -------------------------------------------------
    # Arrow Key Navigation
    # -------------------------------------------------

    def _bind_keys(self):
        self.root.bind("<Left>", self._move_left)
        self.root.bind("<Right>", self._move_right)
        self.root.bind("<Up>", self._move_up)
        self.root.bind("<Down>", self._move_down)

        self.root.bind("<Next>", self._page_down)
        self.root.bind("<Prior>", self._page_up)
        self.root.bind("<Home>", self._go_top)
        self.root.bind("<End>", self._go_bottom)

    def _move_left(self, event=None):
        if self.current_index is None:
            return
        if self.current_index % self.columns > 0:
            self._select_by_index(self.current_index - 1)

    def _move_right(self, event=None):
        if self.current_index is None:
            return
        if self.current_index < len(self.shapes) - 1:
            if self.current_index % self.columns < self.columns - 1:
                self._select_by_index(self.current_index + 1)

    def _move_up(self, event=None):
        if self.current_index is None:
            return
        target = self.current_index - self.columns
        if target >= 0:
            self._select_by_index(target)

    def _move_down(self, event=None):
        if self.current_index is None:
            return
        target = self.current_index + self.columns
        if target < len(self.shapes):
            self._select_by_index(target)

    def _select_by_index(self, index):
        shape = self.shapes[index]
        self.current_index = index
        self._highlight_shape(shape)
        self._update_side_panel(shape)

    # -------------------------------------------------
    # Scroll Navigation
    # -------------------------------------------------

    def _page_down(self, event=None):
        self.canvas.yview_scroll(1, "page")

    def _page_up(self, event=None):
        self.canvas.yview_scroll(-1, "page")

    def _go_top(self, event=None):
        self.canvas.yview_moveto(0)

    def _go_bottom(self, event=None):
        self.canvas.yview_moveto(1)

    # -------------------------------------------------
    # Panel Toggle
    # -------------------------------------------------

    def _toggle_panel(self):
        if self.panel_visible:
            self.side_panel.pack_forget()
            self.toggle_button.config(text="Show panel")
            self.panel_visible = False
        else:
            self.side_panel.pack(side="right", fill="y")
            self.toggle_button.config(text="Hide panel")
            self.panel_visible = True

    # -------------------------------------------------
    # Side Panel Update
    # -------------------------------------------------

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
