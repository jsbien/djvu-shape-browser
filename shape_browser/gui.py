import tkinter as tk
from tkinter import ttk, messagebox

PROGRAM_NAME = "Shape Browser"


class ShapeBrowserGUI:
    def __init__(
        self,
        root,
        model,
        renderer,
        database_name,
        version,
        build_timestamp,
        djview_launcher,
        tile_size=140,
        page_size=600,   # how many shapes per page
    ):
        self.root = root
        self.model = model
        self.repo = model.repo
        self.renderer = renderer
        self.database_name = database_name
        self.version = version
        self.build_timestamp = build_timestamp
        self.djview = djview_launcher

        self.tile_size = tile_size
        self.columns = 6
        self.page_size = page_size

        # Paging state
        self.offset = 0
        self.total_count = 0

        # Mode state
        self.mode = "global"          # "global" or "subtree"
        self.subtree_root_id = None   # shape id
        self.current_subtree_root = None

        # Selection
        self.current_index = None
        self.border_by_shape_id = {}
        self.selected_shape_id = None
        self.occurrences_visible = False

        self.root.title(f"{PROGRAM_NAME} {self.version}")
        self._build_menu()
        self._build_layout()
        self._bind_keys()

        # default filter: roots only
        self.depth_max_entry.insert(0, "0")

        # initial load
        self._reload()

        self.root.focus_set()

    # -------------------------------------------------
    # Menu
    # -------------------------------------------------

    def _build_menu(self):
        menu_bar = tk.Menu(self.root)
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Exit", command=self.root.quit)
        menu_bar.add_cascade(label="File", menu=file_menu)
        self.root.config(menu=menu_bar)

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
        self.info_label.pack(side="left", padx=5)

        self.back_button = ttk.Button(
            self.info_frame,
            text="Back",
            command=self._exit_subtree_mode,
        )

        # Filter row
        self.filter_frame = ttk.Frame(self.main_frame)
        self.filter_frame.pack(side="top", fill="x", pady=4)

        ttk.Label(self.filter_frame, text="Direct:").pack(side="left")
        self.direct_min = ttk.Entry(self.filter_frame, width=4)
        self.direct_min.pack(side="left")
        ttk.Label(self.filter_frame, text="-").pack(side="left")
        self.direct_max = ttk.Entry(self.filter_frame, width=4)
        self.direct_max.pack(side="left")

        ttk.Label(self.filter_frame, text="  Subtree:").pack(side="left")
        self.subtree_min = ttk.Entry(self.filter_frame, width=4)
        self.subtree_min.pack(side="left")
        ttk.Label(self.filter_frame, text="-").pack(side="left")
        self.subtree_max = ttk.Entry(self.filter_frame, width=4)
        self.subtree_max.pack(side="left")

        ttk.Label(self.filter_frame, text="  Height:").pack(side="left")
        self.height_min = ttk.Entry(self.filter_frame, width=4)
        self.height_min.pack(side="left")
        ttk.Label(self.filter_frame, text="-").pack(side="left")
        self.height_max = ttk.Entry(self.filter_frame, width=4)
        self.height_max.pack(side="left")

        ttk.Label(self.filter_frame, text="  Ratio (H/W):").pack(side="left")
        self.ratio_min = ttk.Entry(self.filter_frame, width=4)
        self.ratio_min.pack(side="left")
        ttk.Label(self.filter_frame, text="-").pack(side="left")
        self.ratio_max = ttk.Entry(self.filter_frame, width=4)
        self.ratio_max.pack(side="left")

        ttk.Label(self.filter_frame, text="  Max depth:").pack(side="left")
        self.depth_max_entry = ttk.Entry(self.filter_frame, width=4)
        self.depth_max_entry.pack(side="left")

        ttk.Button(self.filter_frame, text="Apply", command=self._apply_filters).pack(side="left", padx=5)
        ttk.Button(self.filter_frame, text="Clear", command=self._clear_filters).pack(side="left")

        # Paging controls
        ttk.Button(self.filter_frame, text="Prev", command=self._prev_page).pack(side="right", padx=4)
        ttk.Button(self.filter_frame, text="Next", command=self._next_page).pack(side="right")

        # Canvas + scrollbar
        self.canvas = tk.Canvas(self.main_frame)
        self.scrollbar = ttk.Scrollbar(self.main_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        # Clicking anywhere selects by cell
        self.canvas.bind("<Button-1>", self._on_canvas_click)

        # Side panel
        self.side_panel = ttk.Frame(self.root, width=340)
        self.side_panel.pack(side="right", fill="y")

    # -------------------------------------------------
    # Filter parsing
    # -------------------------------------------------

    def _get_int(self, entry):
        s = entry.get().strip()
        if not s:
            return None
        try:
            return int(s)
        except ValueError:
            return None

    def _get_float(self, entry):
        s = entry.get().strip()
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None

    def _current_filters(self):
        return {
            "depth_max": self._get_int(self.depth_max_entry),
            "direct_min": self._get_int(self.direct_min),
            "direct_max": self._get_int(self.direct_max),
            "subtree_min": self._get_int(self.subtree_min),
            "subtree_max": self._get_int(self.subtree_max),
            "height_min": self._get_int(self.height_min),
            "height_max": self._get_int(self.height_max),
            "ratio_min": self._get_float(self.ratio_min),
            "ratio_max": self._get_float(self.ratio_max),
        }

    # -------------------------------------------------
    # Data reload / paging
    # -------------------------------------------------

    def _reload(self):
        f = self._current_filters()

        self.total_count = self.repo.count_shapes(
            document_id=self.model.document_id,
            mode=self.mode,
            subtree_root_id=self.subtree_root_id,
            **f,
        )

        rows = self.repo.fetch_shapes_page(
            document_id=self.model.document_id,
            offset=self.offset,
            limit=self.page_size,
            mode=self.mode,
            subtree_root_id=self.subtree_root_id,
            **f,
        )

        self.model.set_current_page(rows)

        # bits only for displayed shapes
        ids = [s.id for s in self.model.current_shapes]
        self.model.ensure_bits_loaded(ids)

        self.current_index = None
        self.selected_shape_id = None
        self._draw_page()
        self._update_info_bar()

    def _apply_filters(self):
        self.offset = 0
        self._reload()

    def _clear_filters(self):
        for e in (
            self.direct_min, self.direct_max,
            self.subtree_min, self.subtree_max,
            self.height_min, self.height_max,
            self.ratio_min, self.ratio_max,
            self.depth_max_entry,
        ):
            e.delete(0, tk.END)
        self.depth_max_entry.insert(0, "0")
        self.offset = 0
        self._reload()

    def _next_page(self):
        if self.offset + self.page_size < self.total_count:
            self.offset += self.page_size
            self._reload()

    def _prev_page(self):
        if self.offset > 0:
            self.offset = max(0, self.offset - self.page_size)
            self._reload()

    # -------------------------------------------------
    # Subtree mode
    # -------------------------------------------------

    def _enter_subtree_mode(self, root_shape):
        # Root shape id is enough; subtree is SQL-backed (sb_shape_tree)
        self.mode = "subtree"
        self.subtree_root_id = root_shape.id
        self.current_subtree_root = root_shape
        self.back_button.pack(side="right", padx=5)
        self.offset = 0
        self._reload()

    def _exit_subtree_mode(self):
        self.mode = "global"
        self.subtree_root_id = None
        self.current_subtree_root = None
        self.back_button.pack_forget()
        self.offset = 0
        self._reload()

    # -------------------------------------------------
    # Info bar
    # -------------------------------------------------

    def _update_info_bar(self):
        shown = len(self.model.current_shapes)
        total = self.total_count

        if self.mode == "subtree" and self.current_subtree_root is not None:
            text = (
                f"{PROGRAM_NAME} {self.version} ({self.build_timestamp}) | "
                f"DB: {self.database_name} | "
                f"Subtree of {self.current_subtree_root.id} | "
                f"Showing: {shown} / {total} | "
                f"Offset: {self.offset}"
            )
        else:
            text = (
                f"{PROGRAM_NAME} {self.version} ({self.build_timestamp}) | "
                f"DB: {self.database_name} | "
                f"Showing: {shown} / {total} | "
                f"Offset: {self.offset}"
            )

        self.info_label.config(text=text)

    # -------------------------------------------------
    # Drawing
    # -------------------------------------------------

    def _draw_page(self):
        self.canvas.delete("all")
        self.border_by_shape_id.clear()

        tile = self.tile_size
        cols = self.columns

        # Keep image refs to prevent GC
        self._image_refs = []

        for idx, shape in enumerate(self.model.current_shapes):
            row = idx // cols
            col = idx % cols

            x = col * tile + tile // 2
            y = row * tile + tile // 2

            # Render thumbnail
            tk_img = self.renderer.get_tk_image(shape, tile)
            self._image_refs.append(tk_img)

            self.canvas.create_image(x, y, image=tk_img)

            # Cell border (default gray)
            border_id = self.canvas.create_rectangle(
                col * tile, row * tile,
                col * tile + tile, row * tile + tile,
                outline="#c0c0c0",
                width=1,
            )
            self.border_by_shape_id[shape.id] = border_id

            # Badge: depth:sibling (p:parent)
            pid = shape.parent_id if shape.parent_id is not None else "-"
            badge = f"{shape.depth}:{shape.sibling_index} (p:{pid})"
            text_id = self.canvas.create_text(
                col * tile + 4,
                row * tile + 4,
                anchor="nw",
                text=badge,
                font=("TkDefaultFont", 8),
                fill="black",
            )
            bbox = self.canvas.bbox(text_id)
            rect_id = self.canvas.create_rectangle(bbox, fill="white", outline="")
            self.canvas.tag_raise(text_id, rect_id)

        total_rows = (len(self.model.current_shapes) + cols - 1) // cols
        self.canvas.configure(scrollregion=(0, 0, cols * tile, total_rows * tile))

    # -------------------------------------------------
    # Click / selection
    # -------------------------------------------------

    def _on_canvas_click(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        tile = self.tile_size

        col = int(cx // tile)
        row = int(cy // tile)
        idx = row * self.columns + col

        if 0 <= idx < len(self.model.current_shapes):
            shape = self.model.current_shapes[idx]
            self._on_click(event, shape)
        return "break"

    def _on_click(self, event, shape):
        # Ctrl-click enters subtree mode
        if event.state & 0x0004:
            self._enter_subtree_mode(shape)
        else:
            self._select_shape(shape)
        return "break"

    def _select_shape(self, shape):
        # reset previous border
        if self.selected_shape_id is not None:
            old = self.border_by_shape_id.get(self.selected_shape_id)
            if old is not None:
                self.canvas.itemconfigure(old, outline="#c0c0c0", width=1)

        self.selected_shape_id = shape.id
        new = self.border_by_shape_id.get(shape.id)
        if new is not None:
            self.canvas.itemconfigure(new, outline="red", width=2)
            self.canvas.tag_raise(new)

        self._update_side_panel(shape)

    # -------------------------------------------------
    # Side panel / occurrences
    # -------------------------------------------------

    def _update_side_panel(self, shape):
        for w in self.side_panel.winfo_children():
            w.destroy()

        ratio = shape.ratio_hw

        ttk.Label(
            self.side_panel,
            text=(
                f"Shape ID: {shape.id}\n"
                f"Dictionary: {shape.dictionary_id}\n"
                f"Parent: {shape.parent_id}\n"
                f"Size: {shape.width} x {shape.height}\n"
                f"Ratio (H/W): {ratio:.3f}\n"
                f"Depth: {shape.depth}\n"
                f"Usage: {shape.usage_count}\n"
                f"Subtree usage: {shape.subtree_count}"
            ),
            justify="left",
        ).pack(anchor="nw", padx=10, pady=5)

        occs = self.model.get_occurrences(shape)
        if not occs:
            return

        page_groups = {}
        for occ in occs:
            page_groups.setdefault(occ.page_number, []).append(occ)

        header = ttk.Frame(self.side_panel)
        header.pack(anchor="nw", fill="x", padx=10, pady=5)

        ttk.Label(
            header,
            text=f"Occurrences: {len(occs)} ({len(page_groups)} pages)",
        ).pack(side="left")

        ttk.Button(
            header,
            text="Hide" if self.occurrences_visible else "Show",
            width=6,
            command=lambda s=shape: self._toggle_occurrences(s),
        ).pack(side="right")

        if not self.occurrences_visible:
            return

        for page in sorted(page_groups.keys()):
            occ_list = page_groups[page]

            # Page button: open all occurrences (page number displayed 1-based)
            page_btn = ttk.Button(
                self.side_panel,
                text=f"Page {page + 1} ({len(occ_list)})",
                command=lambda p=page, s=shape, o=occ_list: self.djview.open_occurrences(p, s, o),
            )
            page_btn.pack(anchor="nw", padx=20, pady=(2, 0))

            # Each occurrence: open single occurrence
            for i, occ in enumerate(occ_list, 1):
                occ_btn = ttk.Button(
                    self.side_panel,
                    text=f"  #{i}  x={occ.x} y={occ.y}",
                    command=lambda s=shape, oc=occ: self.djview.open_single_occurrence(oc.page_number, s, oc),
                )
                occ_btn.pack(anchor="nw", padx=35, pady=1)

    def _toggle_occurrences(self, shape):
        self.occurrences_visible = not self.occurrences_visible
        self._update_side_panel(shape)

    # -------------------------------------------------
    # Keyboard navigation (within current page only)
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
        if self.current_index < len(self.model.current_shapes) - 1:
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
        if target < len(self.model.current_shapes):
            self._select_by_index(target)

    def _select_by_index(self, idx):
        shape = self.model.current_shapes[idx]
        self.current_index = idx
        self._select_shape(shape)
        
