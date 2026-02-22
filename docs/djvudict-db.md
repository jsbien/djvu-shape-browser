 # djvudict SQLite database (schema and semantics)

 This document describes the SQLite database produced by djvudict when run with SQL output enabled.

 Terminology note (synchronized with Shape Browser):
 - djvudict code uses the table name letters, but in Shape Browser terms we will call these records shapes.
 - These “shapes” are intended to correspond to letters/glyphs, but in practice may also include non-letter components. That’s a known issue to investigate later.

 The authoritative schema is defined in docs/from Trufanov/sqlstorage.cpp.

 ---

 ## What the database represents

 djvudict analyzes JB2 data in DjVu documents:

 - Each page typically contains an Sjbz chunk (JB2 “form” for that page).
 - Multi-page documents may also contain shared dictionaries stored as Djbz chunks.
 - JB2 encoding draws bitmaps at positions and can store bitmaps in dictionaries for later reuse.
 - djvudict stores:
 1) document “forms” (pages and shared dictionaries),
 2) Sjbz metadata and which Djbz it uses,
 3) extracted shapes (bitmaps) and their placement/usage/refinement relationships.

 The database is primarily for inspection and statistics, not for reconstructing a perfect page image.

 ---

 ## Tables overview

 - forms — pages (Sjbz) and shared dictionaries (Djbz)
 - sjbz_info — per-page metadata for Sjbz forms (page size, DPI, version, and Djbz link)
 - letters — shapes extracted from JB2 instructions (position, size, dictionary usage, refinement links)
 - index index_letters — lookup by (form_id, local_id)

 ---

 ## Table: forms

 Represents JB2 “forms” encountered in the DjVu container: pages and shared dictionaries.

 Columns:

 - id INTEGER PRIMARY KEY AUTOINCREMENT
 Internal unique ID.

 - position INTEGER UNIQUE NOT NULL
 Order/position as processed. For multi-page documents, this corresponds to the order of entries.

 - entry_name STRING NOT NULL
 DjVu entry name (page name or shared dict entry name).

- type INTEGER NOT NULL
 Meaning:
 - 0 — unknown / not classified
 - 1 — FORM:DJVU (page component; may contain Sjbz)
 - 2 — FORM:DJVI (shared component; may contain Djbz, but may also be non-dictionary data such as shared annotations)

- path_to_dump STRING
 Path where djvudict dumped bitmaps/logs for this entry (if dumping is enabled). In our sample database, non-dictionary DJVI components have empty path_to_dump.


 ---

 ## Table: sjbz_info

 Additional metadata for Sjbz page forms. One row per page-form.

 Columns:

 - form_id INTEGER NOT NULL UNIQUE
 Foreign key → forms(id)
 The forms row representing this Sjbz page.

 - djbz_id INTEGER NULL
 Foreign key → forms(id)
 The forms row representing the Djbz (shared dictionary) used by this page, if any.

 - width INTEGER NOT NULL
 Page width (pixels).

 - height INTEGER NOT NULL
 Page height (pixels).

 - dpi INTEGER NOT NULL
 Page resolution.

 - version INTEGER NOT NULL
 JB2/JB2-related version field as reported/decoded by djvudict.

 Relationship summary:
 - sjbz_info.form_id identifies “this page”
 - sjbz_info.djbz_id links the page to the shared dictionary it imports (if used)

 ---

 ## Table: letters (Shapes)

 This table stores shapes extracted from JB2 processing.

 Even though the table name is letters, we interpret each row as a shape instance (a bitmap that may be placed and/or added to a dictionary), not necessarily a linguistic letter.

 Columns:

 - id INTEGER PRIMARY KEY AUTOINCREMENT
 Internal unique ID for a shape row.

 - form_id INTEGER NOT NULL
 Foreign key → forms(id)
 Which form this shape belongs to:
 - if the form is type=1, it belongs to that page (Sjbz)
 - if the form is type=2, it belongs to the shared dictionary (Djbz)

 - local_id INTEGER NULL
 The “dictionary index” / local JB2 ID within that form’s local dictionary, if applicable.
 May be NULL for shapes that are not assigned a local dictionary ID in a way djvudict records.

 - x INTEGER
 - y INTEGER
 Placement coordinates for the shape (when the shape is drawn/placed).
 Coordinate origin conventions depend on decoder conventions; djvudict stores whatever it decodes as JB2 placement.

 - width INTEGER NOT NULL
 - height INTEGER NOT NULL
 Bitmap dimensions (pixels).

 - in_image INTEGER NOT NULL
 Whether this shape is placed/drawn into the page image.

 - in_library INTEGER NOT NULL
 Whether this shape is stored in the (local) dictionary/library for reuse.

 - is_non_symbol INTEGER NOT NULL
 A classifier flag from the decoder pipeline (exact semantics depend on minidjvu-mod internals).

 - reference_id INTEGER NULL
 Foreign key → letters(id) (i.e. shapes table self-reference)
 Prototype reference for copy/refinement encoding. If not NULL, this shape is derived from reference_id.

 - is_refinement INTEGER
 Interpretation (per schema comments):
 - 0 — copy of reference_id
 - 1 — refinement of reference_id

 - filename STRING
 Filename of the dumped bitmap (BMP), if dumping is enabled.

 Index:
 - CREATE INDEX index_letters ON letters(form_id, local_id)

 This supports efficient lookup of a shape by its (form_id, local_id).

 ---

 ## Relationships and “what belongs to what”

 - A page is a row in forms where type = 1
 - It has a matching row in sjbz_info (same form_id)
 - It may link to a shared dictionary via sjbz_info.djbz_id

 - A shared dictionary is a row in forms where type = 2
 - It typically has no sjbz_info row
 - It has shapes in letters/shapes with form_id = that forms.id

 - A shape row in letters belongs to exactly one form (form_id)
 - It may reference another shape row via reference_id for refinement/copy chains

 ---

 ## How this maps to Shape Browser concepts (high level)

 - djvudict forms(type=1) ≈ Shape Browser “pages/documents” context
 - djvudict forms(type=2) ≈ Shape Browser “shared dictionary / cross-page shape source”
 - djvudict letters (shapes) ≈ Shape Browser shapes + occurrences, but not normalized the same way
 - djvudict stores per-form shape entries (including dictionary entries and draw operations)
 - Shape Browser normalizes shapes and links occurrences differently (MariaDB schema)

 A detailed mapping will be documented in a separate comparison document.

 ---

 ## Inspecting the sample database

 If you have samples/djvu_sqlite.db in this repo:

  sqlite3 samples/djvu_sqlite.db

 Useful commands:

  .tables
  .schema forms
  .schema sjbz_info
  .schema letters

 Quick sanity queries:

  -- Count pages and shared dictionaries
  SELECT type, COUNT() FROM forms GROUP BY type;

  -- Example: list first pages
  SELECT id, position, entry_name FROM forms WHERE type=1 ORDER BY position LIMIT 10;

  -- Page -> shared dictionary link (if any)
  SELECT f.entry_name AS page, d.entry_name AS shared_dict
  FROM sjbz_info s
  JOIN forms f ON f.id = s.form_id
  LEFT JOIN forms d ON d.id = s.djbz_id
  ORDER BY f.position
  LIMIT 20;

  -- How many shapes per form (page/dict)
  SELECT form_id, COUNT() AS shapes
  FROM letters
  GROUP BY form_id
  ORDER BY shapes DESC
  LIMIT 20;

  -- Refinement/copy usage
  SELECT
  CASE is_refinement WHEN 1 THEN 'refinement' WHEN 0 THEN 'copy' ELSE 'none' END AS kind,
  COUNT(*) AS n
  FROM letters
  GROUP BY kind;

 ---

 ## Open questions / to investigate later

 - What exactly is the coordinate origin for (x, y) as stored by djvudict (and how it matches djview/djvudump conventions).
 - How well “shapes” correspond to actual letters (vs punctuation, noise, or non-text components).
 - The meaning and reliability of is_non_symbol across documents/encoders.
 - Whether local_id is always present for dictionary entries and how to interpret NULL values.

 ---
