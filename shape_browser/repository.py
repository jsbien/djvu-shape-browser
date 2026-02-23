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

    def fetch_root_shapes(self, document_id):
        """
        Returns root shapes (parent_id is NULL or -1) for a given document.

        Requires auxiliary table:
          sb_shape_usage(document_id, shape_id, usage_count)
        """
        query = """
            SELECT
                s.id,
                s.dictionary_id,
                s.parent_id,
                s.width,
                s.height,
                s.bits,
                COALESCE(u.usage_count, 0) AS usage_count
            FROM shapes s
            JOIN dictionaries d ON s.dictionary_id = d.id
            LEFT JOIN sb_shape_usage u
              ON u.document_id = d.document_id AND u.shape_id = s.id
            WHERE d.document_id = %s
              AND (s.parent_id IS NULL OR s.parent_id = -1)
            ORDER BY s.height DESC, s.id
        """

        with self.connection.cursor() as cursor:
            cursor.execute(query, (document_id,))
            return cursor.fetchall()

    def fetch_child_shapes(self, document_id, dictionary_id, parent_id):
        """
        Returns direct children of a given parent shape within a dictionary.

        Requires auxiliary table:
          sb_shape_usage(document_id, shape_id, usage_count)
        """
        query = """
            SELECT
                s.id,
                s.dictionary_id,
                s.parent_id,
                s.width,
                s.height,
                s.bits,
                COALESCE(u.usage_count, 0) AS usage_count
            FROM shapes s
            JOIN dictionaries d ON s.dictionary_id = d.id
            LEFT JOIN sb_shape_usage u
              ON u.document_id = d.document_id AND u.shape_id = s.id
            WHERE d.document_id = %s
              AND s.dictionary_id = %s
              AND s.parent_id = %s
            ORDER BY s.height DESC, s.id
        """

        with self.connection.cursor() as cursor:
            cursor.execute(query, (document_id, dictionary_id, parent_id))
            return cursor.fetchall()

    def fetch_occurrences(self, document_id, shape_id):
        """
        Returns occurrences (blits) for a single shape in a document.
        """
        query = """
            SELECT shape_id, page_number, b_left, b_bottom
            FROM blits
            WHERE document_id = %s AND shape_id = %s
            ORDER BY page_number, b_bottom, b_left
        """

        with self.connection.cursor() as cursor:
            cursor.execute(query, (document_id, shape_id))
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
