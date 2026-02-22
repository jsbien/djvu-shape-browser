 # Common model database for Shape Browser and djvudict

 This document defines an explicit common model database that can represent:
 - the Shape Browser MariaDB schema (normalized shapes + occurrences + tree), and
 - the djvudict SQLite schema (forms + per-form shapes + dictionary membership + placements + prototype links).

 The goal is to make bidirectional conversion possible:
 - Shape Browser DB → Common Model DB
 - djvudict DB → Common Model DB
 - (optionally) Common Model DB → either source format, with clearly stated assumptions.

 All terminology in this document uses “shape” (djvudict calls them letters).

 ---

 ## Design principles

 1) Preserve provenance (where each row came from) to support round-tripping.
 2) Separate shape identity (bitmap) from shape instances (tool-specific rows).
 3) Represent both:
 - occurrences (placements / blits), and
 - dictionary membership (local_id, shared vs local).
 4) Keep the schema simple and SQLite-friendly.
 5) Use a canonical coordinate convention for occurrences: bottom-left origin.

 ---

 ## Canonical schema (SQLite)

 ### Documents and pages

 sql  CREATE TABLE documents (  id INTEGER PRIMARY KEY,  filename TEXT NOT NULL,  source_tool TEXT, -- 'shape-browser' | 'djvudict' | 'import'  notes TEXT  );   CREATE TABLE pages (  id INTEGER PRIMARY KEY,  document_id INTEGER NOT NULL REFERENCES documents(id),  page_number INTEGER NOT NULL, -- canonical: 0-based  width INTEGER, -- pixels  height INTEGER, -- pixels  dpi INTEGER,  UNIQUE(document_id, page_number)  ); 

 ### Forms (djvudict concept)

 A form is a JB2 container unit:
 - Sjbz = per-page JB2 stream
 - Djbz = shared dictionary JB2 stream (virtual 0×0 image)

 sql  CREATE TABLE forms (  id INTEGER PRIMARY KEY,  document_id INTEGER NOT NULL REFERENCES documents(id),   kind TEXT NOT NULL, -- 'Sjbz' | 'Djbz' | 'Unknown'  page_id INTEGER REFERENCES pages(id), -- NULL for Djbz   position INTEGER, -- djvudict forms.position  entry_name TEXT, -- djvudict forms.entry_name  dump_path TEXT, -- djvudict forms.path_to_dump   shared_form_id INTEGER REFERENCES forms(id) -- for Sjbz: which Djbz is used (if any)  ); 

 ### Shape definitions (bitmap identity)

 A shape definition is a unique bitmap (globally), deduplicated by hash when possible.

 sql  CREATE TABLE shape_definitions (  id INTEGER PRIMARY KEY,  width INTEGER NOT NULL,  height INTEGER NOT NULL,  bits_hash TEXT, -- hash for deduplication (optional)  bits_blob BLOB, -- raw bits if available (optional)  external_ref TEXT -- filename/URI (BMP path, etc.)  ); 

 ### Shape instances (tool-specific rows)

 A shape instance is “a shape as represented by a tool in a specific context”.
 This is how we avoid losing djvudict per-form records while still supporting shape-browser normalization.

 sql  CREATE TABLE shape_instances (  id INTEGER PRIMARY KEY,  shape_def_id INTEGER NOT NULL REFERENCES shape_definitions(id),   document_id INTEGER NOT NULL REFERENCES documents(id),  form_id INTEGER REFERENCES forms(id), -- often set for djvudict  page_id INTEGER REFERENCES pages(id), -- often set for shape-browser   source_tool TEXT NOT NULL, -- 'djvudict' | 'shape-browser'  source_id TEXT, -- original PK (e.g. djvudict letters.id, sb shapes.id)   is_non_symbol INTEGER NOT NULL DEFAULT 0,   UNIQUE(source_tool, source_id)  ); 

 ### Dictionary membership

 Captures “shape stored in dictionary” with optional local_id in that form.

 sql  CREATE TABLE dictionary_membership (  id INTEGER PRIMARY KEY,  form_id INTEGER NOT NULL REFERENCES forms(id),  shape_instance_id INTEGER NOT NULL REFERENCES shape_instances(id),   local_id INTEGER, -- djvudict local_id (may be NULL)  in_library INTEGER NOT NULL, -- 0/1  library_kind TEXT, -- 'local' | 'shared' | 'unknown'   UNIQUE(form_id, local_id)  ); 

 ### Occurrences (placements / blits)

 Canonical coordinate system: bottom-left origin, integer pixel coordinates.

 sql  CREATE TABLE occurrences (  id INTEGER PRIMARY KEY,  page_id INTEGER NOT NULL REFERENCES pages(id),  shape_instance_id INTEGER NOT NULL REFERENCES shape_instances(id),   x INTEGER NOT NULL,  y INTEGER NOT NULL,  width INTEGER NOT NULL,  height INTEGER NOT NULL,   source_tool TEXT NOT NULL,  source_id TEXT  ); 

 ### Shape relations (prototype/refinement/copy)

 sql  CREATE TABLE shape_relations (  id INTEGER PRIMARY KEY,  child_shape_instance_id INTEGER NOT NULL REFERENCES shape_instances(id),  parent_shape_instance_id INTEGER NOT NULL REFERENCES shape_instances(id),  relation_type TEXT NOT NULL, -- 'copy' | 'refinement' | 'prototype' | ...  notes TEXT  ); 

 ---

 ## Import mapping: djvudict → common model

 Source tables: forms, sjbz_info, letters.

 ### Documents/pages/forms
 - Create one documents row for the DjVu file.
 - For every djvudict forms row:
 - create a forms row in common model:
 - kind = 'Sjbz' if type=1, kind='Djbz' if type=2
 - position, entry_name, dump_path copied over
 - For every djvudict sjbz_info row:
 - create pages row:
 - page_number can be derived from forms.position (or stored position directly)
 - store width, height, dpi
 - link the Sjbz form to its page_id
 - set forms.shared_form_id using sjbz_info.djbz_id (if present)

 ### Shapes
 For each row in djvudict letters:
 - create (or reuse) a shape_definitions row:
 - if BMP dump exists, compute a hash from the bitmap file and dedupe by hash
 - otherwise dedupe by (width,height,filename) or leave undeduped
 - create a shape_instances row:
 - source_tool='djvudict'
 - source_id = letters.id
 - form_id = letters.form_id
 - is_non_symbol = letters.is_non_symbol

 ### Dictionary membership
 - If letters.in_library = 1, create dictionary_membership:
 - form_id = letters.form_id
 - local_id = letters.local_id
 - in_library=1
 - library_kind = 'shared' if that form is Djbz else 'local'

 ### Occurrences
 - If letters.in_image = 1, create occurrences:
 - page_id from the Sjbz form’s linked page
 - (x,y,width,height) from letters row
 - ensure coordinate system is bottom-left (djvudict claims to store bottom-left)

 ### Relations
 - If letters.reference_id is not NULL:
 - create shape_relations linking this instance to referenced instance
 - set relation_type using is_refinement:
 - 1 → 'refinement'
 - 0 → 'copy'
 - add a note if source semantics are uncertain

 ---

 ## Import mapping: Shape Browser → common model

 Source tables: documents, dictionaries, shapes, blits.

 ### Documents/pages
 - Create one documents row for each Shape Browser documents record.
 - Create pages rows for every distinct page_number in blits for that document.
 - If page size/dpi is known elsewhere, fill pages.width/height/dpi; otherwise leave NULL.

 ### Forms (optional)
 Shape Browser does not explicitly store Djbz/Sjbz forms. Two options:
 - Minimal: create only Sjbz-like forms, one per page (kind='Sjbz', link to page_id).
 - Or: omit forms and leave form_id NULL in instances (allowed by schema).

 ### Shapes
 For each Shape Browser shapes row:
 - create (or reuse) a shape_definitions row:
 - width/height from DB
 - bits_blob from shapes.bits (if appropriate)
 - optionally compute bits_hash to dedupe
 - create a shape_instances row:
 - source_tool='shape-browser'
 - source_id = shapes.id
 - page_id may be NULL (shape identity is global); occurrences will bind it to pages

 ### Occurrences
 For each row in Shape Browser blits:
 - create an occurrences row:
 - page_id from pages(document_id,page_number)
 - shape_instance_id from instance for shape_id
 - (x,y) = (b_left,b_bottom)
 - (width,height) from the linked shape definition

 ### Relations (tree/prototype)
 Shape Browser has parent_id in shapes. This can be mapped as:
 - create shape_relations:
 - child = shape instance of shapes.id
 - parent = shape instance of shapes.parent_id
 - relation_type='tree_parent'

 This preserves the tree without claiming it is the same as refinement/prototype semantics.

 ---

 ## Export mapping: common model → source DBs (limits)

 ### common → Shape Browser
 This is feasible if:
 - you have global shape definitions with bits_blob compatible with the renderer,
 - you have occurrences per page.

 You may lose djvudict-specific form/dictionary distinctions unless you add extra tables.

 ### common → djvudict
 This is feasible to produce a compatible database, but not necessarily the original encoder’s dictionary strategy.

 If you don’t know the original dictionary membership rules, you must choose a policy, e.g.:
 - mark shapes as in_library=1 if they occur more than once on a page,
 - assign local_id sequentially per form,
 - omit refinements unless relations exist.

 ---

 ## Worked example plan (recommended)

 To make the common model understandable, document it using a real subtree and a real djvudict page:

 1) Pick one Shape Browser subtree root (e.g., 28147) and show:
 - shapes in subtree (tree relations)
 - occurrences on pages

 2) Pick one djvudict page form and show:
 - forms + sjbz_info
 - dictionary-only shapes (Djbz)
 - placed shapes (Sjbz)
 - a prototype chain (reference_id)

 Then show how both map into:
 - shape_definitions
 - shape_instances
 - occurrences
 - shape_relations

 ---


