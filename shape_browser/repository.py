import pymysql


class ShapeRepository:
    """
    Handles database access for shapes and blits.
    No rendering, no GUI logic.
    """

    def __init__(self, host, user, password, database):
        self.connection = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )

    # -------------------------
    # Public API
    # -------------------------

    def fetch_shapes(self, document_id):
        """
        Returns list of shape rows for a given document.
        """
        query = """
            SELECT s.id, s.parent_id, s.width, s.height, s.bits
            FROM shapes s
            JOIN dictionaries d ON s.dictionary_id = d.id
            WHERE d.document_id = %s
        """

        with self.connection.cursor() as cursor:
            cursor.execute(query, (document_id,))
            return cursor.fetchall()

    def fetch_blits(self, document_id):
        """
        Returns list of blits (shape occurrences) for a document.
        """
        query = """
            SELECT shape_id, page_number, b_left, b_bottom
            FROM blits
            WHERE document_id = %s
        """

        with self.connection.cursor() as cursor:
            cursor.execute(query, (document_id,))
            return cursor.fetchall()

    def fetch_documents(self):
        """
        Returns available documents.
        """
        query = "SELECT id, document FROM documents"

        with self.connection.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall()

    def close(self):
        self.connection.close()
