"""UI panels for the image editor.

This module provides:
- Layer panel for managing layers
- Tool options panel for tool settings
- Color picker panel
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSlider, QListWidget, QListWidgetItem, QGroupBox, QSpinBox,
    QColorDialog, QCheckBox, QInputDialog, QFrame,
    QMessageBox, QComboBox, QToolButton, QToolTip,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QBrush
from typing import List, Optional


def _make_tool_icon(name: str, size: int = 24) -> QIcon:
    """Draw a simple icon for a tool in light grey (for use on dark grey button background)."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    icon_color = QColor(230, 230, 230)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    pen = QPen(icon_color, 1.5)
    p.setPen(pen)
    p.setBrush(QBrush(icon_color))
    cx, cy = size // 2, size // 2
    if name == "brush":
        # Brush: circle (tip) with a short stroke
        r = size // 5
        p.drawEllipse(cx - r, cy - r, 2 * r, 2 * r)
        p.drawLine(cx - r, cy, cx + r + 2, cy - 2)
    elif name == "eraser":
        # Eraser: rounded rectangle
        margin = size // 5
        p.drawRoundedRect(margin, margin, size - 2 * margin, size - 2 * margin, 3, 3)
    elif name == "eyedropper":
        # Eyedropper: small circle at bottom, line up to top-left
        drop_r = size // 6
        p.drawEllipse(cx - drop_r, cy + 2, 2 * drop_r, 2 * drop_r)
        p.drawLine(cx, cy - 4, cx - 4, 2)
        p.drawLine(cx - 4, 2, cx + 2, 2)
    elif name == "paint_bucket":
        # Paint bucket: tilted bucket shape (trapezoid + handle)
        margin = size // 6
        p.drawLine(cx - 4, cy + 2, cx + 4, cy + 2)
        p.drawLine(cx + 4, cy + 2, cx + 2, cy - 4)
        p.drawLine(cx + 2, cy - 4, cx - 2, cy - 2)
        p.drawLine(cx - 2, cy - 2, cx - 4, cy + 2)
        p.drawLine(cx + 2, cy - 4, cx + 4, cy - 2)
    elif name == "shape":
        p.drawRect(cx - 6, cy - 5, 12, 10)
    elif name == "transparency":
        p.drawRect(cx - 5, cy - 5, 10, 10)
        p.drawLine(cx - 3, cy - 3, cx + 3, cy + 3)
        p.drawLine(cx + 3, cy - 3, cx - 3, cy + 3)
    elif name == "zoom":
        p.drawEllipse(cx - 6, cy - 6, 12, 12)
        p.drawLine(cx + 3, cy + 3, cx + 7, cy + 7)
        p.drawRect(cx + 5, cy + 5, 5, 5)
    elif name == "crop":
        p.drawRect(cx - 6, cy - 5, 12, 10)
        p.drawLine(cx - 6, cy - 5, cx + 6, cy + 5)
    p.end()
    return QIcon(pix)


# Short and long descriptions for tools (name, shortcut, detail)
TOOL_INFO = {
    "brush": (
        "Brush (B)",
        "Draw with the current color and opacity. Use the sliders below for size and opacity.",
    ),
    "eraser": (
        "Eraser (E)",
        "Remove paint on the current layer by restoring pixels to what is visible "
        "from the layers below (no transparency). Only affects the active layer.",
    ),
    "transparency": (
        "Transparency (T)",
        "Paint transparency (alpha = 0) on the current layer. Use for punching holes or erasing to see through.",
    ),
    "eyedropper": (
        "Eyedropper (I)",
        "Click on the canvas to set the brush color from the composited image at that pixel.",
    ),
    "paint_bucket": (
        "Paint Bucket (G)",
        "Click to fill a contiguous area of similar color on the current layer. "
        "Use tolerance to control how similar colors must be.",
    ),
    "shape": (
        "Shapes (R)",
        "Draw shapes on the current layer. Choose Rectangle, Ellipse, etc. from the "
        "dropdown below, then click and drag on the canvas.",
    ),
    "zoom": (
        "Zoom (Z)",
        "Click to zoom in on an area. Shift+click to zoom out. Keeps the point under the cursor in view.",
    ),
    "crop": (
        "Crop (C)",
        "Drag a rectangle to set the crop region. Release to apply. Right-click or Escape to cancel.",
    ),
}

# Shape kinds for the Shapes tool dropdown (id, display name)
SHAPE_OPTIONS = [
    ("rectangle", "Rectangle"),
    ("ellipse", "Ellipse"),
    ("rounded_rect", "Rounded rectangle"),
    ("line", "Line"),
]
# Shape style: filled with color, outline only, or transparent (filled or outline)
SHAPE_STYLE_OPTIONS = [
    ("filled", "Filled"),
    ("outline", "Outline only"),
    ("transparent_fill", "Transparent (filled)"),
    ("transparent_outline", "Transparent (outline)"),
]


class LayerPanel(QWidget):
    """Panel for managing layers.
    
    Features:
    - List of layers with thumbnails
    - Add/remove layer buttons
    - Layer visibility toggle
    - Opacity slider
    - Move up/down buttons
    
    Signals:
        layer_selected: Emitted when a layer is selected (layer_index)
        add_layer_requested: Emitted when add layer button is clicked
        remove_layer_requested: Emitted when remove layer button is clicked (layer_index)
        move_layer_up_requested: Emitted when move up is requested (layer_index)
        move_layer_down_requested: Emitted when move down is requested (layer_index)
        opacity_changed: Emitted when opacity changes (layer_index, opacity)
        visibility_toggled: Emitted when visibility is toggled (layer_index)
    """
    
    layer_selected = pyqtSignal(int)
    layer_rename_requested = pyqtSignal(int, str)  # layer_index, new_name
    add_layer_requested = pyqtSignal()
    remove_layer_requested = pyqtSignal(int)
    move_layer_up_requested = pyqtSignal(int)
    move_layer_down_requested = pyqtSignal(int)
    opacity_changed = pyqtSignal(int, int)
    visibility_toggled = pyqtSignal(int)
    
    def __init__(self, project, parent=None):
        """Initialize the layer panel.
        
        Args:
            project: Project instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.project = project
        self.current_layer_index = 0
        self.setMaximumWidth(500)
        self.setMinimumWidth(80)
        
        self.setup_ui()
        self.refresh_layers()
        
        # Connect signals
        self.project.layers_changed.connect(self.refresh_layers)
        self.project.layer_modified.connect(self.on_layer_modified)
    
    def setup_ui(self):
        """Set up the user interface."""
        self._layers_expanded = True
        self._panel_collapsed = False
        
        self.layers_main_widget = QWidget()
        layout = QVBoxLayout(self.layers_main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Title row with condense and collapse
        title_row = QHBoxLayout()
        title = QLabel("Layers")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        title_row.addWidget(title)
        title_row.addStretch()
        self.layers_expand_btn = QPushButton("−")
        self.layers_expand_btn.setFixedSize(24, 24)
        self.layers_expand_btn.setToolTip("Condense panel")
        self.layers_expand_btn.clicked.connect(self._toggle_layers_expanded)
        title_row.addWidget(self.layers_expand_btn)
        self.layers_collapse_btn = QPushButton("<<")
        self.layers_collapse_btn.setFixedSize(24, 24)
        self.layers_collapse_btn.setToolTip("Collapse panel")
        self.layers_collapse_btn.clicked.connect(self._toggle_layers_panel_collapsed)
        title_row.addWidget(self.layers_collapse_btn)
        layout.addLayout(title_row)
        
        # Layer list
        self.layer_list = QListWidget()
        self.layer_list.setIconSize(QSize(64, 64))
        self.layer_list.currentRowChanged.connect(self.on_layer_selected)
        self.layer_list.itemDoubleClicked.connect(self.on_layer_double_clicked)
        layout.addWidget(self.layer_list)
        
        # Layer controls (in details - can be condensed)
        self.layers_details_widget = QWidget()
        layers_details_layout = QVBoxLayout(self.layers_details_widget)
        layers_details_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("+")
        self.add_btn.setToolTip("Add Layer")
        self.add_btn.clicked.connect(self.add_layer_requested.emit)
        controls_layout.addWidget(self.add_btn)
        
        self.remove_btn = QPushButton("-")
        self.remove_btn.setToolTip("Remove Layer")
        self.remove_btn.clicked.connect(self.on_remove_layer)
        controls_layout.addWidget(self.remove_btn)
        
        self.up_btn = QPushButton("↑")
        self.up_btn.setToolTip("Move Layer Up")
        self.up_btn.clicked.connect(self.on_move_up)
        controls_layout.addWidget(self.up_btn)
        
        self.down_btn = QPushButton("↓")
        self.down_btn.setToolTip("Move Layer Down")
        self.down_btn.clicked.connect(self.on_move_down)
        controls_layout.addWidget(self.down_btn)
        
        layers_details_layout.addLayout(controls_layout)
        
        # Opacity control
        opacity_group = QGroupBox("Opacity")
        opacity_layout = QVBoxLayout()
        
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setMinimum(0)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.valueChanged.connect(self.on_opacity_changed)
        opacity_layout.addWidget(self.opacity_slider)
        
        self.opacity_label = QLabel("100%")
        self.opacity_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        opacity_layout.addWidget(self.opacity_label)
        
        opacity_group.setLayout(opacity_layout)
        layers_details_layout.addWidget(opacity_group)
        
        # Visibility checkbox
        self.visibility_check = QCheckBox("Visible")
        self.visibility_check.setChecked(True)
        self.visibility_check.stateChanged.connect(self.on_visibility_toggled)
        layers_details_layout.addWidget(self.visibility_check)
        
        layers_details_layout.addStretch()
        layout.addWidget(self.layers_details_widget)
        
        layout.addStretch()
        
        # Collapsed bar
        self.layers_collapsed_bar = QWidget()
        self.layers_collapsed_bar.setMaximumWidth(44)
        bar_layout = QVBoxLayout(self.layers_collapsed_bar)
        bar_layout.setContentsMargins(4, 4, 4, 4)
        bar_label = QLabel("Layers")
        bar_label.setStyleSheet("font-weight: bold; font-size: 11px;")
        bar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bar_layout.addWidget(bar_label)
        self.layers_expand_panel_btn = QPushButton(">>")
        self.layers_expand_panel_btn.setToolTip("Expand panel")
        self.layers_expand_panel_btn.clicked.connect(self._toggle_layers_panel_collapsed)
        bar_layout.addWidget(self.layers_expand_panel_btn)
        bar_layout.addStretch()
        self.layers_collapsed_bar.hide()
        
        top_layout = QVBoxLayout(self)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addWidget(self.layers_main_widget)
        top_layout.addWidget(self.layers_collapsed_bar)
    
    def _toggle_layers_panel_collapsed(self):
        self._panel_collapsed = not self._panel_collapsed
        self.layers_main_widget.setVisible(not self._panel_collapsed)
        self.layers_collapsed_bar.setVisible(self._panel_collapsed)
        self.setMaximumWidth(44 if self._panel_collapsed else 500)
    
    def _toggle_layers_expanded(self):
        self._layers_expanded = not self._layers_expanded
        self.layers_details_widget.setVisible(self._layers_expanded)
        self.layers_expand_btn.setText("−" if self._layers_expanded else "+")
        self.layers_expand_btn.setToolTip("Condense panel" if self._layers_expanded else "Expand panel")
    
    def refresh_layers(self):
        """Refresh the layer list."""
        self.layer_list.clear()
        
        # Add layers in reverse order (top to bottom)
        for i in range(len(self.project.layers) - 1, -1, -1):
            layer = self.project.layers[i]
            
            # Create list item
            item = QListWidgetItem()
            item.setText(layer.name)
            
            # Add thumbnail
            thumbnail = layer.get_thumbnail((64, 64))
            item.setIcon(QIcon(thumbnail))
            
            # Add to list
            self.layer_list.addItem(item)
        
        # Select the last layer (top-most)
        if len(self.project.layers) > 0:
            self.layer_list.setCurrentRow(0)
    
    def on_layer_modified(self, layer_index: int):
        """Handle layer modification.
        
        Args:
            layer_index: Index of modified layer
        """
        # Update thumbnail
        layer = self.project.get_layer(layer_index)
        if layer:
            # Convert layer index to list row (reversed)
            row = len(self.project.layers) - 1 - layer_index
            if 0 <= row < self.layer_list.count():
                item = self.layer_list.item(row)
                thumbnail = layer.get_thumbnail((64, 64))
                item.setIcon(QIcon(thumbnail))
    
    def on_layer_selected(self, row: int):
        """Handle layer selection.
        
        Args:
            row: Selected row in list
        """
        if row >= 0:
            # Convert row to layer index (reversed)
            layer_index = len(self.project.layers) - 1 - row
            self.current_layer_index = layer_index
            
            # Update controls
            layer = self.project.get_layer(layer_index)
            if layer:
                self.opacity_slider.setValue(layer.opacity)
                self.opacity_label.setText(f"{layer.opacity}%")
                self.visibility_check.setChecked(layer.visible)
            
            self.layer_selected.emit(layer_index)
    
    def on_remove_layer(self):
        """Handle remove layer button click."""
        if self.layer_list.currentRow() >= 0:
            self.remove_layer_requested.emit(self.current_layer_index)
    
    def on_move_up(self):
        """Handle move up button click."""
        if self.current_layer_index < len(self.project.layers) - 1:
            self.move_layer_up_requested.emit(self.current_layer_index)
    
    def on_move_down(self):
        """Handle move down button click."""
        if self.current_layer_index > 0:
            self.move_layer_down_requested.emit(self.current_layer_index)
    
    def on_opacity_changed(self, value: int):
        """Handle opacity slider change.
        
        Args:
            value: New opacity value
        """
        self.opacity_label.setText(f"{value}%")
        self.opacity_changed.emit(self.current_layer_index, value)
    
    def on_visibility_toggled(self, state: int):
        """Handle visibility checkbox toggle.
        
        Args:
            state: Checkbox state
        """
        self.visibility_toggled.emit(self.current_layer_index)
    
    def on_layer_double_clicked(self, item: QListWidgetItem):
        """Rename layer on double-click."""
        row = self.layer_list.row(item)
        layer_index = len(self.project.layers) - 1 - row
        layer = self.project.get_layer(layer_index)
        if not layer:
            return
        new_name, ok = QInputDialog.getText(self, "Rename Layer", "Layer name:", text=layer.name)
        if ok and new_name.strip():
            self.layer_rename_requested.emit(layer_index, new_name.strip())


class ToolOptionsPanel(QWidget):
    """Panel for tool options.
    
    Features:
    - Brush size control
    - Brush opacity control
    - Color picker
    - Tool selection
    
    Signals:
        brush_size_changed: Emitted when brush size changes
        brush_opacity_changed: Emitted when brush opacity changes
        color_changed: Emitted when color changes
        tool_changed: Emitted when tool changes
    """
    
    brush_size_changed = pyqtSignal(int)
    brush_opacity_changed = pyqtSignal(int)
    color_changed = pyqtSignal(QColor)
    tool_changed = pyqtSignal(str)
    paint_bucket_tolerance_changed = pyqtSignal(int)
    shape_kind_changed = pyqtSignal(str)
    shape_style_changed = pyqtSignal(str)
    shape_outline_width_changed = pyqtSignal(int)
    eraser_color_changed = pyqtSignal(QColor)
    
    def __init__(self, parent=None):
        """Initialize the tool options panel.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.current_color = QColor(0, 0, 0, 255)
        self._current_tool = "brush"
        self.setMaximumWidth(500)
        self.setMinimumWidth(200)
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface."""
        self._tools_expanded = True
        self._panel_collapsed = False
        
        # Main content (can be hidden when panel is collapsed)
        self.tools_main_widget = QWidget()
        layout = QVBoxLayout(self.tools_main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Title row with condense and collapse
        title_row = QHBoxLayout()
        title = QLabel("Tools")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        title_row.addWidget(title)
        title_row.addStretch()
        self.tools_expand_btn = QPushButton("−")
        self.tools_expand_btn.setFixedSize(24, 24)
        self.tools_expand_btn.setToolTip("Condense panel")
        self.tools_expand_btn.clicked.connect(self._toggle_tools_expanded)
        title_row.addWidget(self.tools_expand_btn)
        self.tools_collapse_btn = QPushButton("<<")
        self.tools_collapse_btn.setFixedSize(24, 24)
        self.tools_collapse_btn.setToolTip("Collapse panel")
        self.tools_collapse_btn.clicked.connect(self._toggle_tools_panel_collapsed)
        title_row.addWidget(self.tools_collapse_btn)
        layout.addLayout(title_row)
        
        # Tool buttons (icons only for compact layout; light icons on dark grey background)
        tool_group = QGroupBox("Tool")
        tool_group.setStyleSheet(
            "QGroupBox QToolButton { "
            "  background-color: #505050; border: 1px solid #404040; border-radius: 3px; "
            "  color: #e6e6e6; "
            "} "
            "QGroupBox QToolButton:hover { background-color: #5a5a5a; } "
            "QGroupBox QToolButton:checked { background-color: #606060; border-color: #707070; }"
        )
        tool_layout = QHBoxLayout()
        icon_size = 28
        for tool_id, (title, _) in TOOL_INFO.items():
            btn = QToolButton()
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            btn.setIcon(_make_tool_icon(tool_id, 22))
            btn.setIconSize(QSize(icon_size, icon_size))
            btn.setCheckable(True)
            btn.setChecked(tool_id == "brush")
            btn.setFixedSize(icon_size + 12, icon_size + 12)
            btn.setToolTip(f"{title}\n{TOOL_INFO[tool_id][1]}")
            btn.setProperty("tool_id", tool_id)
            btn.clicked.connect(lambda checked=False, t=tool_id: self.select_tool(t))
            tool_layout.addWidget(btn)
            if tool_id == "brush":
                self.brush_btn = btn
            elif tool_id == "eraser":
                self.eraser_btn = btn
            elif tool_id == "transparency":
                self.transparency_btn = btn
            elif tool_id == "eyedropper":
                self.eyedropper_btn = btn
            elif tool_id == "paint_bucket":
                self.paint_bucket_btn = btn
            elif tool_id == "zoom":
                self.zoom_btn = btn
            elif tool_id == "crop":
                self.crop_btn = btn
            else:
                self.shape_btn = btn
        tool_group.setLayout(tool_layout)
        layout.addWidget(tool_group)
        
        # Details (options, size, opacity, color) - can be condensed
        self.tools_details_widget = QWidget()
        tools_details_layout = QVBoxLayout(self.tools_details_widget)
        tools_details_layout.setContentsMargins(0, 0, 0, 0)
        
        # Eraser color (visible when Eraser is selected)
        self.eraser_color_widget = QWidget()
        eraser_layout = QHBoxLayout(self.eraser_color_widget)
        eraser_layout.addWidget(QLabel("Eraser color:"))
        self.eraser_color_display = QLabel()
        self.eraser_color_display.setMinimumHeight(24)
        self.eraser_color_display.setStyleSheet("background-color: rgb(255,255,255); border: 1px solid black;")
        self.eraser_color_display.mousePressEvent = lambda e: self._pick_eraser_color()
        eraser_layout.addWidget(self.eraser_color_display)
        tools_details_layout.addWidget(self.eraser_color_widget)
        self.eraser_color_widget.setVisible(False)
        self._eraser_color = QColor(255, 255, 255)
        
        # Shapes: dropdown to choose shape type (visible when Shapes tool is selected)
        self.shape_options_widget = QWidget()
        shape_options_layout = QHBoxLayout(self.shape_options_widget)
        shape_options_layout.addWidget(QLabel("Shape:"))
        self.shape_combo = QComboBox()
        for shape_id, label in SHAPE_OPTIONS:
            self.shape_combo.addItem(label, shape_id)
        self.shape_combo.setToolTip("Choose which shape to draw (Rectangle, Ellipse, etc.)")
        self.shape_combo.currentIndexChanged.connect(self._on_shape_combo_changed)
        shape_options_layout.addWidget(self.shape_combo)
        self.shape_options_widget.setVisible(False)
        shape_options_layout.addWidget(QLabel("Style:"))
        self.shape_style_combo = QComboBox()
        for style_id, label in SHAPE_STYLE_OPTIONS:
            self.shape_style_combo.addItem(label, style_id)
        self.shape_style_combo.currentIndexChanged.connect(self._on_shape_style_changed)
        shape_options_layout.addWidget(self.shape_style_combo)
        tools_details_layout.addWidget(self.shape_options_widget)
        # Shape outline/border thickness (visible when Shapes tool is selected)
        self.shape_outline_widget = QWidget()
        outline_layout = QHBoxLayout(self.shape_outline_widget)
        outline_layout.addWidget(QLabel("Border:"))
        self.shape_outline_spin = QSpinBox()
        self.shape_outline_spin.setRange(1, 50)
        self.shape_outline_spin.setValue(2)
        self.shape_outline_spin.setToolTip("Outline/border thickness for shapes (pixels)")
        self.shape_outline_spin.valueChanged.connect(self._on_shape_outline_changed)
        outline_layout.addWidget(self.shape_outline_spin)
        tools_details_layout.addWidget(self.shape_outline_widget)
        self.shape_outline_widget.setVisible(False)
        
        # Expandable tool description: one-line summary + "Details" for full help
        self.tool_detail_frame = QFrame()
        self.tool_detail_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        self.tool_detail_frame.setStyleSheet("QFrame { background-color: palette(midlight); border-radius: 4px; }")
        detail_layout = QVBoxLayout(self.tool_detail_frame)
        self.tool_summary_label = QLabel(TOOL_INFO["brush"][1])
        self.tool_summary_label.setWordWrap(True)
        self.tool_summary_label.setStyleSheet("font-size: 11px; color: palette(mid);")
        detail_layout.addWidget(self.tool_summary_label)
        self.details_btn = QPushButton("Details…")
        self.details_btn.setMaximumWidth(80)
        self.details_btn.clicked.connect(self._show_tool_details)
        detail_layout.addWidget(self.details_btn)
        tools_details_layout.addWidget(self.tool_detail_frame)
        
        # Paint bucket tolerance (shown when paint bucket is selected)
        self.paint_bucket_tolerance_widget = QWidget()
        pb_layout = QHBoxLayout(self.paint_bucket_tolerance_widget)
        pb_layout.addWidget(QLabel("Tolerance:"))
        self.paint_bucket_tolerance_spin = QSpinBox()
        self.paint_bucket_tolerance_spin.setRange(0, 255)
        self.paint_bucket_tolerance_spin.setValue(32)
        self.paint_bucket_tolerance_spin.setToolTip("Color similarity (0 = exact match, 255 = fill all)")
        self.paint_bucket_tolerance_spin.valueChanged.connect(self.paint_bucket_tolerance_changed.emit)
        pb_layout.addWidget(self.paint_bucket_tolerance_spin)
        tools_details_layout.addWidget(self.paint_bucket_tolerance_widget)
        self.paint_bucket_tolerance_widget.setVisible(False)
        
        # Brush size
        size_group = QGroupBox("Brush Size")
        size_layout = QVBoxLayout()
        
        size_control_layout = QHBoxLayout()
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setMinimum(1)
        self.size_slider.setMaximum(200)
        self.size_slider.setValue(10)
        self.size_slider.valueChanged.connect(self.on_size_changed)
        size_control_layout.addWidget(self.size_slider)
        
        self.size_spinbox = QSpinBox()
        self.size_spinbox.setMinimum(1)
        self.size_spinbox.setMaximum(200)
        self.size_spinbox.setValue(10)
        self.size_spinbox.valueChanged.connect(self.on_size_spinbox_changed)
        size_control_layout.addWidget(self.size_spinbox)
        
        size_layout.addLayout(size_control_layout)
        size_group.setLayout(size_layout)
        tools_details_layout.addWidget(size_group)
        
        # Brush opacity
        opacity_group = QGroupBox("Brush Opacity")
        opacity_layout = QVBoxLayout()
        
        self.brush_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.brush_opacity_slider.setMinimum(0)
        self.brush_opacity_slider.setMaximum(100)
        self.brush_opacity_slider.setValue(100)
        self.brush_opacity_slider.valueChanged.connect(self.on_brush_opacity_changed)
        opacity_layout.addWidget(self.brush_opacity_slider)
        
        self.brush_opacity_label = QLabel("100%")
        self.brush_opacity_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        opacity_layout.addWidget(self.brush_opacity_label)
        
        opacity_group.setLayout(opacity_layout)
        tools_details_layout.addWidget(opacity_group)
        
        # Color picker
        color_group = QGroupBox("Color")
        color_layout = QVBoxLayout()
        
        self.color_display = QLabel()
        self.color_display.setMinimumHeight(50)
        self.color_display.setStyleSheet(f"background-color: {self.current_color.name()}; border: 1px solid black;")
        color_layout.addWidget(self.color_display)
        
        self.color_btn = QPushButton("Choose Color")
        self.color_btn.clicked.connect(self.choose_color)
        color_layout.addWidget(self.color_btn)
        
        color_group.setLayout(color_layout)
        tools_details_layout.addWidget(color_group)
        
        # Color palette: 12 fixed slots. Left-click = use color; Right-click = set slot to current.
        palette_group = QGroupBox("Palette")
        palette_layout = QVBoxLayout()
        self.palette_colors: List[Optional[QColor]] = [None] * 12
        self.palette_swatches = []
        swatch_row = QHBoxLayout()
        swatch_size = 24
        for i in range(12):
            lbl = QLabel()
            lbl.setFixedSize(swatch_size, swatch_size)
            lbl.setStyleSheet("background-color: #333; border: 1px solid #555; border-radius: 3px;")
            lbl.setCursor(Qt.CursorShape.PointingHandCursor)
            lbl.setToolTip("Slot %d: Left-click = use color. Right-click = set to current. Alt+1–12 = use slot." % (i + 1))
            lbl.mousePressEvent = lambda e, idx=i: self._on_palette_swatch_clicked(e, idx)
            self.palette_swatches.append(lbl)
            swatch_row.addWidget(lbl)
        palette_layout.addLayout(swatch_row)
        palette_hint = QLabel(
            "Left-click: use color · Right-click: set slot to current · "
            "Alt+1–0: slots 1–10 · Ctrl+Alt+1/2: slots 11–12"
        )
        palette_hint.setStyleSheet("font-size: 11px; color: #888;")
        palette_layout.addWidget(palette_hint)
        palette_group.setLayout(palette_layout)
        tools_details_layout.addWidget(palette_group)
        
        tools_details_layout.addStretch()
        layout.addWidget(self.tools_details_widget)
        
        layout.addStretch()
        
        # Collapsed state: a narrow "tab" that pops out so the user can always click to expand
        self._tools_tab_width = 28
        self.tools_collapsed_bar = QWidget()
        self.tools_collapsed_bar.setFixedWidth(self._tools_tab_width)
        self.tools_collapsed_bar.setStyleSheet(
            "background-color: #404050; border: 1px solid #606070; border-left: none; "
            "border-radius: 0 6px 6px 0;"
        )
        bar_layout = QVBoxLayout(self.tools_collapsed_bar)
        bar_layout.setContentsMargins(2, 8, 2, 8)
        bar_layout.setSpacing(4)
        self.tools_expand_panel_btn = QPushButton(">>")
        self.tools_expand_panel_btn.setToolTip("Click to expand Tools panel")
        self.tools_expand_panel_btn.setFixedSize(22, 36)
        self.tools_expand_panel_btn.setStyleSheet(
            "font-weight: bold; font-size: 12px; border: none; background: transparent;"
        )
        self.tools_expand_panel_btn.clicked.connect(self._toggle_tools_panel_collapsed)
        bar_layout.addWidget(self.tools_expand_panel_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        bar_layout.addStretch()
        tab_label = QLabel("Tools")
        tab_label.setStyleSheet("font-size: 9px; color: #a0a0b0; border: none;")
        tab_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tab_label.setWordWrap(True)
        bar_layout.addWidget(tab_label, alignment=Qt.AlignmentFlag.AlignCenter)
        self.tools_collapsed_bar.hide()
        
        # Top-level: stacked or single layout with main + collapsed bar
        top_layout = QVBoxLayout(self)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addWidget(self.tools_main_widget)
        top_layout.addWidget(self.tools_collapsed_bar)
    
    def _toggle_tools_panel_collapsed(self):
        self._panel_collapsed = not self._panel_collapsed
        self.tools_main_widget.setVisible(not self._panel_collapsed)
        self.tools_collapsed_bar.setVisible(self._panel_collapsed)
        if self._panel_collapsed:
            self.setMinimumWidth(self._tools_tab_width)
            self.setMaximumWidth(self._tools_tab_width)
        else:
            self.setMinimumWidth(200)
            self.setMaximumWidth(500)
    
    def _toggle_tools_expanded(self):
        self._tools_expanded = not self._tools_expanded
        self.tools_details_widget.setVisible(self._tools_expanded)
        self.tools_expand_btn.setText("−" if self._tools_expanded else "+")
        self.tools_expand_btn.setToolTip("Condense panel" if self._tools_expanded else "Expand panel")
    
    def _on_shape_combo_changed(self):
        kind = self.shape_combo.currentData()
        if kind:
            self.shape_kind_changed.emit(kind)
    
    def _on_shape_style_changed(self):
        style = self.shape_style_combo.currentData()
        if style:
            self.shape_style_changed.emit(style)
    
    def _on_shape_outline_changed(self, value: int):
        self.shape_outline_width_changed.emit(value)
    
    def get_shape_outline_width(self) -> int:
        """Return current shape outline/border width in pixels (1–50)."""
        return self.shape_outline_spin.value()
    
    def _pick_eraser_color(self):
        c = QColorDialog.getColor(self._eraser_color, self, "Eraser color")
        if c.isValid():
            self._eraser_color = c
            self.eraser_color_display.setStyleSheet(f"background-color: {c.name()}; border: 1px solid black;")
            self.eraser_color_changed.emit(c)
    
    def _on_palette_swatch_clicked(self, event, index: int):
        """Left-click: use palette color. Right-click: set slot to current color."""
        try:
            if event is None or index < 0 or index >= 12:
                return
            if event.button() == Qt.MouseButton.RightButton:
                if not self.current_color.isValid():
                    return
                new_rgb = self.current_color.rgb()
                for j in range(12):
                    if j != index and self.palette_colors[j] is not None:
                        oc = self.palette_colors[j]
                        if oc.isValid() and oc.rgb() == new_rgb:
                            w = self.palette_swatches[index]
                            QToolTip.showText(
                                w.mapToGlobal(w.rect().center()),
                                "Color already in palette",
                                w,
                                2000,
                            )
                            return
                self.palette_colors[index] = QColor(self.current_color)
                self._refresh_palette_swatches()
                return
            if event.button() != Qt.MouseButton.LeftButton:
                return
            c = self.palette_colors[index]
            if c is not None and c.isValid():
                self.current_color = QColor(c)
                self.color_display.setStyleSheet(
                    "background-color: %s; border: 1px solid black;" % self.current_color.name()
                )
                self.color_changed.emit(self.current_color)
        except Exception:
            pass

    def set_brush_from_palette_index(self, index: int):
        """Set current brush color from palette slot (0–11). Used by Alt+1–12 shortcuts."""
        try:
            if 0 <= index < 12:
                c = self.palette_colors[index]
                if c is not None and c.isValid():
                    self.current_color = QColor(c)
                    self.color_display.setStyleSheet(
                        "background-color: %s; border: 1px solid black;"
                        % self.current_color.name()
                    )
                    self.color_changed.emit(self.current_color)
        except Exception:
            pass

    def _refresh_palette_swatches(self):
        """Update swatch labels to show palette colors."""
        for i in range(12):
            c = self.palette_colors[i]
            if c is not None and c.isValid():
                self.palette_swatches[i].setStyleSheet(
                    "background-color: %s; border: 1px solid #555; border-radius: 3px;" % c.name()
                )
            else:
                self.palette_swatches[i].setStyleSheet(
                    "background-color: #333; border: 1px solid #555; border-radius: 3px;"
                )
    
    def get_shape_kind(self) -> str:
        """Return current shape kind for the Shapes tool (e.g. 'rectangle', 'ellipse')."""
        data = self.shape_combo.currentData()
        return data if data else "rectangle"
    
    def _show_tool_details(self):
        """Show full tool description in a dialog."""
        title, detail = TOOL_INFO.get(self._current_tool, ("Tool", ""))
        QMessageBox.information(
            self,
            f"Tool: {title}",
            f"{title}\n\n{detail}",
        )
    
    def select_tool(self, tool: str):
        """Select a tool."""
        self._current_tool = tool
        self.brush_btn.setChecked(tool == "brush")
        self.eraser_btn.setChecked(tool == "eraser")
        self.transparency_btn.setChecked(tool == "transparency")
        self.eyedropper_btn.setChecked(tool == "eyedropper")
        self.paint_bucket_btn.setChecked(tool == "paint_bucket")
        self.shape_btn.setChecked(tool == "shape")
        self.zoom_btn.setChecked(tool == "zoom")
        self.crop_btn.setChecked(tool == "crop")
        self.paint_bucket_tolerance_widget.setVisible(tool == "paint_bucket")
        self.eraser_color_widget.setVisible(False)  # Eraser has no color option; it just erases
        self.shape_options_widget.setVisible(tool == "shape")
        self.shape_outline_widget.setVisible(tool == "shape")
        if tool == "paint_bucket":
            self.paint_bucket_tolerance_changed.emit(self.paint_bucket_tolerance_spin.value())
        if tool == "shape":
            self.shape_kind_changed.emit(self.get_shape_kind())
            self.shape_style_changed.emit(self.shape_style_combo.currentData() or "filled")
            self.shape_outline_width_changed.emit(self.get_shape_outline_width())
        self.tool_summary_label.setText(TOOL_INFO.get(tool, ("", ""))[1])
        self.tool_changed.emit(tool)
    
    def set_color(self, color: QColor):
        """Set current color (e.g. from eyedropper)."""
        if color.isValid():
            self.current_color = color
            self.color_display.setStyleSheet(f"background-color: {color.name()}; border: 1px solid black;")
            self.color_changed.emit(color)
    
    def on_size_changed(self, value: int):
        self.size_spinbox.setValue(value)
        self.brush_size_changed.emit(value)
    
    def on_size_spinbox_changed(self, value: int):
        self.size_slider.setValue(value)
        self.brush_size_changed.emit(value)
    
    def on_brush_opacity_changed(self, value: int):
        self.brush_opacity_label.setText(f"{value}%")
        self.brush_opacity_changed.emit(value)
    
    def _set_standard_colors_rainbow(self):
        """Set the color dialog standard colors (6x8 grid) in rainbow order with basics and variants.
        Row 0: red, orange, yellow, green, cyan, blue, purple, pink.
        Row 1: darker variants. Row 2: lighter variants. Row 3: medium (brown, navy, etc).
        Row 4: more hues. Row 5: white, grays, black.
        """
        # 48 colors: (r, g, b) – standard grid is 6 rows x 8 columns
        colors_rgb = [
            # Row 0 – vivid spectrum (left to right)
            (255, 0, 0), (255, 128, 0), (255, 255, 0), (0, 255, 0), (0, 255, 255),
            (0, 0, 255), (128, 0, 255), (255, 0, 255),
            # Row 1 – darker
            (180, 0, 0), (200, 80, 0), (180, 180, 0), (0, 160, 0), (0, 160, 160),
            (0, 0, 180), (80, 0, 160), (180, 0, 160),
            # Row 2 – lighter / pastel
            (255, 180, 180), (255, 210, 170), (255, 255, 180), (180, 255, 180),
            (180, 255, 255), (180, 200, 255), (210, 180, 255), (255, 180, 230),
            # Row 3 – medium (brown, navy, violet, etc.)
            (139, 0, 0), (160, 80, 40), (200, 150, 0), (34, 139, 34),
            (0, 128, 128), (0, 0, 128), (75, 0, 130), (200, 0, 128),
            # Row 4 – more distinct
            (128, 0, 0), (180, 90, 30), (210, 180, 140), (50, 205, 50),
            (0, 206, 209), (65, 105, 225), (138, 43, 226), (255, 105, 180),
            # Row 5 – neutrals: white → black
            (255, 255, 255), (220, 220, 220), (192, 192, 192), (128, 128, 128),
            (80, 80, 80), (50, 50, 50), (0, 0, 0), (101, 67, 33),
        ]
        for i, (r, g, b) in enumerate(colors_rgb):
            if i >= 48:
                break
            QColorDialog.setStandardColor(i, QColor(r, g, b))

    def _set_rainbow_custom_colors(self):
        """Set the color dialog custom colors to rainbow order: red top-left, down to black."""
        n = QColorDialog.customCount()
        for i in range(min(16, n)):
            if i < 8:
                hue = (i * 45) % 360
                c = QColor.fromHsv(hue, 255, 255)
            elif i < 15:
                hue = ((i - 8) * 45) % 360
                val = 255 - (i - 7) * 32
                val = max(0, min(255, val))
                c = QColor.fromHsv(hue, 255, val)
            else:
                c = QColor(0, 0, 0)
            QColorDialog.setCustomColor(i, c)

    def choose_color(self):
        """Open color picker with standard colors in rainbow order and custom colors."""
        self._set_standard_colors_rainbow()
        self._set_rainbow_custom_colors()
        opts = QColorDialog.ColorDialogOption.DontUseNativeDialog
        color = QColorDialog.getColor(
            self.current_color, self, "Choose Color", opts
        )
        if color.isValid():
            self.current_color = color
            self.color_display.setStyleSheet(
                "background-color: %s; border: 1px solid black;" % color.name()
            )
            self.color_changed.emit(color)


class HistoryPanel(QWidget):
    """Panel showing undo/redo history so the user can see what was done and what was undone."""

    def __init__(self, command_history, parent=None):
        super().__init__(parent)
        self.command_history = command_history
        layout = QVBoxLayout(self)
        title = QLabel("History")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)
        self.history_list = QListWidget()
        self.history_list.setToolTip(
            "Done = applied (can undo). Undone = reverted (can redo). Most recent at top."
        )
        layout.addWidget(self.history_list)
        self.refresh()
        try:
            self.command_history.history_changed.connect(self.refresh)
        except Exception:
            pass

    def refresh(self):
        """Rebuild list: Done (undo stack, newest first), then Undone (redo stack, next redo first)."""
        self.history_list.clear()
        u = self.command_history.undo_stack
        r = self.command_history.redo_stack
        if not u and not r:
            self.history_list.addItem("(no actions yet)")
            return
        # Section: Done (applied, can undo) – newest at top
        done_header = QListWidgetItem("Done (can undo)")
        done_header.setForeground(QBrush(QColor(160, 220, 160)))
        self.history_list.addItem(done_header)
        for cmd in reversed(u):
            self.history_list.addItem("  " + cmd.get_name())
        # Section: Undone (can redo) – next redo at top
        if r:
            self.history_list.addItem("")
            redo_header = QListWidgetItem("Undone (can redo)")
            redo_header.setForeground(QBrush(QColor(220, 200, 140)))
            self.history_list.addItem(redo_header)
            for cmd in reversed(r):
                self.history_list.addItem("  \u2933 " + cmd.get_name())
