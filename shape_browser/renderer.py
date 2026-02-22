import io
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
        data = shape.bits

        # Many datasets store a full PBM (P4) file in `bits` (with header).
        # Detect and decode it properly to avoid header bytes becoming pixels.
        if isinstance(data, (bytes, bytearray)) and data.startswith(b"P"):
            try:
                img = Image.open(io.BytesIO(data))
                return img.convert("1")
            except Exception:
                # Fall back to raw decode below if header parsing fails
                pass

        # Fallback: treat `bits` as raw packed 1-bit rows
        width = shape.width
        height = shape.height

        image = Image.frombytes(
            "1",                      # mode
            (width, height),          # size
            data,                     # data
            "raw",                    # decoder
            "1;I",                    # raw mode
            0,                        # stride
            1,                        # orientation
        )

        return image

