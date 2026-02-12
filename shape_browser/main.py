import argparse
import tkinter as tk

from repository import ShapeRepository
from model import ShapeModel
from renderer import ShapeRenderer
from gui import ShapeBrowserGUI


VERSION = "0.2"


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Shape Browser — browse canonical glyph shapes"
    )

    parser.add_argument("--host", required=True, help="MariaDB host")
    parser.add_argument("--user", required=True, help="MariaDB user")
    parser.add_argument("--password", required=True, help="MariaDB password")
    parser.add_argument("--database", required=True, help="Database name")
    parser.add_argument("--document", required=True, type=int,
                        help="Document ID to load")
    parser.add_argument("--tile-size", type=int, default=140,
                        help="Grid tile size in pixels (default: 140)")

    return parser.parse_args()


def main():
    args = parse_arguments()

    repo = ShapeRepository(
        host=args.host,
        user=args.user,
        password=args.password,
        database=args.database,
    )

    shape_rows = repo.fetch_shapes(args.document)
    blit_rows = repo.fetch_blits(args.document)

    model = ShapeModel(shape_rows, blit_rows)
    renderer = ShapeRenderer()

    root = tk.Tk()

    app = ShapeBrowserGUI(
        root=root,
        model=model,
        renderer=renderer,
        tile_size=args.tile_size,
        database_name=args.database,
        version=VERSION,
    )

    root.mainloop()

    repo.close()


if __name__ == "__main__":
    main()
