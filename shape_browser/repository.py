import pymysql


class ShapeRepository:
    """
    Repository for the aux DB (e.g. Exercitum__aux).

    Requirements in aux DB:
      - views: documents, dictionaries, shapes, blits (pointing to source DB)
      - tables: sb_shape_usage, sb_shape_tree, sb_shape_subtree_usage
    """

    def __init__(self, host, user, password, database, port=3306):
        self.connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
        )
        self._assert_aux_tables_exist()

    def close(self):
        try:
            self.connection.close()
        except Exception:
            pass

    # -------------------------------------------------
    # Safety checks
    # -------------------------------------------------

    def _assert_aux_tables_exist(self):
        required = {
            "sb_shape_usage",
            "sb_shape_tree",
            "sb_shape_subtree_usage",
        }
        with self.connection.cursor() as cur:
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = DATABASE()
                """
            )
            existing = {r["table_name"] for r in cur.fetchall()}

        missing = sorted(required - existing)
        if missing:
            raise RuntimeError(
                "Aux DB is missing required tables: "
                + ", ".join(missing)
                + ". Run the import/precompute utility first."
            )

    # -------------------------------------------------
    # Basic metadata
    # -------------------------------------------------

    def fetch_documents(self):
        query = "SELECT id, document FROM documents ORDER BY id"
        with self.connection.cursor() as cur:
            cur.execute(query)
            return cur.fetchall()

    # -------------------------------------------------
    # Shape listing (paged, SQL-filtered)
    # -------------------------------------------------

    @staticmethod
    def _normalize_range(min_val, max_val):
        """
        Return (min,max) where either may be None.
        Accepts empty strings / None.
        """
        def norm(x):
            if x is None:
                return None
            if isinstance(x, str):
                x = x.strip()
                if not x:
                    return None
            return x

        return norm(min_val), norm(max_val)

    def count_shapes(self, document_id, depth_max=None,
                     direct_min=None, direct_max=None,
                     subtree_min=None, subtree_max=None,
                     height_min=None, height_max=None,
                     ratio_min=None, ratio_max=None,
                     mode="global", subtree_root_id=None):
        """
        Count shapes matching filters.

        mode:
          - 'global': use sb_shape_tree.depth <= depth_max
          - 'subtree': use sb_shape_tree dfs interval for subtree_root_id
        """
        (direct_min, direct_max) = self._normalize_range(direct_min, direct_max)
        (subtree_min, subtree_max) = self._normalize_range(subtree_min, subtree_max)
        (height_min, height_max) = self._normalize_range(height_min, height_max)
        (ratio_min, ratio_max) = self._normalize_range(ratio_min, ratio_max)

        if depth_max is None:
            depth_max = 0  # default roots only, like your current workflow

        params = {"doc": document_id, "depth_max": int(depth_max)}

        where = []
        joins = []

        # Base join: shapes -> dictionaries (doc filter)
        joins.append("JOIN dictionaries d ON d.id = s.dictionary_id")
        where.append("d.document_id = %(doc)s")

        # Tree table: to get depth + subtree intervals
        joins.append("JOIN sb_shape_tree t ON t.dictionary_id = s.dictionary_id AND t.shape_id = s.id")

        # Usage join (direct)
        joins.append(
            "LEFT JOIN sb_shape_usage u ON u.document_id = d.document_id AND u.shape_id = s.id"
        )

        # Subtree usage join (per doc)
        joins.append(
            "LEFT JOIN sb_shape_subtree_usage su "
            "ON su.dictionary_id = s.dictionary_id AND su.shape_id = s.id AND su.document_id = d.document_id"
        )

        if mode == "global":
            where.append("t.depth <= %(depth_max)s")
        elif mode == "subtree":
            if subtree_root_id is None:
                raise ValueError("subtree_root_id is required for mode='subtree'")
            # Limit to root's dictionary and interval
            params["root_id"] = int(subtree_root_id)
            # Join root row once
            joins.append(
                "JOIN sb_shape_tree r ON r.shape_id = %(root_id)s AND r.dictionary_id = t.dictionary_id"
            )
            where.append("t.dfs_pre BETWEEN r.dfs_pre AND r.dfs_post")
        else:
            raise ValueError("Unknown mode: " + str(mode))

        # Filters
        if direct_min is not None:
            params["direct_min"] = int(direct_min)
            where.append("COALESCE(u.usage_count, 0) >= %(direct_min)s")
        if direct_max is not None:
            params["direct_max"] = int(direct_max)
            where.append("COALESCE(u.usage_count, 0) <= %(direct_max)s")

        if subtree_min is not None:
            params["subtree_min"] = int(subtree_min)
            where.append("COALESCE(su.subtree_usage, 0) >= %(subtree_min)s")
        if subtree_max is not None:
            params["subtree_max"] = int(subtree_max)
            where.append("COALESCE(su.subtree_usage, 0) <= %(subtree_max)s")

        if height_min is not None:
            params["height_min"] = int(height_min)
            where.append("s.height >= %(height_min)s")
        if height_max is not None:
            params["height_max"] = int(height_max)
            where.append("s.height <= %(height_max)s")

        # Ratio H/W
        if ratio_min is not None:
            params["ratio_min"] = float(ratio_min)
            where.append("(CASE WHEN s.width=0 THEN 0.0 ELSE (s.height / s.width) END) >= %(ratio_min)s")
        if ratio_max is not None:
            params["ratio_max"] = float(ratio_max)
            where.append("(CASE WHEN s.width=0 THEN 0.0 ELSE (s.height / s.width) END) <= %(ratio_max)s")

        query = f"""
            SELECT COUNT(*) AS n
            FROM shapes s
            {' '.join(joins)}
            WHERE {' AND '.join(where)}
        """

        with self.connection.cursor() as cur:
            cur.execute(query, params)
            return int(cur.fetchone()["n"])

    def fetch_shapes_page(self, document_id, offset, limit, depth_max=None,
                          direct_min=None, direct_max=None,
                          subtree_min=None, subtree_max=None,
                          height_min=None, height_max=None,
                          ratio_min=None, ratio_max=None,
                          mode="global", subtree_root_id=None):
        """
        Fetch a page of shapes (metadata only; no bits blob).
        Sort: height desc, id (stable).
        Returns rows with: id, dictionary_id, parent_id, width, height, depth,
                          usage_count, subtree_usage, ratio
        """
        (direct_min, direct_max) = self._normalize_range(direct_min, direct_max)
        (subtree_min, subtree_max) = self._normalize_range(subtree_min, subtree_max)
        (height_min, height_max) = self._normalize_range(height_min, height_max)
        (ratio_min, ratio_max) = self._normalize_range(ratio_min, ratio_max)

        if depth_max is None:
            depth_max = 0

        params = {
            "doc": document_id,
            "depth_max": int(depth_max),
            "offset": int(offset),
            "limit": int(limit),
        }

        where = []
        joins = []

        joins.append("JOIN dictionaries d ON d.id = s.dictionary_id")
        where.append("d.document_id = %(doc)s")

        joins.append("JOIN sb_shape_tree t ON t.dictionary_id = s.dictionary_id AND t.shape_id = s.id")
        joins.append("LEFT JOIN sb_shape_usage u ON u.document_id = d.document_id AND u.shape_id = s.id")
        joins.append(
            "LEFT JOIN sb_shape_subtree_usage su "
            "ON su.dictionary_id = s.dictionary_id AND su.shape_id = s.id AND su.document_id = d.document_id"
        )

        if mode == "global":
            where.append("t.depth <= %(depth_max)s")
        elif mode == "subtree":
            if subtree_root_id is None:
                raise ValueError("subtree_root_id is required for mode='subtree'")
            params["root_id"] = int(subtree_root_id)
            joins.append(
                "JOIN sb_shape_tree r ON r.shape_id = %(root_id)s AND r.dictionary_id = t.dictionary_id"
            )
            where.append("t.dfs_pre BETWEEN r.dfs_pre AND r.dfs_post")
        else:
            raise ValueError("Unknown mode: " + str(mode))

        if direct_min is not None:
            params["direct_min"] = int(direct_min)
            where.append("COALESCE(u.usage_count, 0) >= %(direct_min)s")
        if direct_max is not None:
            params["direct_max"] = int(direct_max)
            where.append("COALESCE(u.usage_count, 0) <= %(direct_max)s")

        if subtree_min is not None:
            params["subtree_min"] = int(subtree_min)
            where.append("COALESCE(su.subtree_usage, 0) >= %(subtree_min)s")
        if subtree_max is not None:
            params["subtree_max"] = int(subtree_max)
            where.append("COALESCE(su.subtree_usage, 0) <= %(subtree_max)s")

        if height_min is not None:
            params["height_min"] = int(height_min)
            where.append("s.height >= %(height_min)s")
        if height_max is not None:
            params["height_max"] = int(height_max)
            where.append("s.height <= %(height_max)s")

        if ratio_min is not None:
            params["ratio_min"] = float(ratio_min)
            where.append("(CASE WHEN s.width=0 THEN 0.0 ELSE (s.height / s.width) END) >= %(ratio_min)s")
        if ratio_max is not None:
            params["ratio_max"] = float(ratio_max)
            where.append("(CASE WHEN s.width=0 THEN 0.0 ELSE (s.height / s.width) END) <= %(ratio_max)s")

        query = f"""
            SELECT
                s.id,
                s.dictionary_id,
                s.parent_id,
                s.width,
                s.height,
                t.depth,
                t.sibling_index,
                COALESCE(u.usage_count, 0) AS usage_count,
                COALESCE(su.subtree_usage, 0) AS subtree_usage,
                (CASE WHEN s.width=0 THEN 0.0 ELSE (s.height / s.width) END) AS ratio_hw
            FROM shapes s
            {' '.join(joins)}
            WHERE {' AND '.join(where)}
            ORDER BY s.height DESC, s.id
            LIMIT %(limit)s OFFSET %(offset)s
        """

        with self.connection.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()

    # -------------------------------------------------
    # Bits on demand
    # -------------------------------------------------

    def fetch_bits_for_shape_ids(self, shape_ids):
        """
        Fetch PBM bits blobs for selected shapes only.
        Returns dict shape_id -> bits (bytes)
        """
        if not shape_ids:
            return {}

        # Avoid enormous IN() lists (chunk)
        out = {}
        chunk_size = 500

        with self.connection.cursor() as cur:
            for i in range(0, len(shape_ids), chunk_size):
                chunk = shape_ids[i:i + chunk_size]
                placeholders = ",".join(["%s"] * len(chunk))
                query = f"SELECT id, bits FROM shapes WHERE id IN ({placeholders})"
                cur.execute(query, chunk)
                for r in cur.fetchall():
                    out[int(r["id"])] = r["bits"]

        return out

    # -------------------------------------------------
    # Occurrences (on demand)
    # -------------------------------------------------

    def fetch_occurrences(self, document_id, shape_id):
        query = """
            SELECT shape_id, page_number, b_left, b_bottom
            FROM blits
            WHERE document_id = %s AND shape_id = %s
            ORDER BY page_number, b_bottom, b_left
        """
        with self.connection.cursor() as cur:
            cur.execute(query, (document_id, shape_id))
            return cur.fetchall()
        
