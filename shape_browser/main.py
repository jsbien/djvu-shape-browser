import argparse
from datetime import datetime
import tkinter as tk

from repository import ShapeRepository
from model import ShapeModel
from renderer import ShapeRenderer
from gui import ShapeBrowserGUI


PROGRAM_NAME = "Shape Browser"
VERSION = "0.4"
BUILD_TIMESTAMP = datetime.now().strftime("%Y-%m-%d-%H%M%S")


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Browse glyph shapes stored in MariaDB."
    )

    parser.add_argument("--host", required=True, help="Database host")
    parser.add_argument("--user", required=True, help="Database user")
    parser.add_argument("--password", required=True, help="Database password")
    parser.add_argument("--database", required=True, help="Database name")
    parser.add_argument(
        "--document",
        required=True,
        help="Document ID to load (required)",
    )

    return parser.parse_args()


def main():
    args = parse_arguments()

    print(f"{PROGRAM_NAME} {VERSION}")
    print(f"Build: {BUILD_TIMESTAMP}")
    print("Connecting to database...")

    # -------------------------------------------------
    # Repository
    # -------------------------------------------------

    repo = ShapeRepository(
        host=args.host,
        user=args.user,
        password=args.password,
        database=args.database,
    )

    # -------------------------------------------------
    # Load shapes + blits
    # -------------------------------------------------

    print("Loading shapes...")
    shapes = repo.fetch_shapes(args.document)

    print("Loading blits...")
    blits = repo.fetch_blits(args.document)

    # -------------------------------------------------
    # Build model
    # -------------------------------------------------

    print("Building model...")
    model = ShapeModel(shapes, blits)

    # -------------------------------------------------
    # Start GUI
    # -------------------------------------------------

    print("Launching GUI...")

    root = tk.Tk()
    renderer = ShapeRenderer()

    app = ShapeBrowserGUI(
        root=root,
        model=model,
        renderer=renderer,
        tile_size=140,
        database_name=args.database,
        version=VERSION,
        build_timestamp=BUILD_TIMESTAMP,
    )

    root.mainloop()

    repo.close()


if __name__ == "__main__":
    main()
