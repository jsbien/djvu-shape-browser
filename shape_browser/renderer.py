from PIL import Image, ImageTk


class ShapeRenderer:
    """
    Responsible for decoding PBM-stored glyph bitmaps
    and converting them into Tkinter-compatible images.

    Caches decoded images to avoid repeated work.
    """

    def __init__(self):
        # shape_id -> PIL.Image
        self._pil_cache = {}

        # shape_id -> ImageTk.PhotoImage
        self._tk_cache = {}

    # -------------------------
    # Public API
    # -------------------------

    def get_pil_image(self, shape):
        if shape.id not in self._pil_cache:
            self._pil_cache[shape.id] = self._decode_pbm(shape)
        return self._pil_cache[shape.id]

    def get_tk_image(self, shape):
        pil_image = self.get_pil_image(shape)
        return ImageTk.PhotoImage(pil_image)

    def clear_cache(self):
        """
        Clears all cached images.
        """
        self._pil_cache.clear()
        self._tk_cache.clear()

    # -------------------------
    # Internal Methods
    # -------------------------

    def _get_pil_image(self, shape):
        """
        Returns decoded PIL image for the shape.
        """
        if shape.id not in self._pil_cache:
            self._pil_cache[shape.id] = self._decode_pbm(shape)

        return self._pil_cache[shape.id]

    def _decode_pbm(self, shape):
        """
        Decodes PBM (P4) image stored in shape.bits.

        shape.bits format:
            P4
            <width> <height>
            <binary bitmap data>
        """

        raw_bytes = shape.bits

        # PBM header format is:
        # b"P4\n<width> <height>\n"
        #
        # We reconstruct header length dynamically
        header = f"P4\n{shape.width} {shape.height}\n".encode("ascii")
        image_bytes = raw_bytes[len(header):]

        # Create 1-bit image from raw data
        image = Image.frombytes(
            "1",
            (shape.width, shape.height),
            image_bytes,
            "raw",
            "1;I",
            0,
            1
        )

        return image
