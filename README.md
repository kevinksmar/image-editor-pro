# Image Editor Pro

[![Python app](https://github.com/thomas-sabu-cs/image-editor-pro/actions/workflows/python-app.yml/badge.svg)](https://github.com/thomas-sabu-cs/image-editor-pro/actions/workflows/python-app.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![PyQt6](https://img.shields.io/badge/PyQt-6.6.1-brightgreen)

A professional desktop image editing application built with Python and PyQt6. Image Editor Pro provides a free, open-source alternative to commercial image editors with powerful features including layer-based editing, drawing tools, image filters, and a complete undo/redo system.

---

## Feature Demo

A short demo helps viewers see the app in action. Add a GIF or short video here once you have one.

<!-- Replace the placeholder below with your demo asset (e.g. docs/demo.gif or a link to a short video). -->
<p align="center">
  <img src="docs/demo.gif" alt="Image Editor Pro – Feature Demo" width="720" />
</p>
<p align="center">
  <em>Quick demo: layers, drawing tools, and filters in action.</em>
</p>

**Tips:** Record with a tool like [ScreenToGif](https://www.screentogif.com/) or [LICEcap](https://www.cockos.com/licecap/). Keep it under 15 seconds and show: creating a layer, brushing, applying a filter, and zoom/pan.

---

## Screenshots

The UI uses a **modern dark theme**, **dockable panels**, and a **central canvas**. Use the grid below to showcase your screenshots.

### Main interface (dark mode + canvas)

| | |
|:---:|:---:|
| **Dark theme & canvas** | **Dockable panels** |
| ![Main window – dark mode and central canvas](docs/screenshots/main-dark-canvas.png) | ![Layers and Tools panels docked](docs/screenshots/panels-docked.png) |
| Dark mode (charcoal grays, blue accents), menu bar, toolbar, and central canvas with zoom. | Layers panel (left) and Tools panel (right) can be docked, floated, or hidden. |

### Panels and workflow

| | |
|:---:|:---:|
| **Layers panel** | **Filter dialog** |
| ![Layers list with thumbnails and opacity](docs/screenshots/layers-panel.png) | ![Filter dialog with live preview](docs/screenshots/filter-dialog.png) |
| Layer list with thumbnails, visibility toggles, opacity sliders, and add/remove. | Parametric filters (e.g. Blur, Brightness) with live preview and sliders. |

**How to add your images:** Place files in `docs/screenshots/` with the names above (e.g. `main-dark-canvas.png`, `panels-docked.png`, `layers-panel.png`, `filter-dialog.png`). If you use different names, update the paths in this table.

---

## 🌟 Features

### Core Editing Features
- **Layer System**
  - Add, delete, and reorder layers
  - Adjust layer opacity (0-100%)
  - Toggle layer visibility
  - Layer thumbnails for easy identification
  - Duplicate and merge layers
  
- **Drawing Tools**
  - Brush tool with adjustable size (1-200px) and opacity
  - Eraser tool for removing content
  - Color picker with full RGB color selection
  - Real-time drawing preview

- **Image Filters & Adjustments**
  - Blur (Gaussian blur with adjustable radius)
  - Sharpen, Brightness, Contrast, Hue/Saturation
  - Grayscale, Invert, Edge detection
  - Sepia, Posterize (adjustable bits)
- **Image Transforms**
  - Flip Horizontal / Flip Vertical
  - Rotate 90° CW / 90° CCW / 180°
  - Resize Image (canvas and all layers)
  - Canvas Size (expand/shrink with 9-position anchor)
  - Crop (to rectangle)
  - Make color transparent
- **Edit**
  - Clear Layer, Fill
  - Copy Merged (Ctrl+Shift+C), Paste as New Layer (Ctrl+Shift+V)
- **Layer**
  - Flatten Image (merge all layers into one; undoable)
- **File**
  - Revert (reload from last saved .iep when modified)
- **Transparency**
  - New project: choose **White** or **Transparent** background
  - View > Transparency display: **Checkerboard**, **White**, **Gray**, or **Black** (preview on different backgrounds)

- **File Operations**
  - Open images (PNG, JPG, JPEG, BMP, GIF)
  - Save images (PNG, JPG with format conversion)
  - Save/Load custom `.iep` project format (preserves all layers)
  - New project creation with custom dimensions

- **Undo/Redo System**
  - Full undo/redo support for all operations
  - Command pattern implementation
  - History limit (default: 50 operations)
  - Keyboard shortcuts support

- **User Interface**
  - Professional, intuitive interface
  - Dockable panels (layers, tools)
  - Zoom in/out/reset functionality
  - Keyboard shortcuts for common actions
  - Menu bar with organized features
  - Toolbar for quick access

## 📋 Requirements

- **Python:** 3.8 or higher
- **Operating System:** Windows, macOS, or Linux
- **Dependencies:** See `requirements.txt`

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/thomas-sabu-cs/image-editor-pro.git
cd image-editor-pro
```

### 2. Create a Virtual Environment (Recommended)

```bash
# On Windows
python -m venv venv
venv\\Scripts\\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Application

```bash
python main.py
```

## 📖 Usage Guide

### Getting Started

1. **Create a New Project**
   - Click `File > New` or press `Ctrl+N`
   - Enter desired width and height
   - A new blank project will be created

2. **Open an Image**
   - Click `File > Open Image` or press `Ctrl+O`
   - Select an image file (PNG, JPG, etc.)
   - The image will load as the background layer

### Working with Layers

- **Add a Layer:** Click the `+` button in the Layers panel or use `Layer > New Layer` (`Ctrl+Shift+N`)
- **Remove a Layer:** Select a layer and click the `-` button
- **Reorder Layers:** Use the `↑` and `↓` buttons to move layers up or down
- **Adjust Opacity:** Use the opacity slider in the Layers panel
- **Toggle Visibility:** Check/uncheck the "Visible" checkbox
- **Duplicate Layer:** Use `Layer > Duplicate Layer` (`Ctrl+J`)
- **Merge Down:** Use `Layer > Merge Down` (`Ctrl+E`)

### Drawing

1. **Select a Tool**
   - Choose "Brush" or "Eraser" in the Tools panel
   
2. **Adjust Settings**
   - Set brush size (1-200px)
   - Set brush opacity (0-100%)
   - Choose a color (click "Choose Color" button)

3. **Draw on Canvas**
   - Click and drag on the canvas to draw
   - Release to complete the stroke
   - Use `Ctrl+Z` to undo if needed

### Applying Filters

1. Select the layer you want to apply the filter to
2. Go to `Filter` menu and choose a filter
3. For filters with parameters (Blur, Sharpen, etc.), adjust settings in the dialog
4. Click OK to apply

### Saving Your Work

- **Save as Image:** `File > Save Image` (`Ctrl+S`) - Exports the final composited image
- **Save as Project:** `File > Save Project` (`Ctrl+Shift+S`) - Saves the project with all layers as `.iep` file
- **Open Project:** `File > Open Project` (`Ctrl+Shift+O`) - Opens a previously saved `.iep` project

### Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| New Project | `Ctrl+N` |
| Open Image | `Ctrl+O` |
| Open Project | `Ctrl+Shift+O` |
| Save Image | `Ctrl+S` |
| Save Project | `Ctrl+Shift+S` |
| Undo | `Ctrl+Z` |
| Redo | `Ctrl+Y` or `Ctrl+Shift+Z` |
| New Layer | `Ctrl+Shift+N` |
| Duplicate Layer | `Ctrl+J` |
| Merge Down | `Ctrl+E` |
| Zoom In | `Ctrl++` |
| Zoom Out | `Ctrl+-` |
| Reset Zoom | `Ctrl+0` |
| Fit to Window | `Ctrl+1` |
| Zoom (mouse) | Ctrl + scroll wheel over canvas |
| Quit | `Ctrl+Q` |

For a full **Photoshop-style feature checklist** (what we have vs. what’s not implemented), see [docs/PHOTOSHOP_FEATURES.md](docs/PHOTOSHOP_FEATURES.md).

## 🏗️ Architecture Overview

Image Editor Pro follows a clean, modular architecture based on the Model-View-Controller (MVC) pattern:

### Project Structure

```
image-editor-pro/
├── src/                    # Source code
│   ├── __init__.py        # Package initialization
│   ├── models.py          # Data models (Layer, Project)
│   ├── commands.py        # Command pattern for undo/redo
│   ├── filters.py         # Image filter implementations
│   ├── canvas.py          # Canvas widget for drawing
│   ├── panels.py          # UI panels (layers, tools)
│   └── main_window.py     # Main application window
├── assets/                # Assets (icons, images)
├── docs/                  # Documentation
├── tests/                 # Unit tests
├── main.py               # Application entry point
├── requirements.txt      # Python dependencies
├── .gitignore           # Git ignore rules
├── LICENSE              # MIT License
└── README.md            # This file
```

### Core Components

#### 1. Models (`models.py`)
- **Layer:** Represents a single image layer with properties (opacity, visibility, name)
- **Project:** Manages multiple layers, canvas dimensions, and rendering

#### 2. Commands (`commands.py`)
- Implements the Command pattern for undo/redo functionality
- Each action (draw, add layer, apply filter) is encapsulated as a command
- **CommandHistory:** Manages undo/redo stacks

#### 3. Filters (`filters.py`)
- Pure functions for image processing
- Uses PIL/Pillow and NumPy for efficient operations
- Filters: blur, sharpen, brightness, contrast, hue/saturation, etc.

#### 4. Canvas (`canvas.py`)
- **Canvas:** Main drawing widget, handles mouse events and rendering
- **CanvasScrollArea:** Provides zoom and pan functionality

#### 5. Panels (`panels.py`)
- **LayerPanel:** UI for layer management
- **ToolOptionsPanel:** UI for tool settings and color picker

#### 6. Main Window (`main_window.py`)
- **MainWindow:** Integrates all components
- Handles menu actions, file operations, and signal routing

### Design Patterns Used

1. **Model-View-Controller (MVC)**
   - Models: `Layer`, `Project`
   - Views: `Canvas`, `LayerPanel`, `ToolOptionsPanel`
   - Controller: `MainWindow`

2. **Command Pattern**
   - All operations are commands that can be undone/redone
   - Enables flexible history management

3. **Observer Pattern**
   - Qt signals/slots for component communication
   - Loose coupling between components

4. **Strategy Pattern**
   - Different filters as interchangeable strategies
   - Easy to add new filters

## 🔧 How to Contribute/Extend

### Adding a New Filter

1. Add your filter function to `src/filters.py`:

```python
@staticmethod
def my_new_filter(image: Image.Image, param1: float) -> Image.Image:
    \"\"\"Apply my new filter.
    
    Args:
        image: Input PIL Image
        param1: Filter parameter
        
    Returns:
        Filtered image
    \"\"\"
    # Your filter implementation
    return processed_image
```

2. Add menu action in `src/main_window.py` in `setup_menus()`:

```python
new_filter_action = QAction("My New Filter", self)
new_filter_action.triggered.connect(lambda: self.apply_filter("My New Filter"))
filter_menu.addAction(new_filter_action)
```

3. Add filter application logic in `apply_filter()` method

### Adding a New Tool

1. Extend the `Canvas` class in `src/canvas.py`
2. Add tool selection in `ToolOptionsPanel` in `src/panels.py`
3. Implement tool behavior in mouse event handlers

## Testing

The project includes unit tests for filters and the undo/redo command system. Run the test suite with [pytest](https://pytest.org/).

### Running the test suite

1. Install dependencies (including pytest) from the project root:

   ```bash
   pip install -r requirements.txt
   ```

2. Run all tests:

   ```bash
   pytest tests/ -v
   ```

3. Run only filter tests or only command tests:

   ```bash
   pytest tests/test_filters.py -v
   pytest tests/test_commands.py -v
   ```

### What is tested

- **`tests/test_filters.py`** – Every filter in `src/filters.py` (Blur, Sharpen, Brightness, Contrast, Hue/Saturation, Grayscale, Invert, Edge Detect, Sepia, Posterize, Emboss, Smooth, Detail, etc.) is run on a small dummy image. Tests check that each filter returns a valid `PIL.Image.Image`, preserves dimensions, and (where relevant) output mode (e.g. Grayscale/Invert output mode). One test ensures filters do not mutate the input image.
- **`tests/test_commands.py`** – Command history and basic commands (Add Layer, Remove Layer, Filter, Draw, Opacity, Clear Layer, Resize) are tested. For each, the test performs an action, calls `undo()`, then `redo()`, and asserts that the project state (layer count, layer content, dimensions, opacity) is consistent after the round-trip.

### Running Tests (short reference)

```bash
pip install -r requirements.txt
pytest tests/ -v
```

## 🐛 Known Issues

- Large images (>10000x10000px) may cause performance issues
- Undo history is limited to 50 operations by default
- Some filters may take time on large layers

## 🗺️ Roadmap

Planned **advanced** features to make Image Editor Pro even more competitive with professional tools:

| Feature | Description | Status |
|--------|-------------|--------|
| **AI upscaling** | Enhance resolution using a local or API-based model (e.g. Real-ESRGAN-style) for high-quality upscaling. | 🔜 Coming soon |
| **Layer masks** | Non-destructive masking per layer with brush/gradient for compositing and effects. | 🔜 Coming soon |
| **SVG export** | Export vector paths and shapes to SVG in addition to raster PNG/JPEG. | 🔜 Coming soon |
| **Non-destructive adjustment layers** | Apply brightness, contrast, etc. as reusable layers that can be edited or toggled without baking pixels. | 🔜 Coming soon |
| **Plugin / extension API** | Allow third-party filters and tools via a simple Python plugin API. | 🔜 Coming soon |

This roadmap shows long-term direction; implementation order may change based on feedback and contribution.

---

## 🔮 Future Enhancements

- [ ] Selection tools (rectangular, elliptical, lasso)
- [ ] Text tool
- [ ] Shape tools (rectangle, circle, line)
- [ ] More filters (gaussian blur, motion blur, etc.)
- [ ] Brush presets
- [ ] History panel
- [ ] Export templates

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) for the GUI framework
- Image processing powered by [Pillow](https://python-pillow.org/)
- Efficient array operations with [NumPy](https://numpy.org/)

## 📧 Contact & Support

If you have questions, suggestions, or issues:
- Open an issue on GitHub
- Check the documentation in the `docs/` folder
- Read the inline code documentation

- **Contributors:** See **[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)** for architecture (MVC, Command pattern), data flow, and how to add filters or tools.  
- **Releases:** [v1.0.0 release notes](docs/RELEASE_v1.0.0.md) (build system, CI/CD, dark theme, logging).

---

**Made with ❤️ using Python and PyQt6**

*A free alternative for your image editing needs!*
