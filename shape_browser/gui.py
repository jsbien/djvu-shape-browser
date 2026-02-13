import tkinter as tk
from tkinter import ttk, messagebox


PROGRAM_NAME = "Shape Browser"


class ShapeBrowserGUI:
    def __init__(
        self,
        root,
        model,
        renderer,
        tile_size,
        database_name,
        version,
        build_timestamp,
    ):
        self.root = root
        self.model = model
        self.renderer = renderer
        self.tile_size = tile_size
        self.database_name = database_name
        self.version = version
        self.build_timestamp = build_timestamp

        # Full tree internally
        self.all_shapes = sorted(
            self.model.shapes.values(),
            key=lambda s: s.height,
            reverse=True,
        )

        self.filtered_shapes = self.all_shapes

        self.columns = 6

        self.shape_positions = {}
        self.index_by_shape_id = {}
        self.current_index = None
        self.current_highlight = None

        self.panel_visible = True

        self.root.title(f"{PROGRAM_NAME} {self.version}")

        self._build_menu()
        self._build_layout()

        # Default startup filter: depth = 0 (roots only)
        self.depth_max_entry.insert(0, "0")
        self._apply_filters()

        self._bind_keys()
        self._update_info_bar()

        self.root.focus_set()

    # -------------------------------------------------
    # Menu
    # -------------------------------------------------

    def _build_menu(self):
        menu_bar = tk.Menu(self.root)

        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Exit", command=self.root.quit)
        menu_bar.add_cascade(label="File", menu=file_menu)

        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="About", command=self._show_about)
        menu_bar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menu_bar)

    def _show_about(self):
        messagebox.showinfo(
            "About",
            f"{PROGRAM_NAME}\n"
            f"Version: {self.version}\n"
            f"Build: {self.build_timestamp}",
        )

    # -------------------------------------------------
    # Layout
    # -------------------------------------------------

    def _build_layout(self):
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True)

        # Info bar
        self.info_frame = ttk.Frame(self.main_frame)
        self.info_frame.pack(side="top", fill="x")

        self.info_label = ttk.Label(self.info_frame, text="")
        self.info_label.pack(side="left", padx=5, pady=5)

        # Filter bar
        self.filter_frame = ttk.Frame(self.main_frame)
        self.filter_frame.pack(side="top", fill="x")

        ttk.Label(self.filter_frame, text="Direct:").pack(side="left", padx=5)
        self.direct_min_entry = ttk.Entry(self.filter_frame, width=6)
        self.direct_min_entry.pack(side="left")
        ttk.Label(self.filter_frame, text="–").pack(side="left")
        self.direct_max_entry = ttk.Entry(self.filter_frame, width=6)
        self.direct_max_entry.pack(side="left")

        ttk.Label(self.filter_frame, text="  Subtree:").pack(side="left", padx=5)
        self.subtree_min_entry = ttk.Entry(self.filter_frame, width=6)
        self.subtree_min_entry.pack(side="left")
        ttk.Label(self.filter_frame, text="–").pack(side="left")
        self.subtree_max_entry = ttk.Entry(self.filter_frame, width=6)
        self.subtree_max_entry.pack(side="left")

        ttk.Label(self.filter_frame, text="  Height:").pack(side="left", padx=5)
        self.height_min_entry = ttk.Entry(self.filter_frame, width=6)
        self.height_min_entry.pack(side="left")
        ttk.Label(self.filter_frame, text="–").pack(side="left")
        self.height_max_entry = ttk.Entry(self.filter_frame, width=6)
        self.height_max_entry.pack(side="left")

        ttk.Label(self.filter_frame, text="  Ratio (H/W):").pack(side="left", padx=5)
        self.ratio_min_entry = ttk.Entry(self.filter_frame, width=6)
        self.ratio_min_entry.pack(side="left")
        ttk.Label(self.filter_frame, text="–").pack(side="left")
        self.ratio_max_entry = ttk.Entry(self.filter_frame, width=6)
        self.ratio_max_entry.pack(side="left")

        ttk.Label(self.filter_frame, text="  Max depth:").pack(side="left", padx=5)
        self.depth_max_entry = ttk.Entry(self.filter_frame, width=4)
        self.depth_max_entry.pack(side="left")

        self.apply_button = ttk.Button(
            self.filter_frame,
            text="Apply",
            command=self._apply_filters,
        )
        self.apply_button.pack(side="left", padx=5)

        self.clear_button = ttk.Button(
            self.filter_frame,
            text="Clear",
            command=self._clear_filters,
        )
        self.clear_button.pack(side="left", padx=5)

        # Toggle panel
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

    # -------------------------------------------------
    # Filtering
    # -------------------------------------------------

    def _apply_filters(self):
        def parse_int(entry):
            value = entry.get().strip()
            if not value:
                return None
            try:
                return int(value)
            except ValueError:
                return None

        def parse_float(entry):
            value = entry.get().strip()
            if not value:
                return None
            try:
                return float(value)
            except ValueError:
                return None

        direct_min = parse_int(self.direct_min_entry)
        direct_max = parse_int(self.direct_max_entry)
        subtree_min = parse_int(self.subtree_min_entry)
        subtree_max = parse_int(self.subtree_max_entry)
        height_min = parse_int(self.height_min_entry)
        height_max = parse_int(self.height_max_entry)
        ratio_min = parse_float(self.ratio_min_entry)
        ratio_max = parse_float(self.ratio_max_entry)
        depth_max = parse_int(self.depth_max_entry)

        filtered = []

        for shape in self.all_shapes:

            if direct_min is not None and shape.usage_count < direct_min:
                continue
            if direct_max is not None and shape.usage_count > direct_max:
                continue

            if subtree_min is not None and shape.subtree_count < subtree_min:
                continue
            if subtree_max is not None and shape.subtree_count > subtree_max:
                continue

            if height_min is not None and shape.height < height_min:
                continue
            if height_max is not None and shape.height > height_max:
                continue

            ratio = shape.height / shape.width if shape.width else 0
            if ratio_min is not None and ratio < ratio_min:
                continue
            if ratio_max is not None and ratio > ratio_max:
                continue

            if depth_max is not None and shape.depth > depth_max:
                continue

            filtered.append(shape)

        self.filtered_shapes = filtered
        self.current_index = None
        self.current_highlight = None

        self._draw_all_shapes()
        self._update_info_bar()

    def _clear_filters(self):
        for entry in [
            self.direct_min_entry,
            self.direct_max_entry,
            self.subtree_min_entry,
            self.subtree_max_entry,
            self.height_min_entry,
            self.height_max_entry,
            self.ratio_min_entry,
            self.ratio_max_entry,
            self.depth_max_entry,
        ]:
            entry.delete(0, tk.END)

        self.filtered_shapes = self.all_shapes
        self.current_index = None
        self.current_highlight = None

        self._draw_all_shapes()
        self._update_info_bar()

    # -------------------------------------------------
    # Info bar
    # -------------------------------------------------

    def _update_info_bar(self):
        total = len(self.all_shapes)
        shown = len(self.filtered_shapes)

        text = (
            f"{PROGRAM_NAME} {self.version} "
            f"({self.build_timestamp})  |  "
            f"DB: {self.database_name}  |  "
            f"Showing: {shown} / {total}"
        )

        self.info_label.config(text=text)

    # -------------------------------------------------
    # Drawing
    # -------------------------------------------------

    def _draw_all_shapes(self):
        self.canvas.delete("all")
        self._image_refs = []

        tile = self.tile_size
        columns = self.columns

        self.shape_positions.clear()
        self.index_by_shape_id.clear()

        for index, shape in enumerate(self.filtered_shapes):
            row = index // columns
            col = index % columns

            self.shape_positions[shape.id] = (row, col)
            self.index_by_shape_id[shape.id] = index

            x = col * tile + tile // 2
            y = row * tile + tile // 2

            tk_image = self.renderer.get_tk_image(shape, tile)
            self._image_refs.append(tk_image)

            item = self.canvas.create_image(x, y, image=tk_image)

            self.canvas.tag_bind(
                item,
                "<Button-1>",
                lambda e, s=shape: self._on_select(s),
            )

        total_rows = (len(self.filtered_shapes) + columns - 1) // columns
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
            left, top, right, bottom,
            outline="red",
            width=2,
        )

    def _update_side_panel(self, shape):
        ratio = shape.height / shape.width if shape.width else 0

        metadata = (
            f"Shape ID: {shape.id}\n"
            f"Size: {shape.width} x {shape.height}\n"
            f"Ratio (H/W): {ratio:.3f}\n"
            f"Depth: {shape.depth}\n"
            f"Direct usage: {shape.usage_count}\n"
            f"Subtree usage: {shape.subtree_count}\n"
            f"Children: {len(shape.children)}\n"
            f"Parent ID: {shape.parent_id}\n"
        )

        self.metadata_label.config(text=metadata)

    # -------------------------------------------------
    # Keyboard navigation
    # -------------------------------------------------

    def _bind_keys(self):
        self.root.bind("<Left>", self._move_left)
        self.root.bind("<Right>", self._move_right)
        self.root.bind("<Up>", self._move_up)
        self.root.bind("<Down>", self._move_down)

    def _move_left(self, event=None):
        if self.current_index is None:
            return
        if self.current_index % self.columns > 0:
            self._select_by_index(self.current_index - 1)

    def _move_right(self, event=None):
        if self.current_index is None:
            return
        if self.current_index < len(self.filtered_shapes) - 1:
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
        if target < len(self.filtered_shapes):
            self._select_by_index(target)

    def _select_by_index(self, index):
        shape = self.filtered_shapes[index]
        self.current_index = index
        self._highlight_shape(shape)
        self._update_side_panel(shape)

    # -------------------------------------------------
    # Panel toggle
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
