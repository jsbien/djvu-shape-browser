#!/usr/bin/env python3
import configparser
import os
from collections import defaultdict
import pymysql


def load_cfg():
    cfg_path = os.path.expanduser("~/.config/shape-browser/sb_import.ini")
    cp = configparser.ConfigParser()
    cp.read(cfg_path)
    db = cp["db"]
    return {
        "host": db.get("host", "localhost"),
        "port": db.getint("port", 3306),
        "user": db["user"],
        "password": db.get("password", ""),
        "database": db["aux_db"],  # Exercitum__aux
        "charset": "utf8mb4",
    }


def connect_mysql(cfg):
    return pymysql.connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["database"],
        charset=cfg["charset"],
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


def main(document_id: int = 1):
    cfg = load_cfg()
    conn = connect_mysql(cfg)

    try:
        with conn.cursor() as cur:
            # Process dictionary by dictionary to keep memory bounded
            cur.execute("SELECT DISTINCT dictionary_id FROM sb_shape_tree ORDER BY dictionary_id")
            dict_ids = [r["dictionary_id"] for r in cur.fetchall()]
            print(f"Found {len(dict_ids)} dictionaries")

            # Clear previous results for this document (idempotent rebuild)
            cur.execute("DELETE FROM sb_shape_subtree_usage WHERE document_id=%s", (document_id,))
            conn.commit()

            for i, did in enumerate(dict_ids, start=1):
                print(f"[{i}/{len(dict_ids)}] dictionary_id={did}: loading tree order...")

                # Load shapes in descending dfs_pre so children come before parents (postorder-like).
                cur.execute(
                    """
                    SELECT shape_id, parent_id
                    FROM sb_shape_tree
                    WHERE dictionary_id=%s
                    ORDER BY dfs_pre DESC
                    """,
                    (did,),
                )
                nodes = cur.fetchall()

                # Load direct usage for all shapes in this dictionary for this document.
                # We must map shape_id -> usage_count. If missing, treat as 0.
                cur.execute(
                    """
                    SELECT u.shape_id, u.usage_count
                    FROM sb_shape_usage u
                    JOIN shapes s ON s.id = u.shape_id
                    WHERE u.document_id=%s AND s.dictionary_id=%s
                    """,
                    (document_id, did),
                )
                usage = {int(r["shape_id"]): int(r["usage_count"]) for r in cur.fetchall()}

                subtree = defaultdict(int)

                # Accumulate: start each node with its own usage, then add to parent
                for r in nodes:
                    sid = int(r["shape_id"])
                    pid = r["parent_id"]
                    pid = int(pid) if pid is not None else None

                    total = usage.get(sid, 0) + subtree[sid]
                    subtree[sid] = total

                    # Add to parent if parent looks valid (ignore NULL/-1 roots)
                    if pid is not None and pid != -1:
                        subtree[pid] += total

                # Bulk insert results
                out = [(did, document_id, sid, int(val)) for sid, val in subtree.items()]

                print(f"[{i}/{len(dict_ids)}] dictionary_id={did}: writing {len(out)} rows...")
                cur.executemany(
                    """
                    INSERT INTO sb_shape_subtree_usage(dictionary_id, document_id, shape_id, subtree_usage)
                    VALUES (%s, %s, %s, %s)
                    """,
                    out,
                )
                conn.commit()

        print("Done.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main(document_id=1)
    
