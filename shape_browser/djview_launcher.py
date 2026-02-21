import subprocess
import logging

LOG_FILE = "shape_browser_djview.log"


class DjViewLauncher:
    """
    Responsible for constructing djview4 URLs and launching djview4.
    Also writes a structured debug log of each launch.

    Assumptions:
    - `page_info_provider` exists and works (djvudump availability checked elsewhere).
    - Occurrence coordinates (occ.x/occ.y) are in the same coordinate system expected
      by djview's highlight (if not, we'll adjust later using page height).
    """

    def __init__(self, document_path, page_info_provider):
        self.document_path = document_path
        self.page_info = page_info_provider
        self._setup_logging()

    # -------------------------------------------------
    # Logging setup
    # -------------------------------------------------

    def _setup_logging(self):
        self.logger = logging.getLogger("DjViewLauncher")
        self.logger.setLevel(logging.INFO)

        # Prevent duplicate handlers if multiple launcher instances are created
        if not self.logger.handlers:
            file_handler = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
            formatter = logging.Formatter("%(asctime)s\n%(message)s\n")
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def open_single_occurrence(self, page_number, shape, occurrence):
        page_1based = page_number + 1

        page_w, page_h = self.page_info.get_page_size(page_number)

        x = occurrence.x
        y = occurrence.y
        w = shape.width
        h = shape.height

        center_x = x + w / 2
        center_y = y + h / 2

        px = round(center_x / page_w, 6)
        py = round((page_h - center_y) / page_h, 6)

        highlight = f"highlight={x},{y},{w},{h}"
        showposition = f"showposition={px},{py}"

        query = (
            f"djvuopts=&page={page_1based}"
            f"&zoom=width"
            f"&{highlight}"
            f"&{showposition}"
        )
        url = f"file://{self.document_path}?{query}"

        subprocess.Popen(["djview4", url])

    # def open_single_occurrence(self, page_number, shape, occurrence):
    #     """
    #     Open djview4 and highlight a single occurrence of the shape on the given page.

    #     For now, the URL style is the same as open_occurrences, just with one highlight.
    #     """
    #     page_1based = page_number + 1

    #     x = occurrence.x
    #     y = occurrence.y
    #     w = shape.width
    #     h = shape.height

    #     highlight = f"highlight={x},{y},{w},{h}"
    #     query = f"djvuopts=&page={page_1based}&{highlight}"
    #     url = f"file://{self.document_path}?{query}"

    #     # Optional: log it (recommended)
    #     if hasattr(self, "logger"):
    #         lines = []
    #         lines.append("=" * 60)
    #         lines.append("DjView Launch Mode: SINGLE")
    #         lines.append(f"Document: {self.document_path}")
    #         lines.append(f"Shape ID: {shape.id}")
    #         lines.append(f"DB page (0-based): {page_number}")
    #         lines.append("Occurrence:")
    #         lines.append(f"  x={x} y={y} w={w} h={h}")
    #         lines.append("Final URL:")
    #         lines.append(url)
    #         lines.append("=" * 60)
    #         lines.append("")
    #         self.logger.info("\n".join(lines))

    #     subprocess.Popen(["djview4", url])

    # -------------------------------------------------
    # Page mode: highlight all occurrences on a page
    # -------------------------------------------------

    def open_occurrences(self, page_number, shape, occurrences):
        """
        Open djview4 and highlight all occurrences of `shape` on a given page.

        page_number is expected to be 0-based (DB convention).
        """
        page_1based = page_number + 1

        # Page size info (from djvudump)
        page_w, page_h = self.page_info.get_page_size(page_number)

        highlights = []
        for occ in occurrences:
            x = occ.x
            y = occ.y
            w = shape.width
            h = shape.height
            highlights.append(f"highlight={x},{y},{w},{h}")

        query = f"djvuopts=&page={page_1based}&" + "&".join(highlights)
        url = f"file://{self.document_path}?{query}"

        self._log_launch(
            shape=shape,
            page_number=page_number,
            page_1based=page_1based,
            occurrences=occurrences,
            highlights=highlights,
            page_width=page_w,
            page_height=page_h,
            url=url,
        )

        subprocess.Popen(["djview4", url])

    # -------------------------------------------------
    # Structured logging
    # -------------------------------------------------

    def _log_launch(
        self,
        shape,
        page_number,
        page_1based,
        occurrences,
        highlights,
        page_width,
        page_height,
        url,
    ):
        lines = []
        lines.append("=" * 60)
        lines.append("DjView Launch Mode: PAGE")
        lines.append(f"Document: {self.document_path}")
        lines.append("")
        lines.append("Shape metadata:")
        lines.append(f"  Shape ID: {shape.id}")
        lines.append(f"  Parent ID: {shape.parent_id}")
        lines.append(f"  Depth: {shape.depth}")
        lines.append(f"  Sibling index: {shape.sibling_index}")
        lines.append(f"  Size: {shape.width} x {shape.height}")
        lines.append(f"  Usage count: {shape.usage_count}")
        lines.append(f"  Subtree usage: {shape.subtree_count}")
        lines.append("")
        lines.append(f"Page size: {page_width} x {page_height}")
        lines.append(f"DB page (0-based): {page_number}")
        lines.append(f"DjView page (1-based): {page_1based}")
        lines.append("")
        lines.append("Occurrences:")

        for i, occ in enumerate(occurrences, 1):
            lines.append(
                f"  #{i}: x={occ.x} y={occ.y} "
                f"w={shape.width} h={shape.height}"
            )

        lines.append("")
        lines.append("Highlight parameters:")
        for h in highlights:
            lines.append(f"  {h}")

        lines.append("")
        lines.append("Final URL:")
        lines.append(url)
        lines.append("=" * 60)
        lines.append("")

        self.logger.info("\n".join(lines))
