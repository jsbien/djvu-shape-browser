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

        self.all_shapes = self.model.root_shapes
        self.filtered_shapes = self.all_shapes

        self.columns = 6

        # Selection state
        self.shape_positions = {}
        self.index_by_shape_id = {}
        self.current_index = None
        self.current_highlight = None

        # Panel state
        self.panel_visible = True

        self.root.title(f"{PROGRAM_NAME} {self.version}")

        self._build_menu()
        self._build_layout()
        self._draw_all_shapes()
        self._bind_keys()
        self._update_info_bar()

        self.root.focus_set()

    # -------------------------------------------------
    # Menu
    # -------------------------------------------------

    def _build_menu(self):
        self.menu_bar = tk.Menu(self.root)

        # File menu (placeholder)
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        file_menu.add_command(label="Exit", command=self.root.quit)
        self.menu_bar.add_cascade(label="File", menu=file_menu)

        # Help menu
        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        help_menu.add_command(label="About", command=self._show_about)
        self.menu_bar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=self.menu_bar)

    def _show_about(self):
        messagebox.showinfo(
            "About",
            f"{PROGRAM_NAME}\n"
            f"Version: {self.version}\n"
            f"Build: {self.build_timestamp}\n\n"
            f"Glyph shape browsing tool.",
        )

    # -------------------------------------------------
    # Layout
    # -------------------------------------------------

    def _build_layout(self):
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True)

        # ---------------------------
        # Info bar
        # ---------------------------
        self.info_frame = ttk.Frame(self.main_frame)
        self.info_frame.pack(side="top", fill="x")

        self.info_label = ttk.Label(self.info_frame, text="")
        self.info_label.pack(side="left", padx=5, pady=5)

        # ---------------------------
        # Filter bar (skeleton)
        # ---------------------------
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

        ttk.Label(self.filter_frame, text="  Ratio:").pack(side="left", padx=5)
        self.ratio_min_entry = ttk.Entry(self.filter_frame, width=6)
        self.ratio_min_entry.pack(side="left")
        ttk.Label(self.filter_frame, text="–").pack(side="left")
        self.ratio_max_entry = ttk.Entry(self.filter_frame, width=6)
        self.ratio_max_entry.pack(side="left")

        self.apply_button = ttk.Button(
            self.filter_frame,
            text="Apply",
            command=self._apply_filters_placeholder,
        )
        self.apply_button.pack(side="left", padx=10)

        # Toggle panel button
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
    # Info Bar Update
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
    # Placeholder filter
    # -------------------------------------------------

    def _apply_filters_placeholder(self):
        print("Filtering not implemented yet.")

    # -------------------------------------------------
    # Drawing / navigation methods unchanged...
    # (Keep your previous navigation, selection, scroll logic here)
    # -------------------------------------------------
