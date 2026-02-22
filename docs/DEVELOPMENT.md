# Development Guide

This document is for **developers who want to contribute** to Image Editor Pro. It explains the architecture, data flow, and how to run, test, and extend the codebase. For high-level design, see [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Quick Start

```bash
git clone https://github.com/thomas-sabu-cs/image-editor-pro.git
cd image-editor-pro
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
python main.py
```

Run tests:

```bash
export PYTHONPATH=.   # or set PYTHONPATH to repo root
pytest tests/ -v
```

Lint:

```bash
pip install flake8
flake8 src/ main.py build_exe.py
```

---

## Project Layout

```
image-editor-pro/
├── main.py              # Entry point; sets up logging and launches MainWindow
├── build_exe.py         # PyInstaller script for packaging
├── requirements.txt
├── .flake8              # Lint config (max-line-length 127, ignore W293)
├── src/
│   ├── main_window.py   # Main window, menus, toolbar, docks, filter application
│   ├── models.py        # Layer, Project (data + serialization)
│   ├── commands.py      # Command pattern: all undoable operations + CommandHistory
│   ├── filters.py      # Image filters (blur, sharpen, brightness, etc.)
│   ├── canvas.py       # Canvas widget + CanvasScrollArea (drawing, zoom, pan)
│   ├── panels.py       # LayerPanel, ToolOptionsPanel, HistoryPanel
│   ├── worker.py       # FilterWorker (QThread) for non-blocking filter application
│   ├── styles.qss      # Dark theme stylesheet
│   └── styles.py       # Legacy/fallback theme (optional)
├── tests/
│   ├── conftest.py     # Pytest config; adds repo root to path, optional QApplication
│   ├── test_filters.py # Unit tests for every filter
│   └── test_commands.py# Undo/redo and command consistency tests
├── docs/
│   ├── ARCHITECTURE.md # Design patterns and component details
│   ├── DEVELOPMENT.md # This file
│   ├── PHOTOSHOP_FEATURES.md
│   └── screenshots/   # Place screenshots here for README
└── .github/workflows/
    └── python-app.yml # CI: pytest + flake8 on push to main
```

---

## Architecture in Detail

### Model–View–Controller (MVC)

- **Model**  
  - **`Layer`** (`models.py`): name, PIL `image`, visibility, opacity, optional `filter_history` for “remove last filter.”  
  - **`Project`** (`models.py`): width, height, list of `Layer`s, `render()` to composite visible layers, signals `layers_changed`, `layer_modified`.

- **View**  
  - **`Canvas`** (`canvas.py`): paints `project.render()`, handles mouse (draw, brush, eraser, shapes, eyedropper, paint bucket).  
  - **`LayerPanel`**, **`ToolOptionsPanel`**, **`HistoryPanel`** (`panels.py`): dockable UIs for layers, tools, and history.

- **Controller**  
  - **`MainWindow`** (`main_window.py`): builds menus, toolbar, docks; connects actions to project/commands; applies filters (via worker), file I/O, and dialogs.  
  - User actions flow: **View** (click/menu) → **MainWindow** (handler) → **Command** or **Project** → **Model** updated → **signals** → **View** refreshes.

No business logic lives in the view; the controller never holds image data, only references to `Project` and `CommandHistory`.

### Command Pattern (Undo/Redo)

Every user action that changes state is a **command**:

1. **Execute:** run the action and push the command onto `CommandHistory.undo_stack`; clear `redo_stack`.  
2. **Undo:** pop from `undo_stack`, call `command.undo()`, push command onto `redo_stack`.  
3. **Redo:** pop from `redo_stack`, call `command.execute()`, push onto `undo_stack`.

Commands in `commands.py`:

- **DrawCommand**, **FilterCommand**, **FillLayerCommand**, **ClearLayerCommand**: store `old_image` and `new_image`; `execute()` sets layer to `new_image`, `undo()` sets layer to `old_image`.  
- **AddLayerCommand** / **RemoveLayerCommand**: add/remove layer and record index so undo/redo can reverse it.  
- **MoveLayerCommand**, **SetLayerOpacityCommand**, **SetLayerVisibilityCommand**: store previous and new state; undo restores previous.  
- **ResizeProjectCommand**, **CropProjectCommand**, **CanvasSizeCommand**: store old dimensions and old layer images; undo restores them.  
- **FlattenImageCommand**: store old layers and dimensions; undo restores the full layer stack.

**CommandHistory** limits the size of `undo_stack` (e.g. 50) so memory stays bounded.

### Strategy Pattern (Filters)

All filters live in **`Filters`** (`filters.py`) as static methods. Each takes a PIL `Image` and optional parameters, and returns a **new** PIL `Image`. The controller (or `FilterWorker`) calls the right method by name and applies the result to the layer via **FilterCommand**. Adding a new filter = add a method + menu entry + branch in the worker and/or `apply_filter()`.

### Observer Pattern (Qt Signals)

- **Project** emits `layers_changed` when the list changes (add/remove/reorder), and `layer_modified` when a layer’s image or properties change.  
- **Canvas** and **panels** subscribe to these and call `update()` or refresh lists so the UI stays in sync with the model without the controller polling.

---

## Data Flow Examples

### Drawing on the canvas

1. User drags with the brush.  
2. **Canvas** mouse handlers draw on `project.get_layer(active_index).image` (and keep a pre-draw copy).  
3. On release, **Canvas** emits `drawing_completed(old_image, new_image, layer_index)`.  
4. **MainWindow** creates **DrawCommand**(project, layer_index, old_image, new_image) and runs `command_history.execute(command)`.  
5. **DrawCommand.execute()** sets the layer’s image to `new_image` and emits `layer_modified`.  
6. **Canvas** and **LayerPanel** update from the new project state.

### Applying a filter

1. User picks a filter from the menu (with or without a parameter dialog).  
2. **MainWindow** pushes the current layer image onto the layer’s `filter_history`, shows a progress dialog, and sends work to **FilterWorker** (QThread).  
3. **FilterWorker** runs the appropriate `Filters.*` method and emits `result_ready(new_image)`.  
4. **MainWindow** receives the result, closes the progress dialog, creates **FilterCommand**(…, old_image, new_image) and runs `command_history.execute()`.  
5. Layer image and UI update as above.

---

## How to Add a New Filter

1. **Implement the filter** in `src/filters.py`:
   - Add a `@staticmethod` that takes `image: Image.Image` and any parameters, and returns a new PIL Image.
2. **Expose it in the UI** in `src/main_window.py`:
   - In `setup_menus()`, add a menu action that calls `self.apply_filter("Your Filter Name")`.
   - In `apply_filter()`, add a branch that calls your filter (or send it through the worker for heavy work).
3. **Optional:** If the filter has parameters, add a dialog (or extend `FilterDialog`) and pass parameters into the filter and into the worker if used.
4. **Tests:** Add a test in `tests/test_filters.py` that runs the filter on a small image and checks return type and size/mode.

---

## How to Add a New Tool

1. **Canvas** (`canvas.py`): Add a tool id (e.g. `"my_tool"`), handle it in `mousePressEvent` / `mouseMoveEvent` / `mouseReleaseEvent`, and emit `drawing_completed` when the stroke is done.  
2. **ToolOptionsPanel** (`panels.py`): Add a button or control that calls `tool_changed.emit("my_tool")`.  
3. **MainWindow**: Ensure the canvas’s active layer and tool are wired (usually already via existing signals).  
4. **Commands:** If the tool changes layer pixels, use **DrawCommand** (same as brush). If it does something else (e.g. add a vector shape), introduce a new command type in `commands.py` and execute it from the main window.

---

## Code Style and CI

- **flake8** is used with config in `.flake8`: max line length 127, ignore W293 (blank line whitespace).  
- Run `flake8 src/ main.py build_exe.py` before pushing.  
- **CI** (`.github/workflows/python-app.yml`) runs on every push to `main`: sets up Python 3.10, installs from `requirements.txt`, runs `pytest tests/` and `flake8`. Fix any failing step to keep the build green.

---

## Logging and Debugging

- **main.py** configures logging to a file **`app.log`** (next to `main.py`) and to stderr. Use it to diagnose startup failures or unhandled exceptions in the field.  
- For development, watch the console; for user reports, ask for the `app.log` file.

---

## Packaging (Build System)

- **build_exe.py** uses **PyInstaller** to produce a windowed executable.  
- It bundles **src** and optionally **assets**; you can point to an icon via **assets/icon.ico** (or **assets/icon.png**).  
- Run: `pip install pyinstaller` then `python build_exe.py`. Output appears under **dist/**.

---

## Summary

| Concern | Where it lives |
|--------|-----------------|
| Data (layers, project) | `models.py` |
| Undo/redo (commands) | `commands.py` |
| Image processing | `filters.py` |
| Background filter work | `worker.py` |
| Drawing and canvas UI | `canvas.py` |
| Panels (layers, tools, history) | `panels.py` |
| Menus, toolbar, dialogs, wiring | `main_window.py` |
| Theme | `styles.qss` (loaded by main window) |
| Tests | `tests/` |
| CI | `.github/workflows/python-app.yml` |

For more detail on components and extension points, see [ARCHITECTURE.md](ARCHITECTURE.md).
