"""Main window for Image Editor Pro.

This module provides the main application window with all UI components.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QDockWidget,
    QToolBar, QFileDialog, QMessageBox, QInputDialog,
    QDialog, QLabel, QDialogButtonBox, QSpinBox, QFormLayout,
    QStatusBar, QColorDialog, QApplication, QComboBox, QStyle,
    QLineEdit, QPushButton, QProgressDialog
)
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QAction, QKeySequence, QColor, QImage, QPixmap, QShortcut
from PIL import Image, ImageDraw, ImageFont
import os
import io
import json
import numpy as np
from typing import Tuple

from models import Project
from canvas import Canvas, CanvasScrollArea
from panels import LayerPanel, ToolOptionsPanel, HistoryPanel
from commands import (
    CommandHistory, DrawCommand, AddLayerCommand, RemoveLayerCommand,
    MoveLayerCommand, SetLayerOpacityCommand, SetLayerVisibilityCommand,
    FilterCommand, RemoveLastFilterCommand, ResizeProjectCommand, ClearLayerCommand,
    CropProjectCommand, FillLayerCommand, CanvasSizeCommand, FlattenImageCommand
)
from filters import Filters

# Font choices for Add Text: (display name, font filename in Windows Fonts)
ADD_TEXT_FONTS = [
    ("Arial", "arial.ttf"),
    ("Times New Roman", "times.ttf"),
    ("Courier New", "cour.ttf"),
    ("Georgia", "georgia.ttf"),
    ("Verdana", "verdana.ttf"),
    ("Trebuchet MS", "trebuc.ttf"),
    ("Comic Sans MS", "comic.ttf"),
]


class AddTextDialog(QDialog):
    """Dialog for Layer > Add Text: text, font, size, color, position."""
    
    def __init__(self, layer_width: int, layer_height: int, parent=None):
        super().__init__(parent)
        self.layer_width = layer_width
        self.layer_height = layer_height
        self.setWindowTitle("Add Text")
        self.setup_ui()
    
    def setup_ui(self):
        layout = QFormLayout(self)
        self.text_edit = QLineEdit()
        self.text_edit.setPlaceholderText("Enter text")
        self.text_edit.setText("Hello")
        layout.addRow("Text:", self.text_edit)
        self.font_combo = QComboBox()
        for name, _ in ADD_TEXT_FONTS:
            self.font_combo.addItem(name)
        layout.addRow("Font:", self.font_combo)
        self.size_spin = QSpinBox()
        self.size_spin.setRange(8, 200)
        self.size_spin.setValue(24)
        layout.addRow("Font size:", self.size_spin)
        self.color_btn = QPushButton("Choose color")
        self.color_btn.clicked.connect(self._pick_color)
        self._text_color = QColor(0, 0, 0)
        self.color_btn.setStyleSheet(f"background-color: {self._text_color.name()};")
        layout.addRow("Color:", self.color_btn)
        self.position_combo = QComboBox()
        self.position_combo.addItems(["Top-left (10, 10)", "Center", "Custom position"])
        self.position_combo.currentIndexChanged.connect(self._on_position_changed)
        layout.addRow("Position:", self.position_combo)
        self.custom_x = QSpinBox()
        self.custom_x.setRange(0, 99999)
        self.custom_x.setValue(10)
        self.custom_y = QSpinBox()
        self.custom_y.setRange(0, 99999)
        self.custom_y.setValue(10)
        custom_layout = QHBoxLayout()
        custom_layout.addWidget(QLabel("X:"))
        custom_layout.addWidget(self.custom_x)
        custom_layout.addWidget(QLabel("Y:"))
        custom_layout.addWidget(self.custom_y)
        self.custom_widget = QWidget()
        self.custom_widget.setLayout(custom_layout)
        layout.addRow("", self.custom_widget)
        self.custom_widget.setVisible(False)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
    
    def _on_position_changed(self, idx):
        self.custom_widget.setVisible(idx == 2)
    
    def _pick_color(self):
        c = QColorDialog.getColor(self._text_color, self, "Text color")
        if c.isValid():
            self._text_color = c
            self.color_btn.setStyleSheet(f"background-color: {c.name()};")
    
    def get_text(self):
        return self.text_edit.text().strip()
    
    def get_font_index(self):
        return self.font_combo.currentIndex()
    
    def get_font_size(self):
        return self.size_spin.value()
    
    def get_color(self):
        return self._text_color
    
    def get_position(self, draw, text: str, font) -> Tuple[int, int]:
        """Return (x, y) for text placement. Uses layer size and optional bbox for center."""
        idx = self.position_combo.currentIndex()
        if idx == 0:
            return (10, 10)
        if idx == 2:
            return (self.custom_x.value(), self.custom_y.value())
        # Center: get text bbox
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            x = max(0, (self.layer_width - w) // 2)
            y = max(0, (self.layer_height - h) // 2)
            return (x, y)
        except Exception:
            return ((self.layer_width - 50) // 2, (self.layer_height - 20) // 2)


class FilterDialog(QDialog):
    """Dialog for applying filters with parameters. Supports initial values and optional live preview."""
    
    PREVIEW_MAX = 200  # max dimension for preview image
    
    def __init__(self, filter_name: str, parent=None, initial_params: dict = None, layer_image=None):
        """Initialize filter dialog.
        
        Args:
            filter_name: Name of the filter
            parent: Parent widget
            initial_params: Optional dict of last-used params to pre-fill
            layer_image: Optional PIL Image for live preview (downscaled); full res applied on OK
        """
        super().__init__(parent)
        self.filter_name = filter_name
        self.layer_image = layer_image  # PIL Image or None
        self.parameters = {}
        self.initial_params = initial_params or {}
        self.setup_ui()
        if self.layer_image is not None:
            self._connect_preview()
            self._update_preview()
    
    def _get_initial(self, key: str, default):
        """Get initial value for a param; convert factor to percent for spinboxes that use %."""
        return self.initial_params.get(key, default)
    
    def _preview_image(self) -> Image.Image:
        """Return a downscaled copy of layer_image for preview (max PREVIEW_MAX px)."""
        if self.layer_image is None:
            return None
        img = self.layer_image
        w, h = img.size
        if w <= 0 or h <= 0:
            return None
        scale = min(1.0, self.PREVIEW_MAX / max(w, h))
        if scale >= 1.0:
            return img.copy()
        nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
        return img.resize((nw, nh), Image.Resampling.LANCZOS)
    
    def _apply_filter_to_image(self, img: Image.Image, params: dict) -> Image.Image:
        """Apply current filter by name to img with params. Returns new PIL Image."""
        if self.filter_name == "Blur":
            return Filters.blur(img, **params)
        if self.filter_name == "Sharpen":
            return Filters.sharpen(img, **params)
        if self.filter_name == "Brightness":
            return Filters.adjust_brightness(img, **params)
        if self.filter_name == "Contrast":
            return Filters.adjust_contrast(img, **params)
        if self.filter_name == "Hue/Saturation":
            return Filters.adjust_hue_saturation(img, **params)
        if self.filter_name == "Posterize":
            return Filters.posterize(img, **params)
        return img
    
    def _update_preview(self):
        """Update preview label with current params (downscaled layer + filter)."""
        if self.layer_image is None or not hasattr(self, "preview_label"):
            return
        try:
            params = self.get_parameters()
            preview_img = self._preview_image()
            if preview_img is None:
                return
            filtered = self._apply_filter_to_image(preview_img, params)
            # PIL RGBA to QPixmap
            arr = np.array(filtered)
            if arr.size == 0:
                return
            h, w, ch = arr.shape
            qimg = QImage(arr.data, w, h, ch * w, QImage.Format.Format_RGBA8888)
            self.preview_label.setPixmap(QPixmap.fromImage(qimg.copy()).scaled(
                self.PREVIEW_MAX, self.PREVIEW_MAX, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
        except Exception:
            pass
    
    def _connect_preview(self):
        """Connect all parameter controls to _update_preview."""
        for name in [
            "radius_spinbox", "factor_spinbox", "bits_spinbox",
            "hue_spinbox", "saturation_spinbox",
        ]:
            w = getattr(self, name, None)
            if w is not None:
                w.valueChanged.connect(self._update_preview)
    
    def setup_ui(self):
        """Set up the user interface."""
        self.setWindowTitle(f"Apply {self.filter_name}")
        layout = QFormLayout(self)
        
        if self.layer_image is not None:
            self.preview_label = QLabel()
            self.preview_label.setFixedSize(self.PREVIEW_MAX, self.PREVIEW_MAX)
            self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.preview_label.setStyleSheet("background: #2d2d2d; border: 1px solid #555;")
            self.preview_label.setScaledContents(False)
            layout.addRow("Preview:", self.preview_label)
        
        # Add parameter controls based on filter type (use last-used values when available)
        if self.filter_name == "Blur":
            self.radius_spinbox = QSpinBox()
            self.radius_spinbox.setMinimum(1)
            self.radius_spinbox.setMaximum(50)
            self.radius_spinbox.setValue(self._get_initial("radius", 2))
            layout.addRow("Radius:", self.radius_spinbox)
        
        elif self.filter_name == "Sharpen":
            self.factor_spinbox = QSpinBox()
            self.factor_spinbox.setMinimum(100)
            self.factor_spinbox.setMaximum(500)
            # get_parameters returns factor as float (e.g. 1.5); spinbox is percent (150)
            default_val = int(self._get_initial("factor", 1.5) * 100)
            self.factor_spinbox.setValue(max(100, min(500, default_val)))
            layout.addRow("Factor (%):", self.factor_spinbox)
        
        elif self.filter_name == "Brightness":
            self.factor_spinbox = QSpinBox()
            self.factor_spinbox.setMinimum(0)
            self.factor_spinbox.setMaximum(300)
            default_val = int(self._get_initial("factor", 1.0) * 100)
            self.factor_spinbox.setValue(max(0, min(300, default_val)))
            layout.addRow("Brightness (%):", self.factor_spinbox)
        
        elif self.filter_name == "Contrast":
            self.factor_spinbox = QSpinBox()
            self.factor_spinbox.setMinimum(0)
            self.factor_spinbox.setMaximum(300)
            default_val = int(self._get_initial("factor", 1.0) * 100)
            self.factor_spinbox.setValue(max(0, min(300, default_val)))
            layout.addRow("Contrast (%):", self.factor_spinbox)
        
        elif self.filter_name == "Hue/Saturation":
            self.hue_spinbox = QSpinBox()
            self.hue_spinbox.setMinimum(-180)
            self.hue_spinbox.setMaximum(180)
            self.hue_spinbox.setValue(self._get_initial("hue_shift", 0))
            layout.addRow("Hue Shift:", self.hue_spinbox)
            
            self.saturation_spinbox = QSpinBox()
            self.saturation_spinbox.setMinimum(0)
            self.saturation_spinbox.setMaximum(300)
            default_sat = int(self._get_initial("saturation", 1.0) * 100)
            self.saturation_spinbox.setValue(max(0, min(300, default_sat)))
            layout.addRow("Saturation (%):", self.saturation_spinbox)
        
        elif self.filter_name == "Posterize":
            self.bits_spinbox = QSpinBox()
            self.bits_spinbox.setMinimum(2)
            self.bits_spinbox.setMaximum(8)
            self.bits_spinbox.setValue(self._get_initial("bits", 4))
            layout.addRow("Bits per channel (2-8):", self.bits_spinbox)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def get_parameters(self) -> dict:
        """Get filter parameters.
        
        Returns:
            Dictionary of parameters
        """
        params = {}
        
        if self.filter_name == "Blur":
            params['radius'] = self.radius_spinbox.value()
        elif self.filter_name == "Sharpen":
            params['factor'] = self.factor_spinbox.value() / 100.0
        elif self.filter_name == "Brightness":
            params['factor'] = self.factor_spinbox.value() / 100.0
        elif self.filter_name == "Contrast":
            params['factor'] = self.factor_spinbox.value() / 100.0
        elif self.filter_name == "Hue/Saturation":
            params['hue_shift'] = self.hue_spinbox.value()
            params['saturation'] = self.saturation_spinbox.value() / 100.0
        elif self.filter_name == "Posterize":
            params['bits'] = self.bits_spinbox.value()
        
        return params


class MainWindow(QMainWindow):
    """Main application window.
    
    The main window integrates:
    - Menu bar with File, Edit, Layer, Filter, View menus
    - Tool bar with common actions
    - Canvas for viewing and editing
    - Layer panel for layer management
    - Tool options panel for tool settings
    """
    
    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        
        # Create project
        self.project = Project(800, 600)
        
        # Create command history
        self.command_history = CommandHistory()
        
        # Unsaved changes flag
        self.modified = False
        self._cursor_x = -1
        self._cursor_y = -1
        
        # Last-used filter parameters (so dialog reopens with same values)
        self.last_filter_params = {}
        
        # Settings
        self.settings = QSettings("ImageEditorPro", "ImageEditorPro")
        
        # Set up UI
        self.setup_ui()
        self.setup_menus()
        self.setup_toolbar()
        self.setup_dock_widgets()
        self.setup_status_bar()
        self.connect_signals()
        
        # Apply modern dark theme (load from styles.qss if present)
        self._apply_app_stylesheet()
        
        # Set window properties
        self.setWindowTitle("Image Editor Pro")
        self.resize(1200, 800)
        
        # Restore settings
        self.restore_settings()
    
    def _apply_app_stylesheet(self):
        """Load and apply global QSS from styles.qss (modern dark theme)."""
        # styles.qss lives next to main_window.py (in src/)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        qss_path = os.path.join(base_dir, "styles.qss")
        if os.path.isfile(qss_path):
            try:
                with open(qss_path, "r", encoding="utf-8") as f:
                    self.setStyleSheet(f.read())
            except Exception:
                pass
    
    def setup_ui(self):
        """Set up the main user interface."""
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create canvas
        self.canvas = Canvas(self.project)
        self.canvas_scroll = CanvasScrollArea(self.canvas)
        
        # Layout
        layout = QVBoxLayout(central_widget)
        layout.addWidget(self.canvas_scroll)
        layout.setContentsMargins(0, 0, 0, 0)
    
    def setup_menus(self):
        """Set up menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        new_action = QAction("&New", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)
        
        open_action = QAction("&Open Image...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_image)
        file_menu.addAction(open_action)
        
        open_project_action = QAction("Open &Project...", self)
        open_project_action.setShortcut(QKeySequence("Ctrl+Shift+O"))
        open_project_action.triggered.connect(self.open_project)
        file_menu.addAction(open_project_action)
        
        self.recent_menu = file_menu.addMenu("Open Rece&nt")
        self.recent_files = []
        self._load_recent_files()
        self._update_recent_files_menu()
        
        file_menu.addSeparator()
        
        save_action = QAction("&Save Image...", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_image)
        file_menu.addAction(save_action)
        
        save_project_action = QAction("Save P&roject...", self)
        save_project_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_project_action.triggered.connect(self.save_project)
        file_menu.addAction(save_project_action)
        
        save_as_action = QAction("Save Project &As...", self)
        save_as_action.triggered.connect(self.save_project_as)
        file_menu.addAction(save_as_action)
        
        export_as_action = QAction("Export &As...", self)
        export_as_action.setToolTip("Export composite image to a new file (PNG/JPEG)")
        export_as_action.triggered.connect(self.export_image_as)
        file_menu.addAction(export_as_action)
        
        file_menu.addSeparator()
        
        self.revert_action = QAction("Re&vert", self)
        self.revert_action.setToolTip("Revert to last saved version (reload from file)")
        self.revert_action.triggered.connect(self.revert_project)
        self.revert_action.setEnabled(False)
        file_menu.addAction(self.revert_action)
        
        file_menu.addSeparator()
        
        quit_action = QAction("&Quit", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        
        self.undo_action = QAction("&Undo", self)
        self.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self.undo_action.triggered.connect(self.command_history.undo)
        self.undo_action.setEnabled(False)
        edit_menu.addAction(self.undo_action)
        
        self.redo_action = QAction("&Redo", self)
        self.redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        self.redo_action.triggered.connect(self.command_history.redo)
        self.redo_action.setEnabled(False)
        edit_menu.addAction(self.redo_action)
        
        edit_menu.addSeparator()
        
        clear_layer_action = QAction("Clea&r Layer", self)
        clear_layer_action.setToolTip("Fill the current layer with transparent (undoable)")
        clear_layer_action.triggered.connect(self.clear_layer)
        edit_menu.addAction(clear_layer_action)
        
        fill_action = QAction("&Fill...", self)
        fill_action.setToolTip("Fill the current layer with a color (and opacity)")
        fill_action.triggered.connect(self.fill_layer)
        edit_menu.addAction(fill_action)
        
        edit_menu.addSeparator()
        
        copy_merged_action = QAction("Copy &Merged", self)
        copy_merged_action.setShortcut(QKeySequence("Ctrl+Shift+C"))
        copy_merged_action.setToolTip("Copy the visible result of all layers to clipboard")
        copy_merged_action.triggered.connect(self.copy_merged)
        edit_menu.addAction(copy_merged_action)
        
        paste_layer_action = QAction("Paste as &New Layer", self)
        paste_layer_action.setShortcut(QKeySequence("Ctrl+Shift+V"))
        paste_layer_action.setToolTip("Paste clipboard image as a new layer")
        paste_layer_action.triggered.connect(self.paste_as_new_layer)
        edit_menu.addAction(paste_layer_action)
        
        edit_menu.addSeparator()
        prefs_action = QAction("P&references...", self)
        prefs_action.triggered.connect(self.show_preferences)
        edit_menu.addAction(prefs_action)
        
        # Layer menu
        layer_menu = menubar.addMenu("&Layer")
        
        add_layer_action = QAction("&New Layer", self)
        add_layer_action.setShortcut(QKeySequence("Ctrl+Shift+N"))
        add_layer_action.triggered.connect(self.add_layer)
        layer_menu.addAction(add_layer_action)
        
        add_image_action = QAction("Add Image from &File...", self)
        add_image_action.setToolTip("Import an image file as a new layer")
        add_image_action.triggered.connect(self.add_image_from_file)
        layer_menu.addAction(add_image_action)
        
        duplicate_layer_action = QAction("&Duplicate Layer", self)
        duplicate_layer_action.setShortcut(QKeySequence("Ctrl+J"))
        duplicate_layer_action.triggered.connect(self.duplicate_layer)
        layer_menu.addAction(duplicate_layer_action)
        
        merge_down_action = QAction("&Merge Down", self)
        merge_down_action.setShortcut(QKeySequence("Ctrl+E"))
        merge_down_action.triggered.connect(self.merge_down)
        layer_menu.addAction(merge_down_action)
        
        resize_layer_action = QAction("Resize &Layer...", self)
        resize_layer_action.setToolTip("Scale the current layer to a new size (centered on canvas)")
        resize_layer_action.triggered.connect(self.resize_layer)
        layer_menu.addAction(resize_layer_action)
        
        layer_menu.addSeparator()
        
        self.remove_last_filter_layer_action = QAction("Remove last filter from layer", self)
        self.remove_last_filter_layer_action.setToolTip(
            "Revert only the last filter on this layer (without undoing drawing or other edits). "
            "Use repeatedly to step back through filters on this layer."
        )
        self.remove_last_filter_layer_action.triggered.connect(self.remove_last_filter_from_layer)
        self.remove_last_filter_layer_action.setEnabled(False)
        layer_menu.addAction(self.remove_last_filter_layer_action)
        
        layer_menu.addSeparator()
        
        flatten_action = QAction("Flatten &Image", self)
        flatten_action.setToolTip("Merge all layers into one (undoable)")
        flatten_action.triggered.connect(self.flatten_image)
        layer_menu.addAction(flatten_action)
        
        layer_menu.addSeparator()
        add_text_action = QAction("Add &Text...", self)
        add_text_action.setToolTip("Draw text on the current layer at the top-left")
        add_text_action.triggered.connect(self.add_text_to_layer)
        layer_menu.addAction(add_text_action)
        
        # Filter menu
        filter_menu = menubar.addMenu("F&ilter")
        
        self.undo_last_filter_action = QAction("Undo last filter", self)
        self.undo_last_filter_action.setToolTip(
            "Revert the last change (e.g. undo Blur, Brightness, etc.). Same as Edit > Undo (Ctrl+Z)."
        )
        self.undo_last_filter_action.triggered.connect(self.command_history.undo)
        self.undo_last_filter_action.setEnabled(False)
        filter_menu.addAction(self.undo_last_filter_action)
        
        self.redo_last_filter_action = QAction("Redo last filter", self)
        self.redo_last_filter_action.setToolTip("Re-apply the last undone change. Same as Edit > Redo (Ctrl+Y).")
        self.redo_last_filter_action.triggered.connect(self.command_history.redo)
        self.redo_last_filter_action.setEnabled(False)
        filter_menu.addAction(self.redo_last_filter_action)
        
        self.remove_last_filter_filter_action = QAction("Remove last filter from layer", self)
        self.remove_last_filter_filter_action.setToolTip(
            "Revert only the last filter on the current layer. Use repeatedly to remove earlier filters."
        )
        self.remove_last_filter_filter_action.triggered.connect(self.remove_last_filter_from_layer)
        self.remove_last_filter_filter_action.setEnabled(False)
        filter_menu.addAction(self.remove_last_filter_filter_action)
        
        filter_menu.addSeparator()
        
        blur_action = QAction("&Blur", self)
        blur_action.triggered.connect(lambda: self.apply_filter("Blur"))
        filter_menu.addAction(blur_action)
        
        sharpen_action = QAction("&Sharpen", self)
        sharpen_action.triggered.connect(lambda: self.apply_filter("Sharpen"))
        filter_menu.addAction(sharpen_action)
        
        filter_menu.addSeparator()
        
        brightness_action = QAction("Bright&ness", self)
        brightness_action.triggered.connect(lambda: self.apply_filter("Brightness"))
        filter_menu.addAction(brightness_action)
        
        contrast_action = QAction("&Contrast", self)
        contrast_action.triggered.connect(lambda: self.apply_filter("Contrast"))
        filter_menu.addAction(contrast_action)
        
        hue_sat_action = QAction("&Hue/Saturation", self)
        hue_sat_action.triggered.connect(lambda: self.apply_filter("Hue/Saturation"))
        filter_menu.addAction(hue_sat_action)
        
        filter_menu.addSeparator()
        
        grayscale_action = QAction("&Grayscale", self)
        grayscale_action.triggered.connect(lambda: self.apply_filter("Grayscale"))
        filter_menu.addAction(grayscale_action)
        
        invert_action = QAction("&Invert", self)
        invert_action.triggered.connect(lambda: self.apply_filter("Invert"))
        filter_menu.addAction(invert_action)
        
        edge_detect_action = QAction("&Edge Detect", self)
        edge_detect_action.triggered.connect(lambda: self.apply_filter("Edge Detect"))
        filter_menu.addAction(edge_detect_action)
        
        sepia_action = QAction("Se&pia", self)
        sepia_action.triggered.connect(lambda: self.apply_filter("Sepia"))
        filter_menu.addAction(sepia_action)
        
        posterize_action = QAction("&Posterize...", self)
        posterize_action.triggered.connect(lambda: self.apply_filter("Posterize"))
        filter_menu.addAction(posterize_action)
        
        desaturate_action = QAction("&Desaturate", self)
        desaturate_action.setToolTip("Remove color (grayscale) from current layer")
        desaturate_action.triggered.connect(lambda: self.apply_filter("Desaturate"))
        filter_menu.addAction(desaturate_action)
        
        emboss_action = QAction("Em&boss", self)
        emboss_action.triggered.connect(lambda: self.apply_filter("Emboss"))
        filter_menu.addAction(emboss_action)
        
        smooth_action = QAction("S&mooth", self)
        smooth_action.setToolTip("Soften/smooth the current layer")
        smooth_action.triggered.connect(lambda: self.apply_filter("Smooth"))
        filter_menu.addAction(smooth_action)
        
        detail_action = QAction("&Detail", self)
        detail_action.setToolTip("Enhance fine details on the current layer")
        detail_action.triggered.connect(lambda: self.apply_filter("Detail"))
        filter_menu.addAction(detail_action)
        
        # Image menu (transform, resize)
        image_menu = menubar.addMenu("&Image")
        
        flip_h_action = QAction("Flip &Horizontal", self)
        flip_h_action.triggered.connect(lambda: self.transform_layer("Flip Horizontal"))
        image_menu.addAction(flip_h_action)
        
        flip_v_action = QAction("Flip &Vertical", self)
        flip_v_action.triggered.connect(lambda: self.transform_layer("Flip Vertical"))
        image_menu.addAction(flip_v_action)
        
        image_menu.addSeparator()
        
        rotate_cw_action = QAction("Rotate 90° &CW", self)
        rotate_cw_action.triggered.connect(lambda: self.transform_layer("Rotate 90 CW"))
        image_menu.addAction(rotate_cw_action)
        
        rotate_ccw_action = QAction("Rotate 90° C&CW", self)
        rotate_ccw_action.triggered.connect(lambda: self.transform_layer("Rotate 90 CCW"))
        image_menu.addAction(rotate_ccw_action)
        
        rotate_180_action = QAction("Rotate 180°", self)
        rotate_180_action.triggered.connect(lambda: self.transform_layer("Rotate 180"))
        image_menu.addAction(rotate_180_action)
        
        rotate_arb_action = QAction("Rotate &Arbitrary...", self)
        rotate_arb_action.setToolTip("Rotate current layer by any angle (degrees)")
        rotate_arb_action.triggered.connect(self.rotate_layer_arbitrary)
        image_menu.addAction(rotate_arb_action)
        
        image_menu.addSeparator()
        
        resize_image_action = QAction("&Resize Image...", self)
        resize_image_action.setToolTip("Resize the canvas and all layers")
        resize_image_action.triggered.connect(self.resize_image)
        image_menu.addAction(resize_image_action)
        
        canvas_size_action = QAction("&Canvas Size...", self)
        canvas_size_action.setToolTip("Expand or shrink canvas (image size stays same, position by anchor)")
        canvas_size_action.triggered.connect(self.canvas_size)
        image_menu.addAction(canvas_size_action)
        
        crop_action = QAction("&Crop...", self)
        crop_action.setToolTip("Crop the canvas and all layers to a rectangle")
        crop_action.triggered.connect(self.crop_image)
        image_menu.addAction(crop_action)
        
        image_menu.addSeparator()
        
        make_transparent_action = QAction("Make color transparent...", self)
        make_transparent_action.setToolTip("Make pixels matching a color transparent (e.g. remove white background)")
        make_transparent_action.triggered.connect(self.make_color_transparent)
        image_menu.addAction(make_transparent_action)
        
        trim_action = QAction("Tri&m...", self)
        trim_action.setToolTip("Trim canvas to content (transparent or top-left color)")
        trim_action.triggered.connect(self.trim_image)
        image_menu.addAction(trim_action)
        
        image_menu.addSeparator()
        mode_menu = image_menu.addMenu("&Mode")
        grayscale_mode_action = QAction("&Grayscale (current layer)", self)
        grayscale_mode_action.setToolTip("Convert current layer to grayscale")
        grayscale_mode_action.triggered.connect(lambda: self.apply_filter("Grayscale"))
        mode_menu.addAction(grayscale_mode_action)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        zoom_in_action = QAction("Zoom &In", self)
        zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zoom_in_action.triggered.connect(self.zoom_in_slot)
        view_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction("Zoom &Out", self)
        zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
        zoom_out_action.triggered.connect(self.zoom_out_slot)
        view_menu.addAction(zoom_out_action)
        
        zoom_reset_action = QAction("&Reset Zoom", self)
        zoom_reset_action.setShortcut(QKeySequence("Ctrl+0"))
        zoom_reset_action.triggered.connect(self.zoom_reset_slot)
        view_menu.addAction(zoom_reset_action)
        
        zoom_fit_action = QAction("&Fit to Window", self)
        zoom_fit_action.setShortcut(QKeySequence("Ctrl+1"))
        zoom_fit_action.setToolTip("Zoom so the entire image fits in the window")
        zoom_fit_action.triggered.connect(self.zoom_fit_slot)
        view_menu.addAction(zoom_fit_action)
        
        zoom_actual_action = QAction("Actual Si&ze (100%)", self)
        zoom_actual_action.setShortcut(QKeySequence("Ctrl+2"))
        zoom_actual_action.setToolTip("Zoom to 100% (one image pixel per screen pixel)")
        zoom_actual_action.triggered.connect(self.zoom_reset_slot)
        view_menu.addAction(zoom_actual_action)
        
        view_menu.addSeparator()
        panels_menu = view_menu.addMenu("P&anels")
        self.view_layers_action = QAction("Layers", self)
        self.view_layers_action.setCheckable(True)
        self.view_layers_action.setChecked(True)
        self.view_layers_action.triggered.connect(lambda: self.layer_dock.setVisible(self.view_layers_action.isChecked()))
        panels_menu.addAction(self.view_layers_action)
        self.view_tools_action = QAction("Tools", self)
        self.view_tools_action.setCheckable(True)
        self.view_tools_action.setChecked(True)
        self.view_tools_action.triggered.connect(lambda: self.tool_dock.setVisible(self.view_tools_action.isChecked()))
        panels_menu.addAction(self.view_tools_action)
        self.view_history_action = QAction("History", self)
        self.view_history_action.setCheckable(True)
        self.view_history_action.setChecked(True)
        self.view_history_action.triggered.connect(lambda: self.history_dock.setVisible(self.view_history_action.isChecked()))
        panels_menu.addAction(self.view_history_action)
        
        view_menu.addSeparator()
        
        transparency_menu = view_menu.addMenu("Transparency display")
        trans_checker = QAction("Checkerboard", self)
        trans_checker.setCheckable(True)
        trans_checker.setChecked(True)
        trans_checker.triggered.connect(lambda: self.set_transparency_display("checkerboard"))
        transparency_menu.addAction(trans_checker)
        trans_white = QAction("White", self)
        trans_white.setCheckable(True)
        trans_white.triggered.connect(lambda: self.set_transparency_display("white"))
        transparency_menu.addAction(trans_white)
        trans_gray = QAction("Gray", self)
        trans_gray.setCheckable(True)
        trans_gray.triggered.connect(lambda: self.set_transparency_display("gray"))
        transparency_menu.addAction(trans_gray)
        trans_black = QAction("Black", self)
        trans_black.setCheckable(True)
        trans_black.triggered.connect(lambda: self.set_transparency_display("black"))
        transparency_menu.addAction(trans_black)
        self.transparency_actions = [trans_checker, trans_white, trans_gray, trans_black]
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        shortcuts_action = QAction("&Keyboard Shortcuts", self)
        shortcuts_action.triggered.connect(self.show_keyboard_shortcuts)
        help_menu.addAction(shortcuts_action)
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def setup_toolbar(self):
        """Set up toolbar (icons with tooltips for compact layout)."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setObjectName("MainToolbar")
        toolbar.setMovable(True)
        toolbar.setFloatable(True)
        toolbar.setMaximumHeight(48)
        self.addToolBar(toolbar)
        style = self.style()
        
        new_btn = QAction(self)
        new_btn.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        new_btn.setToolTip("New (Ctrl+N)\nCreate a new image project.")
        new_btn.triggered.connect(self.new_project)
        toolbar.addAction(new_btn)
        
        open_btn = QAction(self)
        open_btn.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton))
        open_btn.setToolTip("Open Image (Ctrl+O)\nOpen an image file as a new project.")
        open_btn.triggered.connect(self.open_image)
        toolbar.addAction(open_btn)
        
        save_btn = QAction(self)
        save_btn.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        save_btn.setToolTip("Save Image (Ctrl+S)\nExport the composite image to a file.")
        save_btn.triggered.connect(self.save_image)
        toolbar.addAction(save_btn)
        
        toolbar.addSeparator()
        
        undo_btn = QAction(self)
        undo_btn.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_ArrowBack))
        undo_btn.setToolTip("Undo (Ctrl+Z)\nRevert the last action.")
        undo_btn.triggered.connect(self.command_history.undo)
        toolbar.addAction(undo_btn)
        
        redo_btn = QAction(self)
        redo_btn.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_ArrowForward))
        redo_btn.setToolTip("Redo (Ctrl+Y)\nRedo the last undone action.")
        redo_btn.triggered.connect(self.command_history.redo)
        toolbar.addAction(redo_btn)
    
    def setup_dock_widgets(self):
        """Set up dock widgets."""
        # Layer panel
        self.layer_panel = LayerPanel(self.project)
        self.layer_dock = QDockWidget("Layers", self)
        self.layer_dock.setObjectName("LayersDock")
        self.layer_dock.setWidget(self.layer_panel)
        self.layer_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.layer_dock.setMaximumWidth(500)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.layer_dock)
        
        # Tool options panel
        self.tool_panel = ToolOptionsPanel()
        self.tool_dock = QDockWidget("Tools", self)
        self.tool_dock.setObjectName("ToolsDock")
        self.tool_dock.setWidget(self.tool_panel)
        self.tool_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.tool_dock.setMaximumWidth(500)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.tool_dock)
        
        # History panel
        self.history_panel = HistoryPanel(self.command_history)
        self.history_dock = QDockWidget("History", self)
        self.history_dock.setObjectName("HistoryDock")
        self.history_dock.setWidget(self.history_panel)
        self.history_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.history_dock)
    
    def setup_status_bar(self):
        """Set up status bar with zoom and cursor position."""
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("")
        self.status_bar.addPermanentWidget(self.status_label)
        self.update_status_bar()
    
    def update_status_bar(self):
        """Update status bar text (zoom, cursor, dimensions)."""
        zoom_pct = int(self.canvas.zoom_level * 100)
        w, h = self.project.width, self.project.height
        if hasattr(self, "_cursor_x") and self._cursor_x >= 0:
            self.status_label.setText(f"Zoom: {zoom_pct}%  |  {w} x {h}  |  Cursor: {self._cursor_x}, {self._cursor_y}")
        else:
            self.status_label.setText(f"Zoom: {zoom_pct}%  |  {w} x {h}")
    
    def zoom_in_slot(self):
        self.canvas_scroll.zoom_in()
        self.update_status_bar()
    
    def zoom_out_slot(self):
        self.canvas_scroll.zoom_out()
        self.update_status_bar()
    
    def zoom_reset_slot(self):
        self.canvas_scroll.zoom_reset()
        self.update_status_bar()
    
    def zoom_fit_slot(self):
        self.canvas_scroll.zoom_fit_to_window()
        self.update_status_bar()
    
    def set_transparency_display(self, mode: str):
        """Set canvas transparency background and update View menu check state."""
        self.canvas.set_transparency_display(mode)
        modes = ["checkerboard", "white", "gray", "black"]
        for i, action in enumerate(self.transparency_actions):
            action.setChecked(mode == modes[i])
    
    def connect_signals(self):
        """Connect signals and slots."""
        # Layer panel signals
        self.layer_panel.layer_selected.connect(self.canvas.set_active_layer_index)
        self.layer_panel.layer_selected.connect(self.update_remove_last_filter_actions)
        self.layer_panel.add_layer_requested.connect(self.add_layer)
        self.layer_panel.remove_layer_requested.connect(self.remove_layer)
        self.layer_panel.move_layer_up_requested.connect(self.move_layer_up)
        self.layer_panel.move_layer_down_requested.connect(self.move_layer_down)
        self.layer_panel.opacity_changed.connect(self.set_layer_opacity)
        self.layer_panel.visibility_toggled.connect(self.toggle_layer_visibility)
        self.layer_panel.layer_rename_requested.connect(self.rename_layer)
        
        # Tool panel signals
        self.tool_panel.brush_size_changed.connect(self.canvas.set_brush_size)
        self.tool_panel.brush_opacity_changed.connect(self.canvas.set_brush_opacity)
        self.tool_panel.color_changed.connect(self.canvas.set_brush_color)
        self.tool_panel.tool_changed.connect(self.canvas.set_tool)
        self.tool_panel.paint_bucket_tolerance_changed.connect(self.canvas.set_paint_bucket_tolerance)
        self.tool_panel.shape_kind_changed.connect(self.canvas.set_shape_kind)
        self.tool_panel.shape_style_changed.connect(self.canvas.set_shape_style)
        self.tool_panel.shape_outline_width_changed.connect(self.canvas.set_shape_outline_width)
        self.tool_panel.eraser_color_changed.connect(self.canvas.set_eraser_color)
        
        # Canvas signals
        self.canvas.drawing_completed.connect(self.on_drawing_completed)
        self.canvas.cursor_position_changed.connect(self.on_cursor_position_changed)
        self.canvas.color_sampled.connect(self.tool_panel.set_color)
        self.canvas_scroll.zoom_changed.connect(self.update_status_bar)
        self.canvas.zoom_requested.connect(self.canvas_scroll.zoom_at_canvas_point)
        self.canvas.crop_requested.connect(self.on_crop_requested)

        # Command history signals
        self.command_history.history_changed.connect(self.update_undo_redo_actions)
        
        # Tool shortcuts (B, E, I, G, R, Z, C)
        self._tool_shortcuts = [
            QShortcut(QKeySequence("B"), self, lambda: self.tool_panel.select_tool("brush")),
            QShortcut(QKeySequence("E"), self, lambda: self.tool_panel.select_tool("eraser")),
            QShortcut(QKeySequence("T"), self, lambda: self.tool_panel.select_tool("transparency")),
            QShortcut(QKeySequence("I"), self, lambda: self.tool_panel.select_tool("eyedropper")),
            QShortcut(QKeySequence("G"), self, lambda: self.tool_panel.select_tool("paint_bucket")),
            QShortcut(QKeySequence("R"), self, lambda: self.tool_panel.select_tool("shape")),
            QShortcut(QKeySequence("Z"), self, lambda: self.tool_panel.select_tool("zoom")),
            QShortcut(QKeySequence("C"), self, lambda: self.tool_panel.select_tool("crop")),
        ]
        QShortcut(QKeySequence(QKeySequence.StandardKey.Cancel), self, self._cancel_crop_if_active)
        # Palette shortcuts: Alt+1–9, Alt+0 (slot 10), Ctrl+Alt+1 (slot 11), Ctrl+Alt+2 (slot 12)
        self._palette_shortcuts = []
        for i in range(10):
            key = str(i + 1) if i < 9 else "0"
            self._palette_shortcuts.append(
                QShortcut(QKeySequence("Alt+" + key), self, lambda idx=i: self.tool_panel.set_brush_from_palette_index(idx))
            )
        self._palette_shortcuts.append(
            QShortcut(QKeySequence("Ctrl+Alt+1"), self, lambda: self.tool_panel.set_brush_from_palette_index(10))
        )
        self._palette_shortcuts.append(
            QShortcut(QKeySequence("Ctrl+Alt+2"), self, lambda: self.tool_panel.set_brush_from_palette_index(11))
        )
        
        # Apply default brush size from preferences
        default_brush = int(self.settings.value("default_brush_size", 10))
        if 1 <= default_brush <= 200:
            self.tool_panel.size_slider.setValue(default_brush)
            self.tool_panel.size_spinbox.setValue(default_brush)
            self.canvas.set_brush_size(default_brush)
        
        # Keep View > Panels in sync when docks are closed by user
        self.layer_dock.visibilityChanged.connect(self.view_layers_action.setChecked)
        self.tool_dock.visibilityChanged.connect(self.view_tools_action.setChecked)
        self.history_dock.visibilityChanged.connect(self.view_history_action.setChecked)
        
        # Initial active layer and "Remove last filter" state
        self.canvas.set_active_layer_index(self.layer_panel.current_layer_index)
        self.update_remove_last_filter_actions()
    
    def on_cursor_position_changed(self, x: int, y: int):
        """Update status bar with cursor position."""
        self._cursor_x = x
        self._cursor_y = y
        self.update_status_bar()
    
    def rename_layer(self, layer_index: int, new_name: str):
        """Rename a layer by index."""
        layer = self.project.get_layer(layer_index)
        if layer:
            layer.name = new_name
            self.project.layer_modified.emit(layer_index)
            self.layer_panel.refresh_layers()
            row = len(self.project.layers) - 1 - layer_index
            self.layer_panel.layer_list.setCurrentRow(row)
            self.modified = True
    
    def prompt_save_unsaved(self) -> bool:
        """If modified, prompt to save. Returns True to continue, False to cancel."""
        if not self.modified:
            return True
        reply = QMessageBox.question(
            self,
            "Unsaved Changes",
            "Save changes before continuing?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save
        )
        if reply == QMessageBox.StandardButton.Cancel:
            return False
        if reply == QMessageBox.StandardButton.Save:
            if self.project.file_path:
                try:
                    self.project.save_project(self.project.file_path)
                    self.modified = False
                    return True
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to save: {e}")
                    return False
            # No file path: show save dialog
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Project", "", "Image Editor Pro Project (*.iep);;All Files (*)"
            )
            if not file_path:
                return False
            if not file_path.endswith('.iep'):
                file_path += '.iep'
            try:
                self.project.save_project(file_path)
                self.modified = False
                self.setWindowTitle(f"Image Editor Pro - {os.path.basename(file_path)}")
                return True
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save: {e}")
                return False
        return True  # Discard
    
    # File operations
    
    def new_project(self):
        """Create a new project."""
        if not self.prompt_save_unsaved():
            return
        
        default_w = int(self.settings.value("default_new_width", 800))
        default_h = int(self.settings.value("default_new_height", 600))
        default_bg = self.settings.value("default_background", "White")
        bg_index = 0 if default_bg == "White" else 1
        
        # Single dialog for canvas size and background
        dialog = QDialog(self)
        dialog.setWindowTitle("New image")
        form = QFormLayout(dialog)
        w_spin = QSpinBox()
        w_spin.setRange(1, 10000)
        w_spin.setValue(default_w)
        w_spin.setSuffix(" px")
        form.addRow("Canvas width:", w_spin)
        h_spin = QSpinBox()
        h_spin.setRange(1, 10000)
        h_spin.setValue(default_h)
        h_spin.setSuffix(" px")
        form.addRow("Canvas height:", h_spin)
        bg_combo = QComboBox()
        bg_combo.addItems(["White", "Transparent"])
        bg_combo.setCurrentIndex(bg_index)
        form.addRow("Background:", bg_combo)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        width = w_spin.value()
        height = h_spin.value()
        initial_white = bg_combo.currentText() == "White"
        
        # Create new project
        self.project = Project(width, height, initial_background_white=initial_white)
        self.canvas.project = self.project
        self.layer_panel.project = self.project
        
        # Clear history
        self.command_history.clear()
        
        # Reconnect signals
        self.project.layers_changed.connect(self.canvas.on_project_changed)
        self.project.layer_modified.connect(self.canvas.on_project_changed)
        self.project.layers_changed.connect(self.layer_panel.refresh_layers)
        self.project.layer_modified.connect(self.layer_panel.on_layer_modified)
        
        # Update UI
        self.canvas.update_size()
        self.layer_panel.refresh_layers()
        self.setWindowTitle("Image Editor Pro - Untitled")
        self.modified = False
    
    def open_image(self):
        """Open an image file."""
        if not self.prompt_save_unsaved():
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)"
        )
        if file_path:
            self._open_image_path(file_path)
    
    def save_image(self):
        """Save the rendered image."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Image",
            "",
            "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg);;All Files (*)"
        )
        
        if file_path:
            try:
                rendered = self.project.render()
                if file_path.lower().endswith(('.jpg', '.jpeg')):
                    rendered = rendered.convert('RGB')
                rendered.save(file_path)
                self.modified = False
                self.update_revert_action()
                QMessageBox.information(self, "Success", "Image saved successfully!")
            except PermissionError:
                QMessageBox.critical(
                    self, "Error",
                    "Permission denied. The file may be open elsewhere or the folder is read-only."
                )
            except OSError as e:
                QMessageBox.critical(self, "Error", f"Cannot save image: {str(e)}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save image: {str(e)}")
    
    def open_project(self):
        """Open a project file."""
        if not self.prompt_save_unsaved():
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Project",
            "",
            "Image Editor Pro Project (*.iep);;All Files (*)"
        )
        if file_path:
            self._open_project_path(file_path)
    
    def save_project(self):
        """Save the project (to current path if set, else show dialog)."""
        file_path = getattr(self.project, "file_path", None)
        if not file_path:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Project",
                "",
                "Image Editor Pro Project (*.iep);;All Files (*)"
            )
        if file_path:
            try:
                if not file_path.endswith('.iep'):
                    file_path += '.iep'
                self.project.save_project(file_path)
                self.modified = False
                self.update_revert_action()
                QMessageBox.information(self, "Success", "Project saved successfully!")
                self.setWindowTitle(f"Image Editor Pro - {os.path.basename(file_path)}")
            except PermissionError:
                QMessageBox.critical(
                    self, "Error",
                    "Permission denied. The file or folder may be read-only or in use."
                )
            except OSError as e:
                QMessageBox.critical(self, "Error", f"Cannot save project: {str(e)}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save project: {str(e)}")
    
    def save_project_as(self):
        """Save the project to a new path (always show dialog)."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Project As",
            getattr(self.project, "file_path", "") or "",
            "Image Editor Pro Project (*.iep);;All Files (*)"
        )
        if file_path:
            try:
                if not file_path.endswith('.iep'):
                    file_path += '.iep'
                self.project.save_project(file_path)
                self.modified = False
                self.update_revert_action()
                QMessageBox.information(self, "Success", "Project saved successfully!")
                self.setWindowTitle(f"Image Editor Pro - {os.path.basename(file_path)}")
            except PermissionError:
                QMessageBox.critical(
                    self, "Error",
                    "Permission denied. The file or folder may be read-only or in use."
                )
            except OSError as e:
                QMessageBox.critical(self, "Error", f"Cannot save project: {str(e)}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save project: {str(e)}")
    
    def export_image_as(self):
        """Export the composite image to a new file (always show dialog)."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export As",
            "",
            "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg);;All Files (*)"
        )
        if file_path:
            try:
                rendered = self.project.render()
                if file_path.lower().endswith(('.jpg', '.jpeg')):
                    rendered = rendered.convert('RGB')
                rendered.save(file_path)
                QMessageBox.information(self, "Success", "Image exported successfully!")
            except PermissionError:
                QMessageBox.critical(self, "Error", "Permission denied. Cannot write to that location.")
            except OSError as e:
                QMessageBox.critical(self, "Error", f"Cannot export: {str(e)}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export: {str(e)}")
    
    RECENT_MAX = 8
    RECENT_KEY = "recent_files"
    
    def _load_recent_files(self):
        """Load recent file list from settings."""
        self.recent_files = self.settings.value(self.RECENT_KEY, [], type=list)
        if not isinstance(self.recent_files, list):
            self.recent_files = []
    
    def _update_recent_files_menu(self):
        """Rebuild the Open Recent submenu from self.recent_files."""
        self.recent_menu.clear()
        for path in self.recent_files:
            if path and isinstance(path, str) and os.path.isfile(path):
                name = os.path.basename(path)
                action = QAction(name, self)
                action.setData(path)
                action.triggered.connect(lambda checked=False, p=path: self._open_recent(p))
                self.recent_menu.addAction(action)
        if not self.recent_menu.actions():
            none_action = QAction("(No recent files)", self)
            none_action.setEnabled(False)
            self.recent_menu.addAction(none_action)
        else:
            self.recent_menu.addSeparator()
            clear_recent_action = QAction("Clear &list", self)
            clear_recent_action.triggered.connect(self._clear_recent_list)
            self.recent_menu.addAction(clear_recent_action)
    
    def _clear_recent_list(self):
        """Clear the recent files list and refresh menu."""
        self.recent_files = []
        self.settings.setValue(self.RECENT_KEY, self.recent_files)
        self._update_recent_files_menu()
    
    def show_preferences(self):
        """Show preferences dialog and save defaults."""
        d = QDialog(self)
        d.setWindowTitle("Preferences")
        layout = QFormLayout(d)
        w_spin = QSpinBox()
        w_spin.setRange(1, 10000)
        w_spin.setValue(int(self.settings.value("default_new_width", 800)))
        layout.addRow("Default new image width:", w_spin)
        h_spin = QSpinBox()
        h_spin.setRange(1, 10000)
        h_spin.setValue(int(self.settings.value("default_new_height", 600)))
        layout.addRow("Default new image height:", h_spin)
        brush_spin = QSpinBox()
        brush_spin.setRange(1, 200)
        brush_spin.setValue(int(self.settings.value("default_brush_size", 10)))
        layout.addRow("Default brush size:", brush_spin)
        bg_combo = QComboBox()
        bg_combo.addItems(["White", "Transparent"])
        bg_combo.setCurrentText(self.settings.value("default_background", "White"))
        layout.addRow("Default background:", bg_combo)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(d.accept)
        buttons.rejected.connect(d.reject)
        layout.addRow(buttons)
        if d.exec() == QDialog.DialogCode.Accepted:
            self.settings.setValue("default_new_width", w_spin.value())
            self.settings.setValue("default_new_height", h_spin.value())
            self.settings.setValue("default_brush_size", brush_spin.value())
            self.settings.setValue("default_background", bg_combo.currentText())
    
    def _add_to_recent(self, file_path: str):
        """Add a path to recent files and persist."""
        if not file_path or not os.path.isfile(file_path):
            return
        path = os.path.normpath(os.path.abspath(file_path))
        if path in self.recent_files:
            self.recent_files.remove(path)
        self.recent_files.insert(0, path)
        self.recent_files = self.recent_files[: self.RECENT_MAX]
        self.settings.setValue(self.RECENT_KEY, self.recent_files)
        self._update_recent_files_menu()
    
    def _open_recent(self, file_path: str):
        """Open a recent file (image or .iep by extension)."""
        if not self.prompt_save_unsaved():
            return
        if not file_path or not os.path.isfile(file_path):
            QMessageBox.warning(self, "Open Recent", "File no longer exists.")
            self._load_recent_files()
            self._update_recent_files_menu()
            return
        if file_path.lower().endswith(".iep"):
            self._open_project_path(file_path)
        else:
            self._open_image_path(file_path)
    
    def _replace_project_and_reconnect(self):
        """After loading a new project, wire it to canvas and layer panel."""
        self.canvas.project = self.project
        self.layer_panel.project = self.project
        self.project.layers_changed.connect(self.canvas.on_project_changed)
        self.project.layer_modified.connect(self.canvas.on_project_changed)
        self.project.layers_changed.connect(self.layer_panel.refresh_layers)
        self.project.layer_modified.connect(self.layer_panel.on_layer_modified)
        self.canvas.update_size()
        self.layer_panel.refresh_layers()
    
    def _open_image_path(self, file_path: str):
        """Open an image file at path (used by Open Image and Open Recent)."""
        try:
            image = Image.open(file_path)
            image.load()  # Force load to catch truncated/corrupt files
            self.project = Project(image.width, image.height)
            self.project.layers[0].image = image.convert("RGBA")
            self._replace_project_and_reconnect()
            self._add_to_recent(file_path)
            self.setWindowTitle(f"Image Editor Pro - {os.path.basename(file_path)}")
            self.modified = False
            self.command_history.clear()
        except FileNotFoundError:
            QMessageBox.critical(self, "Error", "File not found.")
        except PermissionError:
            QMessageBox.critical(self, "Error", "Permission denied. Cannot read that file.")
        except OSError as e:
            if "cannot identify" in str(e).lower() or "truncated" in str(e).lower():
                QMessageBox.critical(self, "Error", "The file is not a valid or supported image, or it may be corrupted.")
            else:
                QMessageBox.critical(self, "Error", f"Cannot open image: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open image: {str(e)}")
    
    def _open_project_path(self, file_path: str):
        """Open a project file at path (used by Open Project and Open Recent)."""
        try:
            self.project = Project.load_project(file_path)
            self._replace_project_and_reconnect()
            self._add_to_recent(file_path)
            self.setWindowTitle(f"Image Editor Pro - {os.path.basename(file_path)}")
            self.modified = False
            self.command_history.clear()
        except FileNotFoundError:
            QMessageBox.critical(self, "Error", "File not found.")
        except PermissionError:
            QMessageBox.critical(self, "Error", "Permission denied. Cannot read that file.")
        except json.JSONDecodeError:
            QMessageBox.critical(
                self, "Error",
                "The project file is corrupted or not a valid .iep file."
            )
        except (KeyError, TypeError, ValueError):
            QMessageBox.critical(
                self, "Error",
                "The project file has an invalid structure and cannot be opened."
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open project: {str(e)}")
    
    # Layer operations
    
    def add_layer(self):
        """Add a new layer."""
        name, ok = QInputDialog.getText(self, "New Layer", "Layer name:", text="New Layer")
        if ok:
            command = AddLayerCommand(self.project, name)
            self.command_history.execute(command)
            self.modified = True
    
    def add_image_from_file(self):
        """Import an image file as a new layer (resized to fit canvas)."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Add Image as Layer",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)"
        )
        if not file_path:
            return
        try:
            img = Image.open(file_path)
            img.load()
            img_rgba = img.convert("RGBA")
            pw, ph = self.project.width, self.project.height
            iw, ih = img_rgba.size
            if (iw, ih) != (pw, ph):
                img_rgba = img_rgba.resize((pw, ph), Image.Resampling.LANCZOS)
            name = os.path.splitext(os.path.basename(file_path))[0]
            self.project.add_layer(name or "Image", image=img_rgba)
            self.layer_panel.refresh_layers()
            self.modified = True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load image: {str(e)}")
    
    def remove_layer(self, layer_index: int):
        """Remove a layer.
        
        Args:
            layer_index: Index of layer to remove
        """
        if len(self.project.layers) <= 1:
            QMessageBox.warning(self, "Warning", "Cannot remove the last layer!")
            return
        
        command = RemoveLayerCommand(self.project, layer_index)
        self.command_history.execute(command)
        self.modified = True
    
    def move_layer_up(self, layer_index: int):
        """Move layer up.
        
        Args:
            layer_index: Index of layer to move
        """
        if layer_index < len(self.project.layers) - 1:
            command = MoveLayerCommand(self.project, layer_index, layer_index + 1)
            self.command_history.execute(command)
            self.modified = True
    
    def move_layer_down(self, layer_index: int):
        """Move layer down.
        
        Args:
            layer_index: Index of layer to move
        """
        if layer_index > 0:
            command = MoveLayerCommand(self.project, layer_index, layer_index - 1)
            self.command_history.execute(command)
            self.modified = True
    
    def set_layer_opacity(self, layer_index: int, opacity: int):
        """Set layer opacity.
        
        Args:
            layer_index: Index of layer
            opacity: New opacity value
        """
        layer = self.project.get_layer(layer_index)
        if layer and layer.opacity != opacity:
            command = SetLayerOpacityCommand(self.project, layer_index, layer.opacity, opacity)
            self.command_history.execute(command)
            self.modified = True
    
    def toggle_layer_visibility(self, layer_index: int):
        """Toggle layer visibility.
        
        Args:
            layer_index: Index of layer
        """
        command = SetLayerVisibilityCommand(self.project, layer_index)
        self.command_history.execute(command)
        self.modified = True
    
    def duplicate_layer(self):
        """Duplicate the selected layer."""
        current_index = self.layer_panel.current_layer_index
        layer = self.project.get_layer(current_index)
        
        if layer:
            new_layer = self.project.add_layer(f"{layer.name} Copy", image=layer.image.copy())
            new_layer.opacity = layer.opacity
            new_layer.visible = layer.visible
            self.modified = True
    
    def merge_down(self):
        """Merge selected layer with layer below."""
        current_index = self.layer_panel.current_layer_index
        
        if current_index <= 0:
            QMessageBox.warning(self, "Warning", "Cannot merge down the bottom layer!")
            return
        
        # Get layers
        upper_layer = self.project.get_layer(current_index)
        lower_layer = self.project.get_layer(current_index - 1)
        
        if upper_layer and lower_layer:
            # Composite layers
            merged = Image.alpha_composite(lower_layer.image, upper_layer.image)
            lower_layer.image = merged
            
            # Remove upper layer
            self.project.remove_layer(current_index)
            self.modified = True
    
    def flatten_image(self):
        """Merge all layers into one (undoable)."""
        if len(self.project.layers) <= 1:
            QMessageBox.information(self, "Flatten", "Only one layer — nothing to flatten.")
            return
        reply = QMessageBox.question(
            self, "Flatten Image",
            "Merge all layers into one? This cannot be undone beyond a single Undo.",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Ok
        )
        if reply == QMessageBox.StandardButton.Ok:
            command = FlattenImageCommand(self.project)
            self.command_history.execute(command)
            self.modified = True
            self.layer_panel.refresh_layers()
    
    def add_text_to_layer(self):
        """Draw text on the current layer (dialog: text, font, size, color, position)."""
        current_index = self.layer_panel.current_layer_index
        layer = self.project.get_layer(current_index)
        if not layer:
            return
        dialog = AddTextDialog(layer.image.width, layer.image.height, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        text = dialog.get_text()
        if not text:
            return
        size = dialog.get_font_size()
        color = dialog.get_color()
        font_idx = dialog.get_font_index()
        font_name, font_file = ADD_TEXT_FONTS[font_idx]
        font = None
        try:
            fonts_dir = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts")
            path = os.path.join(fonts_dir, font_file)
            if os.path.isfile(path):
                font = ImageFont.truetype(path, size)
            if font is None:
                path = os.path.join(fonts_dir, "arial.ttf")
                if os.path.isfile(path):
                    font = ImageFont.truetype(path, size)
            if font is None:
                for _path in ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
                    if os.path.isfile(_path):
                        font = ImageFont.truetype(_path, size)
                        break
        except Exception:
            pass
        if font is None:
            font = ImageFont.load_default()
        old_image = layer.image.copy()
        new_image = old_image.copy()
        draw = ImageDraw.Draw(new_image, "RGBA")
        x, y = dialog.get_position(draw, text, font)
        fill = (color.red(), color.green(), color.blue(), 255)
        draw.text((x, y), text, fill=fill, font=font)
        self._push_layer_filter_history(layer)
        command = FilterCommand(self.project, current_index, "Add Text", old_image, new_image)
        self.command_history.execute(command)
        self.modified = True
        self.update_remove_last_filter_actions()
    
    def copy_merged(self):
        """Copy the composited image (all layers) to the clipboard."""
        rendered = self.project.render()
        arr = np.array(rendered)
        h, w, c = arr.shape
        qimg = QImage(arr.data, w, h, c * w, QImage.Format.Format_RGBA8888)
        QApplication.clipboard().setImage(qimg.copy())
    
    def paste_as_new_layer(self):
        """Paste clipboard image as a new layer (center or resize to fit)."""
        qimg = QApplication.clipboard().image()
        if qimg.isNull():
            QMessageBox.information(self, "Paste", "No image in clipboard.")
            return
        from PyQt6.QtCore import QBuffer
        buf = QBuffer()
        buf.open(QBuffer.OpenModeFlag.WriteOnly)
        qimg.save(buf, b"PNG")
        data = bytes(buf.data().data())
        pil_img = Image.open(io.BytesIO(data)).convert("RGBA")
        pw, ph = self.project.width, self.project.height
        iw, ih = pil_img.size
        if (iw, ih) != (pw, ph):
            pil_img = pil_img.resize((pw, ph), Image.Resampling.LANCZOS)
        self.project.add_layer("Pasted", image=pil_img)
        self.modified = True
        self.layer_panel.refresh_layers()
    
    def revert_project(self):
        """Revert to last saved state (reload from file)."""
        if not self.project.file_path or not os.path.isfile(self.project.file_path):
            return
        if not self.modified:
            return
        reply = QMessageBox.question(
            self, "Revert",
            "Revert to last saved version? All unsaved changes will be lost.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            self.project = Project.load_project(self.project.file_path)
            self.canvas.project = self.project
            self.layer_panel.project = self.project
            self.project.layers_changed.connect(self.canvas.on_project_changed)
            self.project.layer_modified.connect(self.canvas.on_project_changed)
            self.project.layers_changed.connect(self.layer_panel.refresh_layers)
            self.project.layer_modified.connect(self.layer_panel.on_layer_modified)
            self.canvas.update_size()
            self.layer_panel.refresh_layers()
            self.command_history.clear()
            self.modified = False
            self.update_undo_redo_actions()
            self.update_remove_last_filter_actions()
            self.revert_action.setEnabled(False)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to revert: {e}")
    
    # Image transform and resize
    
    def transform_layer(self, action: str):
        """Flip or rotate the current layer. Uses same undo as filters."""
        from PIL import Image as PILImage
        current_index = self.layer_panel.current_layer_index
        layer = self.project.get_layer(current_index)
        if not layer:
            return
        old_image = layer.image.copy()
        if action == "Flip Horizontal":
            new_image = old_image.transpose(PILImage.Transpose.FLIP_LEFT_RIGHT)
        elif action == "Flip Vertical":
            new_image = old_image.transpose(PILImage.Transpose.FLIP_TOP_BOTTOM)
        elif action == "Rotate 90 CW":
            new_image = old_image.transpose(PILImage.Transpose.ROTATE_270)
        elif action == "Rotate 90 CCW":
            new_image = old_image.transpose(PILImage.Transpose.ROTATE_90)
        elif action == "Rotate 180":
            new_image = old_image.transpose(PILImage.Transpose.ROTATE_180)
        else:
            return
        self._push_layer_filter_history(layer)
        command = FilterCommand(self.project, current_index, action, old_image, new_image)
        self.command_history.execute(command)
        self.modified = True
        self.update_remove_last_filter_actions()
    
    def rotate_layer_arbitrary(self):
        """Rotate the current layer by an arbitrary angle (degrees)."""
        from PIL import Image as PILImage
        current_index = self.layer_panel.current_layer_index
        layer = self.project.get_layer(current_index)
        if not layer:
            return
        angle, ok = QInputDialog.getDouble(
            self, "Rotate Arbitrary", "Angle (degrees, counter-clockwise):",
            0.0, -360.0, 360.0, 1
        )
        if not ok:
            return
        if abs(angle) < 0.01:
            return
        old_image = layer.image.copy()
        # expand=False keeps canvas size; corners may be cropped
        new_image = old_image.rotate(-angle, resample=PILImage.Resampling.BICUBIC, expand=False)
        self._push_layer_filter_history(layer)
        command = FilterCommand(
            self.project, current_index, "Rotate Arbitrary", old_image, new_image
        )
        self.command_history.execute(command)
        self.modified = True
        self.update_remove_last_filter_actions()
    
    def resize_layer(self):
        """Resize the current layer to new dimensions; content is scaled and centered on the canvas."""
        current_index = self.layer_panel.current_layer_index
        layer = self.project.get_layer(current_index)
        if not layer:
            return
        lw, lh = layer.image.size
        pw, ph = self.project.width, self.project.height
        w, ok1 = QInputDialog.getInt(
            self, "Resize Layer", "Width:", lw, 1, max(pw, 10000)
        )
        if not ok1:
            return
        h, ok2 = QInputDialog.getInt(
            self, "Resize Layer", "Height:", lh, 1, max(ph, 10000)
        )
        if not ok2:
            return
        if w == lw and h == lh:
            return
        old_image = layer.image.copy()
        resized = old_image.resize((w, h), Image.Resampling.LANCZOS)
        new_image = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
        x = (pw - w) // 2
        y = (ph - h) // 2
        new_image.paste(resized, (x, y))
        self._push_layer_filter_history(layer)
        command = FilterCommand(
            self.project, current_index, "Resize Layer", old_image, new_image
        )
        self.command_history.execute(command)
        self.modified = True
        self.update_remove_last_filter_actions()
    
    def resize_image(self):
        """Resize canvas and all layers to new dimensions."""
        w, ok1 = QInputDialog.getInt(self, "Resize Image", "Width:", self.project.width, 1, 10000)
        if not ok1:
            return
        h, ok2 = QInputDialog.getInt(self, "Resize Image", "Height:", self.project.height, 1, 10000)
        if not ok2:
            return
        if w == self.project.width and h == self.project.height:
            return
        command = ResizeProjectCommand(self.project, w, h)
        self.command_history.execute(command)
        self.modified = True
        self.canvas.update_size()
        self.update_status_bar()
    
    def canvas_size(self):
        """Change canvas size (expand or shrink) with anchor positioning."""
        pw, ph = self.project.width, self.project.height
        dialog = QDialog(self)
        dialog.setWindowTitle("Canvas Size")
        layout = QFormLayout(dialog)
        w_spin = QSpinBox()
        w_spin.setRange(1, 10000)
        w_spin.setValue(pw)
        layout.addRow("Width:", w_spin)
        h_spin = QSpinBox()
        h_spin.setRange(1, 10000)
        h_spin.setValue(ph)
        layout.addRow("Height:", h_spin)
        anchor_combo = QComboBox()
        anchor_combo.addItems([
            "Center", "Top left", "Top", "Top right", "Left", "Right",
            "Bottom left", "Bottom", "Bottom right"
        ])
        layout.addRow("Anchor:", anchor_combo)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        nw, nh = w_spin.value(), h_spin.value()
        if nw == pw and nh == ph:
            return
        idx = anchor_combo.currentIndex()
        # 0=center, 1=TL, 2=Top, 3=TR, 4=Left, 5=Right, 6=BL, 7=Bottom, 8=BR -> (anchor_h, anchor_v)
        anchor_map = [(1, 1), (0, 0), (1, 0), (2, 0), (0, 1), (2, 1), (0, 2), (1, 2), (2, 2)]
        ah, av = anchor_map[idx]
        command = CanvasSizeCommand(self.project, nw, nh, ah, av)
        self.command_history.execute(command)
        self.modified = True
        self.canvas.update_size()
        self.update_status_bar()
    
    def crop_image(self):
        """Switch to Crop tool so the user can drag a rectangle on the canvas (live preview)."""
        self.tool_panel.select_tool("crop")
    
    def make_color_transparent(self):
        """Make pixels matching the chosen color transparent on the current layer."""
        current_index = self.layer_panel.current_layer_index
        layer = self.project.get_layer(current_index)
        if not layer:
            return
        color = QColorDialog.getColor(QColor(255, 255, 255), self, "Color to make transparent")
        if not color.isValid():
            return
        tolerance, ok = QInputDialog.getInt(
            self, "Make color transparent", "Tolerance (0-255, how close a pixel must match):",
            30, 0, 255
        )
        if not ok:
            return
        old_image = layer.image.copy()
        new_image = Filters.make_color_transparent(
            old_image, color.red(), color.green(), color.blue(), tolerance
        )
        self._push_layer_filter_history(layer)
        command = FilterCommand(
            self.project, current_index, "Make color transparent", old_image, new_image
        )
        self.command_history.execute(command)
        self.modified = True
        self.update_remove_last_filter_actions()
    
    def trim_image(self):
        """Trim canvas to content: transparent pixels or top-left pixel color."""
        rendered = self.project.render()
        arr = np.array(rendered)
        if arr.size == 0:
            return
        pw, ph = self.project.width, self.project.height
        dialog = QDialog(self)
        dialog.setWindowTitle("Trim")
        layout = QFormLayout(dialog)
        mode_combo = QComboBox()
        mode_combo.addItems(["Transparent pixels", "Top-left pixel color"])
        layout.addRow("Trim based on:", mode_combo)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if mode_combo.currentIndex() == 0:
            # Transparent: alpha > 10
            alpha = arr[:, :, 3] if arr.ndim >= 3 else np.full((ph, pw), 255)
            if alpha.size == 0:
                return
            visible = alpha > 10
        else:
            # Top-left pixel color (with small tolerance)
            r0, g0, b0, a0 = (int(arr[0, 0, c]) for c in range(min(4, arr.shape[2])))
            tol = 5
            if arr.ndim >= 3:
                diff = np.any(np.abs(arr[:, :, :4].astype(np.int32) - [r0, g0, b0, a0]) > tol, axis=2)
            else:
                diff = np.abs(arr.astype(np.int32) - r0) > tol
            visible = diff
        if not np.any(visible):
            QMessageBox.information(self, "Trim", "No content to trim to.")
            return
        rows = np.any(visible, axis=1)
        cols = np.any(visible, axis=0)
        y_min, y_max = int(np.argmax(rows)), int(len(rows) - np.argmax(rows[::-1]) - 1)
        x_min, x_max = int(np.argmax(cols)), int(len(cols) - np.argmax(cols[::-1]) - 1)
        if x_min > x_max or y_min > y_max:
            return
        left, top = x_min, y_min
        w, h = x_max - x_min + 1, y_max - y_min + 1
        if left == 0 and top == 0 and w == pw and h == ph:
            QMessageBox.information(self, "Trim", "Content already fills the canvas.")
            return
        command = CropProjectCommand(self.project, left, top, w, h)
        self.command_history.execute(command)
        self.modified = True
        self.canvas.update_size()
        self.update_status_bar()
    
    def fill_layer(self):
        """Fill the current layer with a color (dialog: color + opacity)."""
        current_index = self.layer_panel.current_layer_index
        layer = self.project.get_layer(current_index)
        if not layer:
            return
        color = QColorDialog.getColor(QColor(255, 255, 255), self, "Fill Color")
        if not color.isValid():
            return
        opacity, ok = QInputDialog.getInt(self, "Fill", "Opacity (%):", 100, 0, 100)
        if not ok:
            return
        w, h = layer.image.size
        r, g, b = color.red(), color.green(), color.blue()
        alpha = int(255 * opacity / 100)
        fill_color = (r, g, b, alpha)
        new_image = Image.new("RGBA", (w, h), fill_color)
        old_image = layer.image.copy()
        command = FillLayerCommand(self.project, current_index, old_image, new_image)
        self.command_history.execute(command)
        self.modified = True
    
    def clear_layer(self):
        """Clear the current layer to transparent (undoable)."""
        current_index = self.layer_panel.current_layer_index
        layer = self.project.get_layer(current_index)
        if not layer:
            return
        old_image = layer.image.copy()
        command = ClearLayerCommand(self.project, current_index, old_image)
        self.command_history.execute(command)
        self.modified = True
    
    # Filter operations
    
    FILTER_HISTORY_MAX = 20  # max per-layer filter steps to remember for "Remove last filter"
    
    def _push_layer_filter_history(self, layer):
        """Push current layer image to its filter history (for Remove last filter from layer)."""
        layer.filter_history.append(layer.image.copy())
        if len(layer.filter_history) > self.FILTER_HISTORY_MAX:
            layer.filter_history.pop(0)
    
    def remove_last_filter_from_layer(self):
        """Revert the last filter on the current layer only (does not use global Undo)."""
        current_index = self.layer_panel.current_layer_index
        layer = self.project.get_layer(current_index)
        if not layer:
            return
        if not layer.filter_history:
            QMessageBox.information(
                self,
                "Remove last filter",
                "This layer has no filter steps to remove.\n\n"
                "Filters are recorded when you apply Blur, Brightness, etc. "
                "Use this command repeatedly to step back through filters on this layer only."
            )
            return
        restored_image = layer.filter_history.pop()
        current_image = layer.image.copy()
        command = RemoveLastFilterCommand(
            self.project, current_index, current_image, restored_image
        )
        self.command_history.execute(command)
        self.modified = True
        self.update_remove_last_filter_actions()
    
    def update_remove_last_filter_actions(self):
        """Enable/disable 'Remove last filter from layer' based on current layer's filter history."""
        layer = self.project.get_layer(self.layer_panel.current_layer_index) if self.project else None
        enabled = layer is not None and len(layer.filter_history) > 0
        self.remove_last_filter_layer_action.setEnabled(enabled)
        self.remove_last_filter_filter_action.setEnabled(enabled)
    
    def update_revert_action(self):
        """Enable Revert only when there is a saved file path and the project is modified."""
        self.revert_action.setEnabled(
            bool(getattr(self.project, "file_path", None)) and self.modified
        )
    
    def apply_filter(self, filter_name: str):
        """Apply a filter to the selected layer.
        
        Args:
            filter_name: Name of the filter
        """
        current_index = self.layer_panel.current_layer_index
        layer = self.project.get_layer(current_index)
        
        if not layer:
            return
        if layer.image is None or layer.image.size[0] == 0 or layer.image.size[1] == 0:
            QMessageBox.warning(
                self, "Filter",
                "The current layer has no content to filter. Draw or paste something first."
            )
            return
        
        # Store old image
        old_image = layer.image.copy()
        new_image = None
        
        try:
            # Apply filter based on name
            if filter_name in ["Blur", "Sharpen", "Brightness", "Contrast", "Hue/Saturation", "Posterize"]:
                dialog = FilterDialog(
                    filter_name, self,
                    initial_params=self.last_filter_params.get(filter_name, {}),
                    layer_image=layer.image
                )
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    params = dialog.get_parameters()
                    self.last_filter_params[filter_name] = params
                    self._push_layer_filter_history(layer)
                    progress = QProgressDialog("Applying filter...", None, 0, 0, self)
                    progress.setWindowModality(Qt.WindowModality.WindowModal)
                    progress.setMinimumDuration(0)
                    progress.show()
                    QApplication.processEvents()
                    try:
                        if filter_name == "Blur":
                            new_image = Filters.blur(layer.image, **params)
                        elif filter_name == "Sharpen":
                            new_image = Filters.sharpen(layer.image, **params)
                        elif filter_name == "Brightness":
                            new_image = Filters.adjust_brightness(layer.image, **params)
                        elif filter_name == "Contrast":
                            new_image = Filters.adjust_contrast(layer.image, **params)
                        elif filter_name == "Hue/Saturation":
                            new_image = Filters.adjust_hue_saturation(layer.image, **params)
                        elif filter_name == "Posterize":
                            new_image = Filters.posterize(layer.image, **params)
                    finally:
                        progress.close()
            
            else:
                # One-shot filters: show progress so UI doesn't freeze on large images
                self._push_layer_filter_history(layer)
                progress = QProgressDialog("Applying filter...", None, 0, 0, self)
                progress.setWindowModality(Qt.WindowModality.WindowModal)
                progress.setMinimumDuration(0)
                progress.show()
                QApplication.processEvents()
                try:
                    if filter_name == "Sepia":
                        new_image = Filters.sepia(layer.image)
                    elif filter_name == "Grayscale":
                        new_image = Filters.grayscale(layer.image)
                    elif filter_name == "Desaturate":
                        new_image = Filters.desaturate(layer.image)
                    elif filter_name == "Invert":
                        new_image = Filters.invert(layer.image)
                    elif filter_name == "Edge Detect":
                        new_image = Filters.edge_detect(layer.image)
                    elif filter_name == "Emboss":
                        new_image = Filters.emboss(layer.image)
                    elif filter_name == "Smooth":
                        new_image = Filters.smooth(layer.image)
                    elif filter_name == "Detail":
                        new_image = Filters.detail(layer.image)
                finally:
                    progress.close()
            
            if new_image is not None:
                command = FilterCommand(self.project, current_index, filter_name, old_image, new_image)
                self.command_history.execute(command)
                self.modified = True
                self.update_remove_last_filter_actions()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to apply filter: {str(e)}")
    
    # Drawing operations
    
    def _cancel_crop_if_active(self):
        """On Escape: cancel crop drag if Crop tool is active and a rect is being drawn."""
        if self.canvas.current_tool == "crop" and (
            self.canvas.crop_start_point is not None or self.canvas._crop_preview_end is not None
        ):
            self.canvas.cancel_crop()

    def on_crop_requested(self, left: int, top: int, width: int, height: int):
        """Apply crop from canvas drag (live preview)."""
        if width < 1 or height < 1:
            return
        pw, ph = self.project.width, self.project.height
        if left == 0 and top == 0 and width == pw and height == ph:
            return
        command = CropProjectCommand(self.project, left, top, width, height)
        self.command_history.execute(command)
        self.modified = True
        self.canvas.update_size()
        self.layer_panel.refresh_layers()
        self.update_status_bar()

    def on_drawing_completed(self, old_image, new_image, layer_index: int, tool_name: str):
        """Handle drawing completion.

        Args:
            old_image: Image before drawing
            new_image: Image after drawing
            layer_index: Index of layer that was drawn on
            tool_name: Tool id (e.g. 'brush', 'eraser') for history display
        """
        if np.array_equal(np.array(old_image), np.array(new_image)):
            return
        display_name = DrawCommand.DISPLAY_NAMES.get(tool_name, "Draw")
        command = DrawCommand(
            self.project, layer_index, old_image, new_image, action_name=display_name
        )
        self.command_history.execute(command)
        self.modified = True
    
    # UI updates
    
    def update_undo_redo_actions(self):
        """Update undo/redo action states."""
        can_undo = self.command_history.can_undo()
        can_redo = self.command_history.can_redo()
        self.undo_action.setEnabled(can_undo)
        self.redo_action.setEnabled(can_redo)
        self.undo_last_filter_action.setEnabled(can_undo)
        self.redo_last_filter_action.setEnabled(can_redo)
        self.update_revert_action()
        
        # Update text
        undo_text = self.command_history.get_undo_text()
        if undo_text:
            self.undo_action.setText(undo_text)
        else:
            self.undo_action.setText("Undo")
        
        redo_text = self.command_history.get_redo_text()
        if redo_text:
            self.redo_action.setText(redo_text)
        else:
            self.redo_action.setText("Redo")
    
    def show_keyboard_shortcuts(self):
        """Show keyboard shortcuts dialog."""
        text = """
<h3>File</h3>
Ctrl+N – New<br>
Ctrl+O – Open Image<br>
Ctrl+Shift+O – Open Project<br>
Ctrl+S – Save Image<br>
Ctrl+Shift+S – Save Project<br><br>

<h3>Edit</h3>
Ctrl+Z – Undo<br>
Ctrl+Y – Redo<br>
Ctrl+Shift+C – Copy Merged<br>
Ctrl+Shift+V – Paste as New Layer<br><br>

<h3>View</h3>
Ctrl++ – Zoom In<br>
Ctrl+- – Zoom Out<br>
Ctrl+0 – Reset Zoom<br>
Ctrl+1 – Fit to Window<br>
Ctrl+2 – Actual Size (100%)<br><br>

<h3>Tools</h3>
B – Brush<br>
E – Eraser<br>
T – Transparency<br>
I – Eyedropper<br>
G – Paint Bucket<br>
R – Shapes<br><br>

<h3>Layer</h3>
Ctrl+Shift+N – New Layer<br>
Ctrl+J – Duplicate Layer<br>
Ctrl+E – Merge Down<br>
"""
        QMessageBox.information(self, "Keyboard Shortcuts", text)
    
    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About Image Editor Pro",
            "<h2>Image Editor Pro</h2>"
            "<p>Version 1.0.0</p>"
            "<p>A professional desktop image editing application built with PyQt6.</p>"
            "<p><b>Features:</b></p>"
            "<ul>"
            "<li>Layer-based editing</li>"
            "<li>Drawing tools (brush, eraser)</li>"
            "<li>Image filters and adjustments</li>"
            "<li>Full undo/redo support</li>"
            "<li>Custom project format</li>"
            "</ul>"
            "<p>Built with Python, PyQt6, PIL/Pillow, and NumPy.</p>"
        )
    
    # Settings
    
    def save_settings(self):
        """Save application settings."""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
    
    def restore_settings(self):
        """Restore application settings."""
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        state = self.settings.value("windowState")
        if state:
            self.restoreState(state)
    
    def closeEvent(self, event):
        """Handle window close event."""
        if not self.prompt_save_unsaved():
            event.ignore()
            return
        self.save_settings()
        event.accept()
