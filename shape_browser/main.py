import argparse
import os
import sys
from datetime import datetime
import tkinter as tk

from repository import ShapeRepository
from model import ShapeModel
from renderer import ShapeRenderer
from gui import ShapeBrowserGUI
from djview_launcher import DjViewLauncher
from page_info_provider import PageInfoProvider

VERSION = "0.6"
BUILD_TIMESTAMP = datetime.now().strftime("%Y-%m-%d-%H%M%S")


def main():
    parser = argparse.ArgumentParser(description="Shape Browser (perf-auxdb)")
    parser.add_argument("--host", required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--database", required=True)   # primary name, we will append __aux
    parser.add_argument("--document", type=int, required=True)
    parser.add_argument("--djvu-root", required=True)

    args = parser.parse_args()

    aux_db = args.database + "__aux"
    print(f"Shape Browser {VERSION}")
    print(f"Build: {BUILD_TIMESTAMP}")
    print(f"Using aux DB: {aux_db}")

    repo = ShapeRepository(args.host, args.user, args.password, aux_db)
    model = ShapeModel(repo, args.document)

    docs = repo.fetch_documents()
    doc_row = next((d for d in docs if d["id"] == args.document), None)
    if not doc_row:
        print("Document not found.")
        sys.exit(1)

    document_filename = doc_row["document"]
    document_path = os.path.abspath(os.path.join(args.djvu_root, document_filename))
    if not os.path.exists(document_path):
        print(f"DjVu file not found: {document_path}")
        sys.exit(1)

    page_info = PageInfoProvider(document_path)
    djview_launcher = DjViewLauncher(document_path, page_info)
    renderer = ShapeRenderer()

    root = tk.Tk()
    ShapeBrowserGUI(
        root=root,
        model=model,
        renderer=renderer,
        database_name=aux_db,
        version=VERSION,
        build_timestamp=BUILD_TIMESTAMP,
        djview_launcher=djview_launcher,
        page_size=600,
    )
    root.mainloop()
    repo.close()


if __name__ == "__main__":
    main()
    
