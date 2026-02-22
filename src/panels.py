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
    QMessageBox, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QBrush


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
        "Paint over with the eraser color (e.g. white) so drawn content is covered. Set eraser color below.",
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
        
        self.setup_ui()
        self.refresh_layers()
        
        # Connect signals
        self.project.layers_changed.connect(self.refresh_layers)
        self.project.layer_modified.connect(self.on_layer_modified)
    
    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Layers")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)
        
        # Layer list
        self.layer_list = QListWidget()
        self.layer_list.setIconSize(QSize(64, 64))
        self.layer_list.currentRowChanged.connect(self.on_layer_selected)
        self.layer_list.itemDoubleClicked.connect(self.on_layer_double_clicked)
        layout.addWidget(self.layer_list)
        
        # Layer controls
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
        
        layout.addLayout(controls_layout)
        
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
        layout.addWidget(opacity_group)
        
        # Visibility checkbox
        self.visibility_check = QCheckBox("Visible")
        self.visibility_check.setChecked(True)
        self.visibility_check.stateChanged.connect(self.on_visibility_toggled)
        layout.addWidget(self.visibility_check)
        
        layout.addStretch()
    
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
    eraser_color_changed = pyqtSignal(QColor)
    
    def __init__(self, parent=None):
        """Initialize the tool options panel.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.current_color = QColor(0, 0, 0, 255)
        self._current_tool = "brush"
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Tools")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)
        
        # Tool buttons (icons only for compact layout; light icons on dark grey background)
        tool_group = QGroupBox("Tool")
        tool_group.setStyleSheet(
            "QGroupBox QPushButton { background-color: #505050; border: 1px solid #404040; border-radius: 3px; } "
            "QGroupBox QPushButton:hover { background-color: #5a5a5a; } "
            "QGroupBox QPushButton:checked { background-color: #606060; border-color: #707070; }"
        )
        tool_layout = QHBoxLayout()
        icon_size = 28
        for tool_id, (title, _) in TOOL_INFO.items():
            btn = QPushButton()
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
            else:
                self.shape_btn = btn
        tool_group.setLayout(tool_layout)
        layout.addWidget(tool_group)
        
        # Eraser color (visible when Eraser is selected)
        self.eraser_color_widget = QWidget()
        eraser_layout = QHBoxLayout(self.eraser_color_widget)
        eraser_layout.addWidget(QLabel("Eraser color:"))
        self.eraser_color_display = QLabel()
        self.eraser_color_display.setMinimumHeight(24)
        self.eraser_color_display.setStyleSheet("background-color: rgb(255,255,255); border: 1px solid black;")
        self.eraser_color_display.mousePressEvent = lambda e: self._pick_eraser_color()
        eraser_layout.addWidget(self.eraser_color_display)
        layout.addWidget(self.eraser_color_widget)
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
        layout.addWidget(self.shape_options_widget)
        self.shape_options_widget.setVisible(False)
        shape_options_layout.addWidget(QLabel("Style:"))
        self.shape_style_combo = QComboBox()
        for style_id, label in SHAPE_STYLE_OPTIONS:
            self.shape_style_combo.addItem(label, style_id)
        self.shape_style_combo.currentIndexChanged.connect(self._on_shape_style_changed)
        shape_options_layout.addWidget(self.shape_style_combo)
        
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
        layout.addWidget(self.tool_detail_frame)
        
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
        layout.addWidget(self.paint_bucket_tolerance_widget)
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
        layout.addWidget(size_group)
        
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
        layout.addWidget(opacity_group)
        
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
        layout.addWidget(color_group)
        
        layout.addStretch()
    
    def _on_shape_combo_changed(self):
        kind = self.shape_combo.currentData()
        if kind:
            self.shape_kind_changed.emit(kind)
    
    def _on_shape_style_changed(self):
        style = self.shape_style_combo.currentData()
        if style:
            self.shape_style_changed.emit(style)
    
    def _pick_eraser_color(self):
        c = QColorDialog.getColor(self._eraser_color, self, "Eraser color")
        if c.isValid():
            self._eraser_color = c
            self.eraser_color_display.setStyleSheet(f"background-color: {c.name()}; border: 1px solid black;")
            self.eraser_color_changed.emit(c)
    
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
        self.paint_bucket_tolerance_widget.setVisible(tool == "paint_bucket")
        self.eraser_color_widget.setVisible(tool == "eraser")
        self.shape_options_widget.setVisible(tool == "shape")
        if tool == "paint_bucket":
            self.paint_bucket_tolerance_changed.emit(self.paint_bucket_tolerance_spin.value())
        if tool == "eraser":
            self.eraser_color_changed.emit(self._eraser_color)
        if tool == "shape":
            self.shape_kind_changed.emit(self.get_shape_kind())
            self.shape_style_changed.emit(self.shape_style_combo.currentData() or "filled")
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
    
    def choose_color(self):
        """Open color picker dialog."""
        color = QColorDialog.getColor(self.current_color, self, "Choose Color")
        if color.isValid():
            self.current_color = color
            self.color_display.setStyleSheet(f"background-color: {color.name()}; border: 1px solid black;")
            self.color_changed.emit(color)


class HistoryPanel(QWidget):
    """Panel showing undo history (list of command names)."""
    
    def __init__(self, command_history, parent=None):
        super().__init__(parent)
        self.command_history = command_history
        layout = QVBoxLayout(self)
        title = QLabel("History")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)
        self.history_list = QListWidget()
        self.history_list.setToolTip("List of undo steps (most recent at top)")
        layout.addWidget(self.history_list)
        self.refresh()
        try:
            self.command_history.history_changed.connect(self.refresh)
        except Exception:
            pass
    
    def refresh(self):
        """Rebuild list from undo stack (newest first)."""
        self.history_list.clear()
        for cmd in reversed(self.command_history.undo_stack):
            self.history_list.addItem(cmd.get_name())
