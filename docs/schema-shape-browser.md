 # Shape Browser database schema (MariaDB)

 This document describes the database used by Shape Browser (“shape-browser4djvu”) and explains how the GUI fields relate to database tables.

 Terminology
 - “Shape” = a bitmap element stored in a dictionary (may be a letter, punctuation, etc.).
 - “Occurrence” = a placement of a shape on a page (a “blit”).
 - “Tree / subtree” = parent-child structure between shapes (encoder-dependent).

 ---

 ## Tables used by the current code

 Shape Browser queries these tables (see shape_browser/repository.py):

 ### documents
 Provides available documents.

 Columns used:
 - id (PK)
 - document (filename or label)

 ### dictionaries
 Links shapes to a document.

 Columns used indirectly:
 - id (PK)
 - document_id (FK → documents.id)

 ### shapes
 Stores bitmap shapes.

 Columns used:
 - id (PK)
 - dictionary_id (FK → dictionaries.id)
 - parent_id (tree parent; may be NULL or -1 for roots, depending on dataset)
 - width, height (pixels)
 - bits (bitmap payload; format is renderer-specific)

 ### blits
 Stores occurrences (placements) of shapes.

 Columns used:
 - document_id (FK → documents.id)
 - shape_id (FK → shapes.id)
 - page_number (0-based)
 - b_left (x coordinate)
 - b_bottom (y coordinate)

 Coordinate convention used by Shape Browser:
 - origin is bottom-left
 - x = b_left, y = b_bottom

 ---

 ## Derived fields shown in the GUI

 These are not stored directly; they’re computed in shape_browser/model.py.

 ### Usage (shape.usage_count)
 Definition: number of occurrences of the shape in blits for the selected document.

 Computation: for every row in blits belonging to the document:
 - create an Occurrence
 - append it to shape.occurrences
 - increment shape.usage_count

 Equivalent SQL for one document:
  SELECT shape_id, COUNT() AS usage
  FROM blits
  WHERE document_id = <doc_id>
  GROUP BY shape_id;

 ### Subtree usage (shape.subtree_count)
 Definition: sum of usage_count for the shape plus all descendants in its tree.

 Computation: post-order traversal:
 - subtree_count(shape) = usage_count(shape) + Σ subtree_count(child)

 ### Depth (shape.depth)
 Definition: distance from root in the parent-child tree.

 Computation: DFS from each root shape, assigning depth = parent.depth + 1.

 ### Sibling index (shape.sibling_index)
 Definition: ordinal number among siblings (1-based).

 Important nuance: sibling indices are assigned in the full model and do not change when filtering; therefore large values (e.g. 0.14007) can appear even when only one root is visible.

 ---

 ## Worked example (from the GUI subtree screenshot)

 Use one real subtree as a running example to explain the tree-related fields.

 Example root selected:
 - Shape ID: 28147
 - Parent: -1 (root)
 - Size: 22 x 46
 - Depth: 0
 - Usage: 1
 - Subtree usage: 18
 - Subtree nodes shown: 18

 Interpretation:
 - Only one occurrence of the root itself (usage_count=1).
 - The subtree contains 18 total occurrences across all nodes in the subtree (subtree_count=18).
 - The GUI’s “Nodes: 18” means the subtree has 18 shapes (nodes), not occurrences.

 Occurrences panel example:
 - “Occurrences: 1 (1 pages)”
 - “Page 24 (1)”
 - occurrence line: x=1949 y=2469

 Interpretation:
 - This shape appears once on page 24.
 - Coordinates are bottom-left origin (b_left, b_bottom).

 Grid badge format:
 - Badge shown: {depth}.{sibling_index} (p:{parent_id})
 - Example: 1.1 (p:28147) means depth 1, first child of shape 28147.

 Recommendation for avoiding confusion: consider changing depth.sibling_index to depth:sibling_index in the badge display.

 ---

 ## Practical SQL snippets

 Find the most frequent shapes in a document:
  SELECT shape_id, COUNT() AS c
  FROM blits
  WHERE document_id = <doc_id>
  GROUP BY shape_id
  ORDER BY c DESC
  LIMIT 20;

 Inspect a specific shape (including bitmap length):
  SELECT id, width, height, parent_id, OCTET_LENGTH(bits) AS bits_len
  FROM shapes
  WHERE id = <shape_id>;

 List occurrences of a shape on pages:
  SELECT page_number, b_left, b_bottom
  FROM blits
  WHERE document_id = <doc_id> AND shape_id = <shape_id>
  ORDER BY page_number;
 

 ### dictionaries
 Links shapes to a document and indicates whether a dictionary is page-specific or shared.

 Columns:
 - id (PK)
 - document_id (FK → documents.id)
 - page_number (INT)
 - >= 0 = page-specific (local) dictionary for that page
 - -1 = shared dictionary
 - dictionary_name (VARCHAR)
 - for page-specific dictionaries, this is the page name the dictionary comes from
 - for shared dictionaries, the name identifies the shared dictionary chunk/group (encoder-dependent)

 Notes: Shape Browser currently does not use dictionary_name or page_number in queries; it only uses document_id to load all shapes for a document.
