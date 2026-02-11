# revealshapes1 – Shape Hierarchy Browser
## Clean Redesign Architecture Document
### Minimal Initial Scope

Author: Draft for new branch of revealshapes1  
Status: Architectural proposal (Phase 1 focus)

---

# 1. Objective

Develop a new, clean, minimal shape browser as a new branch of:

    revealshapes1

Initial goal:

    Browse the shape hierarchy conveniently.

Not included in Phase 1:

- Labelling
- OCR integration
- HTML export
- Editing shapes
- Dictionary inheritance handling (initially)
- Page-level reconstruction
- Performance micro-optimizations

Clarity first. Features later.

---

# 2. Design Philosophy

Legacy issues observed:

- Tight GUI–database coupling
- No clean separation of layers
- Rendering mixed with DB access
- Likely no bitmap caching
- Heavy operations in GUI thread

Redesign principles:

- Strict separation of concerns
- Lazy decoding
- Explicit caching
- Testable non-GUI core
- No SQL inside GUI code
- No decoding inside paint handlers

---

# 3. Minimal Functional Requirements (Phase 1)

The system must:

1. Connect to MariaDB database created by exportshapes.
2. Load one document.
3. Load all shapes belonging to that document.
4. Build shape hierarchy using parent_id.
5. Display:
   - Shape ID
   - Parent ID
   - Width, height
   - Bitmap preview
6. Navigate parent/children relations interactively.

Optional (if trivial):

- Show usage count via blits.

---

# 4. Relevant Database Structure

Core tables:

    documents
        ↓
    dictionaries
        ↓
    shapes
        ↓
    blits

Hierarchy is defined solely by:

    shapes.parent_id → shapes.id

For Phase 1, only shapes are required.

---

# 5. Clean Layered Architecture

The system will consist of four strict layers.

---

## 5.1 Data Access Layer (DAL)

Responsibilities:

- Pure SQL
- No GUI
- No rendering
- No business logic

Example (Python-style pseudocode):

    class ShapeRepository:
        def get_shapes_by_document(document_id)
        def get_shape(shape_id)
        def get_children(shape_id)

Rules:

- Returns plain Python (or C++) objects
- No bitmap decoding
- No caching
- No GUI imports

---

## 5.2 Domain Model Layer

Defines structured in-memory representation.

    class Shape:
        id: int
        parent_id: Optional[int]
        width: int
        height: int
        bits: bytes

Hierarchy builder:

    class ShapeTree:
        children_map: Dict[int, List[int]]
        root_shapes: List[int]

This layer:

- Builds tree
- Organizes relationships
- Does not decode images

---

## 5.3 Rendering Layer

Responsibility:

- Decode JB2 bits → bitmap
- Cache decoded bitmaps

Critical rule:

    Never decode inside paint events.

Example:

    class ShapeRenderer:
        bitmap_cache: Dict[int, Bitmap]

        def get_bitmap(shape):
            if shape.id not in cache:
                decode and cache
            return cached bitmap

Decoding happens once per shape.

---

## 5.4 GUI Layer

Responsibilities:

- Display shape tree (left panel)
- Display bitmap preview (right panel)
- Handle selection
- Trigger rendering

GUI must:

- Never execute SQL
- Never decode blobs directly
- Only call repository + renderer APIs

---

# 6. Minimal GUI Design

Two-pane layout:

    ---------------------------------
    | Shape Tree | Shape Preview    |
    |            |                  |
    ---------------------------------

Left:

- Hierarchical tree view
- Expand/collapse parent-child relationships

Right:

- Large bitmap preview
- Metadata display

Optional future panel:

- Child thumbnails grid

---

# 7. Shape Hierarchy Logic

Hierarchy construction:

    children = defaultdict(list)

    for shape in shapes:
        children[shape.parent_id].append(shape.id)

Root shapes:

    parent_id IS NULL
    or parent_id = 0

(depending on DB semantics)

---

# 8. Rendering Strategy

Flow:

1. User selects shape.
2. GUI requests bitmap from ShapeRenderer.
3. Renderer checks cache.
4. If not cached:
       decode bits
       store bitmap
5. GUI displays bitmap.

No SQL during repaint.
No decoding during repaint.

---

# 9. Performance Baseline (Phase 1)

Even minimal implementation should:

- Load all shapes in one SQL query.
- Build hierarchy in memory.
- Decode lazily.
- Cache bitmaps permanently for session.

This alone avoids:

- Per-shape SQL queries
- Per-paint decoding
- GUI freezes

---

# 10. Suggested Technology Options

If staying in C++ (aligned with revealshapes1):

    C++ + Qt Widgets

Advantages:
- Native performance
- Consistent with libdjvu
- Strong tree and image widgets

If using Python for rapid iteration:

    Python + PySide6 / PyQt6

Advantages:
- Faster prototyping
- Simpler experimentation

Recommendation:
Choose based on long-term maintainability.

---

# 11. Suggested Branch Structure

New branch:

    feature/shape-browser

Suggested directory layout:

    /shape_browser/
        repository.*
        model.*
        renderer.*
        gui/
            MainWindow.*
            ShapeTreeWidget.*
            ShapePreviewWidget.*

Keep completely independent from legacy GUI code.

---

# 12. Development Phases

Phase 1:
    Load shapes.
    Print hierarchy in console.

Phase 2:
    Basic GUI with tree + preview.

Phase 3:
    Introduce bitmap caching.

Phase 4:
    Add usage statistics via blits.

---

# 13. Explicit Non-Goals (for Now)

- Labeling
- Editing
- Export
- OCR
- Page reconstruction
- Inherited dictionaries handling

This tool is strictly:

    Shape hierarchy exploration tool.

---

# 14. Why This Architecture Is Safe

It eliminates:

- Tight coupling
- Per-shape SQL
- Repeated blob decoding
- GUI-thread blocking

Even naive implementation will outperform legacy system.

---

# 15. Future Extension Points

After stabilization:

- Page reconstruction view
- Shape frequency heatmap
- Similarity clustering
- Dictionary inheritance visualization
- Graph visualization of hierarchy

But not before core is stable.

---

# End of Document
