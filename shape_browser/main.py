import tkinter as tk

from repository import ShapeRepository
from model import ShapeModel
from renderer import ShapeRenderer
from gui import ShapeBrowserGUI


def choose_document(repo):
    documents = repo.fetch_documents()

    if not documents:
        print("No documents found.")
        return None

    print("Available documents:")
    for doc in documents:
        print(f"{doc['id']}: {doc['document']}")

    while True:
        try:
            selected = int(input("Enter document ID to load: "))
            for doc in documents:
                if doc["id"] == selected:
                    return selected
            print("Invalid ID. Try again.")
        except ValueError:
            print("Please enter a numeric ID.")


def main():
    print("=== Shape Browser ===")

    host = input("DB host [localhost]: ") or "localhost"
    user = input("DB user: ")
    password = input("DB password: ")
    database = input("DB name: ")

    repo = ShapeRepository(host, user, password, database)

    document_id = choose_document(repo)
    if document_id is None:
        return

    print("Loading shapes...")
    shape_rows = repo.fetch_shapes(document_id)

    print("Loading blits...")
    blit_rows = repo.fetch_blits(document_id)

    print("Building model...")
    model = ShapeModel(shape_rows, blit_rows)

    renderer = ShapeRenderer()

    print("Launching GUI...")
    root = tk.Tk()
    app = ShapeBrowserGUI(root, model, renderer)
    root.mainloop()

    repo.close()


if __name__ == "__main__":
    main()
