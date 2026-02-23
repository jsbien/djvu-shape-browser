#!/usr/bin/env python3
import configparser
import os
import sys
from collections import defaultdict
import pymysql


def load_cfg():
    cfg_path = os.path.expanduser("~/.config/shape-browser/sb_import.ini")
    if not os.path.exists(cfg_path):
        raise FileNotFoundError(f"Config not found: {cfg_path}")

    cp = configparser.ConfigParser()
    cp.read(cfg_path)
    db = cp["db"]
    return {
        "host": db.get("host", "localhost"),
        "port": db.getint("port", 3306),
        "user": db["user"],
        "password": db.get("password", ""),
        "database": db["aux_db"],  # e.g. Exercitum__aux
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


def fetch_dictionary_ids(cur):
    cur.execute("SELECT DISTINCT dictionary_id FROM shapes ORDER BY dictionary_id")
    return [r["dictionary_id"] for r in cur.fetchall()]


def fetch_shape_parent_rows(cur, dictionary_id):
    cur.execute(
        """
        SELECT id AS shape_id, parent_id
        FROM shapes
        WHERE dictionary_id = %s
        """,
        (dictionary_id,),
    )
    return cur.fetchall()


def build_adjacency(rows):
    """
    Returns:
      parent_of[shape_id] -> parent_id (can be None/-1)
      children_of[parent_id] -> list[shape_id]
    """
    parent_of = {}
    children_of = defaultdict(list)

    for r in rows:
        sid = int(r["shape_id"])
        pid = r["parent_id"]
        if pid is not None:
            pid = int(pid)
        parent_of[sid] = pid
        children_of[pid].append(sid)

    # Stable sibling ordering: by shape_id for reproducibility
    for pid in list(children_of.keys()):
        children_of[pid].sort()

    return parent_of, children_of


def compute_dfs_for_dictionary(dictionary_id, parent_of, children_of):
    """
    Computes dfs_pre/dfs_post/depth/sibling_index for one dictionary.

    Roots are those with parent_id NULL or -1.
    Returns list of rows to insert into sb_shape_tree.
    """
    roots = []
    for sid, pid in parent_of.items():
        if pid is None or pid == -1:
            roots.append(sid)
    roots.sort()

    pre = {}
    post = {}
    depth = {}
    sibling_index = {}

    counter = 0

    sys.setrecursionlimit(2_000_000)

    def dfs(node, d):
        nonlocal counter
        counter += 1
        pre[node] = counter
        depth[node] = d

        kids = children_of.get(node, [])
        for idx, ch in enumerate(kids, start=1):
            sibling_index[ch] = idx
            dfs(ch, d + 1)

        counter += 1
        post[node] = counter

    # Root sibling_index: order among roots
    for idx, r in enumerate(roots, start=1):
        sibling_index[r] = idx
        dfs(r, 0)

    # Some nodes might be disconnected / cycles / bad parent refs.
    # Treat them as extra roots (keeps tool robust).
    for sid in parent_of.keys():
        if sid not in pre:
            sibling_index[sid] = 1
            dfs(sid, 0)

    out_rows = []
    for sid, pid in parent_of.items():
        out_rows.append(
            (
                dictionary_id,
                sid,
                pid if pid is not None else None,
                pre.get(sid),
                post.get(sid),
                depth.get(sid, 0),
                sibling_index.get(sid, 1),
            )
        )
    return out_rows


def write_sb_shape_tree(cur, dictionary_id, rows):
    # Remove previous data for this dictionary (idempotent rebuild per dict)
    cur.execute("DELETE FROM sb_shape_tree WHERE dictionary_id = %s", (dictionary_id,))

    cur.executemany(
        """
        INSERT INTO sb_shape_tree
          (dictionary_id, shape_id, parent_id, dfs_pre, dfs_post, depth, sibling_index)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        rows,
    )


def main():
    cfg = load_cfg()
    conn = connect_mysql(cfg)

    try:
        with conn.cursor() as cur:
            dict_ids = fetch_dictionary_ids(cur)
            print(f"Found {len(dict_ids)} dictionaries")

            for i, did in enumerate(dict_ids, start=1):
                print(f"[{i}/{len(dict_ids)}] dictionary_id={did}: loading edges...")
                rows = fetch_shape_parent_rows(cur, did)
                parent_of, children_of = build_adjacency(rows)

                print(f"[{i}/{len(dict_ids)}] dictionary_id={did}: computing DFS...")
                out_rows = compute_dfs_for_dictionary(did, parent_of, children_of)

                print(f"[{i}/{len(dict_ids)}] dictionary_id={did}: writing {len(out_rows)} rows...")
                write_sb_shape_tree(cur, did, out_rows)

                conn.commit()

        print("Done.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
    
