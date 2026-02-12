from PIL import Image, ImageTk


class ShapeRenderer:
    def __init__(self):
        # Cache for original decoded PIL images
        self._pil_cache = {}

        # Cache for scaled Tk images: key = (shape_id, tile_size)
        self._tk_cache = {}

    # -------------------------------------------------
    # Public API
    # -------------------------------------------------

    def get_pil_image(self, shape):
        """
        Return original decoded PIL image for a shape.
        Cached after first decode.
        """
        if shape.id not in self._pil_cache:
            self._pil_cache[shape.id] = self._decode_pbm(shape)

        return self._pil_cache[shape.id]

    def get_tk_image(self, shape, tile_size):
        """
        Return scaled PhotoImage ready for Canvas.
        Cached per (shape_id, tile_size).
        """
        key = (shape.id, tile_size)

        if key in self._tk_cache:
            return self._tk_cache[key]

        pil_image = self.get_pil_image(shape)

        max_size = tile_size - 10
        w, h = pil_image.size

        if w > max_size or h > max_size:
            scale = min(max_size / w, max_size / h)
            new_w = max(1, int(w * scale))
            new_h = max(1, int(h * scale))
            pil_image = pil_image.resize((new_w, new_h), Image.NEAREST)

        tk_image = ImageTk.PhotoImage(pil_image)

        self._tk_cache[key] = tk_image
        return tk_image

    # -------------------------------------------------
    # Internal decoding
    # -------------------------------------------------

    def _decode_pbm(self, shape):
        """
        Decode raw PBM (1-bit bitmap) stored in shape into PIL image.
        Assumes shape has:
            - width
            - height
            - bitmap (bytes)
        """

        width = shape.width
        height = shape.height
        data = shape.bits

        # PBM stored as packed bits per row
        # Each row is padded to full bytes
        row_bytes = (width + 7) // 8

        image = Image.frombytes(
            mode="1",
            size=(width, height),
            data=data,
            decoder_name="raw",
            args=("1;I", 0, 1),
        )

        return image
