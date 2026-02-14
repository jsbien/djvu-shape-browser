import argparse
import os
import sys
from datetime import datetime
import tkinter as tk

from repository import ShapeRepository
from model import ShapeModel
from renderer import ShapeRenderer
from gui import ShapeBrowserGUI


VERSION = "0.6"
BUILD_TIMESTAMP = datetime.now().strftime("%Y-%m-%d-%H%M%S")


def main():
    parser = argparse.ArgumentParser(
        description="Shape Browser"
    )

    parser.add_argument("--host", required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--document", type=int, required=True)
    parser.add_argument(
        "--djvu-root",
        required=True,
        help="Directory containing DjVu documents",
    )

    args = parser.parse_args()

    print(f"Shape Browser {VERSION}")
    print(f"Build: {BUILD_TIMESTAMP}")
    print("Connecting to database...")

    repo = ShapeRepository(
        args.host,
        args.user,
        args.password,
        args.database,
    )

    print("Loading shapes...")
    shapes = repo.fetch_shapes(args.document)

    print("Loading blits...")
    blits = repo.fetch_blits(args.document)

    print("Building model...")
    model = ShapeModel(shapes, blits)

    print("Initializing renderer...")
    renderer = ShapeRenderer()

    # ---------------------------------------------------
    # Resolve document filename and absolute path
    # ---------------------------------------------------

    documents = repo.fetch_documents()

    document_row = None
    for doc in documents:
        if doc["id"] == args.document:
            document_row = doc
            break

    if document_row is None:
        print("Document not found in database.")
        sys.exit(1)

    # According to repository.py:
    # SELECT id, document FROM documents
    document_filename = document_row["document"]

    document_path = os.path.abspath(
        os.path.join(args.djvu_root, document_filename)
    )

    if not os.path.exists(document_path):
        print(f"DjVu file not found: {document_path}")
        sys.exit(1)

    print(f"Using DjVu file: {document_path}")

    # ---------------------------------------------------

    print("Launching GUI...")

    root = tk.Tk()

    app = ShapeBrowserGUI(
        root=root,
        model=model,
        renderer=renderer,
        database_name=args.database,
        version=VERSION,
        build_timestamp=BUILD_TIMESTAMP,
        document_path=document_path,
    )

    root.mainloop()

    repo.close()


if __name__ == "__main__":
    main()
