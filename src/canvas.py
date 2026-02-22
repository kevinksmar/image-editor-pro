"""Canvas widget for displaying and interacting with the image.

This module provides the main canvas where users can view and edit images.
"""

import numpy as np
from PIL import Image, ImageDraw
from PyQt6.QtWidgets import QWidget, QScrollArea
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QRect
from PyQt6.QtGui import QPainter, QPixmap, QImage, QPen, QColor, QCursor, QWheelEvent, QBrush


class Canvas(QWidget):
    """Canvas widget for drawing and displaying the project.
    
    The canvas handles:
    - Displaying the composited image from all layers
    - Mouse interaction for drawing tools
    - Zoom and pan
    
    Signals:
        drawing_completed: Emitted when a drawing stroke is completed
    """
    
    drawing_completed = pyqtSignal(object, object, int)  # old_image, new_image, layer_index
    cursor_position_changed = pyqtSignal(int, int)  # canvas x, y (-1,-1 when left)
    color_sampled = pyqtSignal(QColor)
    
    def __init__(self, project, parent=None):
        """Initialize the canvas.
        
        Args:
            project: Project instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.project = project
        self.zoom_level = 1.0
        self.offset_x = 0
        self.offset_y = 0
        
        # Active layer for drawing (set by main window from layer panel selection)
        self.active_layer_index = 0
        
        # Drawing state
        self.is_drawing = False
        self.last_point = None
        self.current_tool = "brush"  # brush, eraser, transparency, eyedropper, paint_bucket, shape
        self.shape_kind = "rectangle"
        self.shape_style = "filled"  # filled, outline, transparent_fill, transparent_outline
        self.brush_size = 10
        self.brush_opacity = 100
        self.brush_color = QColor(0, 0, 0, 255)
        self.eraser_color = QColor(255, 255, 255, 255)
        self.paint_bucket_tolerance = 32
        
        # Store image before drawing for undo
        self.image_before_draw = None
        # Shape tools: start point of drag
        self.shape_start_point = None
        
        # How to show transparency: "checkerboard", "white", "gray", "black"
        self.transparency_display = "checkerboard"
        
        # Eyedropper zoom bubble: cursor position in widget coords (-1 when not over canvas)
        self._picker_cursor_wx = -1
        self._picker_cursor_wy = -1
        
        # Set up widget
        self.setMouseTracking(True)
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        self.update_size()
        
        # Connect signals
        self.project.layers_changed.connect(self.on_project_changed)
        self.project.layer_modified.connect(self.on_project_changed)
    
    def update_size(self):
        """Update widget size based on project dimensions and zoom."""
        width = int(self.project.width * self.zoom_level)
        height = int(self.project.height * self.zoom_level)
        self.setMinimumSize(width, height)
        self.setMaximumSize(width, height)
        self.update()
    
    def on_project_changed(self):
        """Handle project changes."""
        self.update()
    
    def set_zoom(self, zoom_level: float):
        """Set zoom level.
        
        Args:
            zoom_level: Zoom level (1.0 = 100%)
        """
        self.zoom_level = max(0.1, min(10.0, zoom_level))
        self.update_size()
    
    def set_tool(self, tool: str):
        """Set current drawing tool.
        
        Args:
            tool: Tool name ("brush" or "eraser")
        """
        self.current_tool = tool
    
    def set_brush_size(self, size: int):
        """Set brush size.
        
        Args:
            size: Brush size in pixels
        """
        self.brush_size = max(1, min(200, size))
    
    def set_brush_opacity(self, opacity: int):
        """Set brush opacity.
        
        Args:
            opacity: Opacity (0-100)
        """
        self.brush_opacity = max(0, min(100, opacity))
    
    def set_brush_color(self, color: QColor):
        """Set brush color.
        
        Args:
            color: QColor object
        """
        self.brush_color = color
    
    def set_paint_bucket_tolerance(self, tolerance: int):
        """Set paint bucket color tolerance (0-255)."""
        self.paint_bucket_tolerance = max(0, min(255, tolerance))
    
    def set_shape_kind(self, kind: str):
        """Set which shape to draw when using the Shapes tool."""
        allowed = ("rectangle", "ellipse", "line", "rounded_rect")
        self.shape_kind = kind if kind in allowed else "rectangle"
    
    def set_shape_style(self, style: str):
        """Set shape style: filled, outline, transparent_fill, transparent_outline."""
        allowed = ("filled", "outline", "transparent_fill", "transparent_outline")
        self.shape_style = style if style in allowed else "filled"
    
    def set_eraser_color(self, color: QColor):
        """Set color the eraser paints with (e.g. white to 'erase' to paper)."""
        if color.isValid():
            self.eraser_color = color
    
    def set_active_layer_index(self, index: int):
        """Set which layer drawing applies to.
        
        Args:
            index: Layer index in project.layers
        """
        if 0 <= index < len(self.project.layers):
            self.active_layer_index = index
    
    def set_transparency_display(self, mode: str):
        """Set how transparency is shown behind the image.
        
        Args:
            mode: One of "checkerboard", "white", "gray", "black"
        """
        if mode in ("checkerboard", "white", "gray", "black"):
            self.transparency_display = mode
            self.update()
    
    def paintEvent(self, event):
        """Paint the canvas."""
        painter = QPainter(self)
        width = int(self.project.width * self.zoom_level)
        height = int(self.project.height * self.zoom_level)
        
        # Background for transparency (checkerboard or solid)
        if self.transparency_display == "checkerboard":
            checker_size = 12
            for y in range(0, height, checker_size):
                for x in range(0, width, checker_size):
                    light = ((x // checker_size) + (y // checker_size)) % 2 == 0
                    painter.fillRect(x, y, checker_size, checker_size,
                                     QColor(220, 220, 220) if light else QColor(180, 180, 180))
        else:
            color = {
                "white": QColor(255, 255, 255),
                "gray": QColor(128, 128, 128),
                "black": QColor(0, 0, 0),
            }.get(self.transparency_display, QColor(220, 220, 220))
            painter.fillRect(0, 0, width, height, color)
        
        # Render the project
        try:
            rendered_image = self.project.render()
            
            # Convert PIL image to QPixmap
            img_array = np.array(rendered_image)
            h, w, channel = img_array.shape
            bytes_per_line = channel * w
            q_image = QImage(img_array.data, w, h, bytes_per_line, QImage.Format.Format_RGBA8888)
            pixmap = QPixmap.fromImage(q_image)
            
            # Apply zoom
            if self.zoom_level != 1.0:
                pixmap = pixmap.scaled(
                    width, height,
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            
            # Draw the image
            painter.drawPixmap(0, 0, pixmap)
            
            # Eyedropper zoom bubble: zoomed pixel view next to cursor
            if self.current_tool == "eyedropper" and self._picker_cursor_wx >= 0 and self._picker_cursor_wy >= 0:
                self._draw_eyedropper_bubble(painter, rendered_image, width, height)
            
        except Exception as e:
            print(f"Error rendering canvas: {e}")
    
    def _draw_eyedropper_bubble(self, painter: QPainter, rendered_image: Image.Image, canvas_w: int, canvas_h: int):
        """Draw a zoom bubble next to the cursor showing pixels for precise eyedropper picking."""
        bubble_size = 96
        source_size = 11
        cx = int(self._picker_cursor_wx / self.zoom_level)
        cy = int(self._picker_cursor_wy / self.zoom_level)
        half = source_size // 2
        x1 = max(0, cx - half)
        y1 = max(0, cy - half)
        x2 = min(rendered_image.width, x1 + source_size)
        y2 = min(rendered_image.height, y1 + source_size)
        if x2 <= x1 or y2 <= y1:
            return
        crop = rendered_image.crop((x1, y1, x2, y2))
        zoomed = crop.resize((bubble_size, bubble_size), Image.Resampling.NEAREST)
        arr = np.array(zoomed, dtype=np.uint8, copy=True)
        if arr.ndim >= 3:
            h, w = arr.shape[:2]
            bytes_per_line = arr.shape[2] * w
            qimg = QImage(arr.data, w, h, bytes_per_line, QImage.Format.Format_RGBA8888)
            bubble_pix = QPixmap.fromImage(qimg.copy())
        else:
            return
        offset_x = 24
        offset_y = -bubble_size - 12
        bx = self._picker_cursor_wx + offset_x
        by = self._picker_cursor_wy + offset_y
        if bx + bubble_size > canvas_w:
            bx = self._picker_cursor_wx - bubble_size - offset_x
        if by < 0:
            by = self._picker_cursor_wy + 20
        if bx < 0:
            bx = 0
        if by + bubble_size > canvas_h:
            by = canvas_h - bubble_size
        rect = QRect(int(bx), int(by), bubble_size, bubble_size)
        painter.setPen(QPen(QColor(60, 60, 60), 2))
        painter.setBrush(QBrush(QColor(40, 40, 40)))
        painter.drawRoundedRect(rect.adjusted(-2, -2, 2, 2), 6, 6)
        painter.drawPixmap(rect, bubble_pix)
        # Grid so each pixel boundary is visible
        painter.setPen(QPen(QColor(80, 80, 80), 1))
        for i in range(1, source_size):
            px = int(bx + i * bubble_size / source_size)
            painter.drawLine(px, int(by), px, int(by + bubble_size))
            py = int(by + i * bubble_size / source_size)
            painter.drawLine(int(bx), py, int(bx + bubble_size), py)
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        center_x = bx + bubble_size // 2
        center_y = by + bubble_size // 2
        cross = 4
        painter.drawLine(int(center_x - cross), int(center_y), int(center_x + cross), int(center_y))
        painter.drawLine(int(center_x), int(center_y - cross), int(center_x), int(center_y + cross))
        painter.setPen(QPen(QColor(0, 0, 0), 1))
        painter.drawLine(int(center_x - cross - 1), int(center_y), int(center_x + cross + 1), int(center_y))
        painter.drawLine(int(center_x), int(center_y - cross - 1), int(center_x), int(center_y + cross + 1))
    
    def mousePressEvent(self, event):
        """Handle mouse press."""
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pt = self._get_canvas_point(event.position().toPoint())
        # Emit cursor position
        self.cursor_position_changed.emit(pt.x(), pt.y())
        
        if self.current_tool == "eyedropper":
            self._sample_color(pt.x(), pt.y())
            return
        
        if self.current_tool == "paint_bucket":
            active_layer = self.project.get_layer(self.active_layer_index)
            if active_layer and 0 <= pt.x() < self.project.width and 0 <= pt.y() < self.project.height:
                old_image = active_layer.image.copy()
                new_image = self._flood_fill(old_image, pt.x(), pt.y())
                if new_image is not None:
                    active_layer.image = new_image
                    self.project.layer_modified.emit(self.active_layer_index)
                    self.drawing_completed.emit(old_image, new_image, self.active_layer_index)
                return
        
        if self.current_tool == "transparency":
            active_layer = self.project.get_layer(self.active_layer_index)
            if active_layer:
                self.image_before_draw = active_layer.image.copy()
                self.is_drawing = True
                self.last_point = pt
                self._draw_line(active_layer, pt, pt)
                self.update()
            return
        if self.current_tool == "shape":
            active_layer = self.project.get_layer(self.active_layer_index)
            if active_layer:
                self.image_before_draw = active_layer.image.copy()
                self.shape_start_point = pt
                self.is_drawing = True
            return
        
        active_layer = self.project.get_layer(self.active_layer_index)
        if active_layer:
            self.image_before_draw = active_layer.image.copy()
            self.is_drawing = True
            self.last_point = pt
            # Draw a dot on press so a single click (no drag) still draws
            self._draw_line(active_layer, pt, pt)
            self.update()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move."""
        pt_widget = event.position().toPoint()
        pt = self._get_canvas_point(pt_widget)
        self.cursor_position_changed.emit(pt.x(), pt.y())
        if self.current_tool == "eyedropper":
            self._picker_cursor_wx = int(pt_widget.x())
            self._picker_cursor_wy = int(pt_widget.y())
            self.update()
        
        if self.is_drawing and self.shape_start_point and self.current_tool == "shape":
            self.update()
            return
        if self.is_drawing and self.last_point:
            active_layer = self.project.get_layer(self.active_layer_index)
            if active_layer:
                self._draw_line(active_layer, self.last_point, pt)
                self.last_point = pt
                self.update()
    
    def leaveEvent(self, event):
        """Clear cursor position when leaving canvas."""
        self.cursor_position_changed.emit(-1, -1)
        self._picker_cursor_wx = -1
        self._picker_cursor_wy = -1
        if self.current_tool == "eyedropper":
            self.update()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release."""
        if event.button() != Qt.MouseButton.LeftButton:
            if self.is_drawing:
                self.is_drawing = False
                self.shape_start_point = None
                self.last_point = None
                active_layer = self.project.get_layer(self.active_layer_index)
                if active_layer and self.image_before_draw:
                    active_layer.image = self.image_before_draw.copy()
                    self.project.layer_modified.emit(self.active_layer_index)
                self.image_before_draw = None
            return
        if not self.is_drawing:
            return
        pt = self._get_canvas_point(event.position().toPoint())
        active_layer = self.project.get_layer(self.active_layer_index)
        if self.shape_start_point and active_layer and self.image_before_draw and self.current_tool == "shape":
            self._draw_shape(active_layer, self.shape_start_point, pt)
            self.drawing_completed.emit(
                self.image_before_draw,
                active_layer.image.copy(),
                self.active_layer_index
            )
            self.shape_start_point = None
        elif active_layer and self.image_before_draw:
            self.drawing_completed.emit(
                self.image_before_draw,
                active_layer.image.copy(),
                self.active_layer_index
            )
        self.is_drawing = False
        self.image_before_draw = None
        self.last_point = None
    
    def _draw_shape(self, layer, start: QPoint, end: QPoint):
        """Draw shape on layer; supports filled, outline, and transparent variants."""
        draw = ImageDraw.Draw(layer.image, "RGBA")
        alpha = int(255 * self.brush_opacity / 100)
        color = (
            self.brush_color.red(),
            self.brush_color.green(),
            self.brush_color.blue(),
            alpha,
        )
        transparent = (0, 0, 0, 0)
        width = max(1, self.brush_size)
        style = self.shape_style
        use_fill = style in ("filled", "transparent_fill")
        use_outline = style in ("outline", "transparent_outline")
        if not use_fill and not use_outline:
            use_fill = True
        fill_color = transparent if style == "transparent_fill" else color
        outline_color = transparent if style == "transparent_outline" else color
        x1, y1 = start.x(), start.y()
        x2, y2 = end.x(), end.y()
        box = [min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)]
        w = box[2] - box[0]
        h = box[3] - box[1]
        if self.shape_kind == "line":
            line_color = transparent if style == "transparent_outline" else color
            draw.line([x1, y1, x2, y2], fill=line_color, width=width)
        elif self.shape_kind == "rectangle":
            if use_outline:
                draw.rectangle(box, fill=None, outline=outline_color, width=width)
            if use_fill:
                draw.rectangle(box, fill=fill_color)
        elif self.shape_kind == "ellipse":
            if use_outline:
                draw.ellipse(box, fill=None, outline=outline_color, width=width)
            if use_fill:
                draw.ellipse(box, fill=fill_color)
        elif self.shape_kind == "rounded_rect":
            radius = min(w, h) // 4 if (w and h) else 0
            if hasattr(draw, "rounded_rectangle"):
                if use_outline:
                    draw.rounded_rectangle(box, radius=radius, fill=None, outline=outline_color, width=width)
                if use_fill:
                    draw.rounded_rectangle(box, radius=radius, fill=fill_color)
            else:
                if use_outline:
                    draw.rectangle(box, fill=None, outline=outline_color, width=width)
                if use_fill:
                    draw.rectangle(box, fill=fill_color)
        else:
            draw.rectangle(box, fill=fill_color)
    
    def _get_canvas_point(self, widget_point: QPoint) -> QPoint:
        """Convert widget coordinates to canvas coordinates.
        
        Args:
            widget_point: Point in widget coordinates
            
        Returns:
            Point in canvas coordinates
        """
        x = int(widget_point.x() / self.zoom_level)
        y = int(widget_point.y() / self.zoom_level)
        return QPoint(x, y)
    
    def _draw_line(self, layer, start: QPoint, end: QPoint):
        """Draw a line on the layer.
        
        Args:
            layer: Layer to draw on
            start: Start point
            end: End point
        """
        # Create ImageDraw object
        draw = ImageDraw.Draw(layer.image, 'RGBA')
        
        # Prepare color based on tool
        alpha = int(255 * self.brush_opacity / 100)
        if self.current_tool == "eraser":
            color = (
                self.eraser_color.red(),
                self.eraser_color.green(),
                self.eraser_color.blue(),
                alpha,
            )
        elif self.current_tool == "transparency":
            color = (0, 0, 0, 0)
        else:
            color = (
                self.brush_color.red(),
                self.brush_color.green(),
                self.brush_color.blue(),
                alpha,
            )
        
        # Draw line
        draw.line(
            [start.x(), start.y(), end.x(), end.y()],
            fill=color,
            width=self.brush_size
        )
        
        # Draw circle at end point for smoother strokes
        radius = self.brush_size // 2
        draw.ellipse(
            [
                end.x() - radius,
                end.y() - radius,
                end.x() + radius,
                end.y() + radius
            ],
            fill=color
        )
    
    def _flood_fill(self, image: Image.Image, x: int, y: int) -> Image.Image | None:
        """Fill contiguous area at (x,y) with brush color. Returns new image or None."""
        arr = np.array(image)
        if arr.ndim != 3 or arr.shape[2] < 4:
            return None
        h, w = arr.shape[:2]
        if not (0 <= x < w and 0 <= y < h):
            return None
        target = tuple(int(arr[y, x, c]) for c in range(4))
        tol = self.paint_bucket_tolerance
        fill_r = self.brush_color.red()
        fill_g = self.brush_color.green()
        fill_b = self.brush_color.blue()
        fill_a = int(255 * self.brush_opacity / 100)
        fill = (fill_r, fill_g, fill_b, fill_a)
        if all(abs(target[c] - fill[c]) <= tol for c in range(4)):
            return None
        out = arr.copy()
        stack = [(x, y)]
        visited = np.zeros((h, w), dtype=bool)
        while stack:
            cx, cy = stack.pop()
            if not (0 <= cx < w and 0 <= cy < h) or visited[cy, cx]:
                continue
            if not all(abs(int(out[cy, cx, c]) - target[c]) <= tol for c in range(4)):
                continue
            visited[cy, cx] = True
            out[cy, cx, 0], out[cy, cx, 1] = fill_r, fill_g
            out[cy, cx, 2], out[cy, cx, 3] = fill_b, fill_a
            stack.append((cx + 1, cy))
            stack.append((cx - 1, cy))
            stack.append((cx, cy + 1))
            stack.append((cx, cy - 1))
        return Image.fromarray(out)
    
    def _sample_color(self, x: int, y: int):
        """Sample color from composited image at (x, y) and set as brush color."""
        if not (0 <= x < self.project.width and 0 <= y < self.project.height):
            return
        rendered = self.project.render()
        img_array = np.array(rendered)
        r, g, b, a = img_array[y, x]
        self.brush_color = QColor(int(r), int(g), int(b), int(a))
        self.color_sampled.emit(self.brush_color)


class CanvasScrollArea(QScrollArea):
    """Scroll area for the canvas. Supports Ctrl+wheel zoom."""
    
    zoom_changed = pyqtSignal()
    
    def __init__(self, canvas: Canvas, parent=None):
        """Initialize the scroll area.
        
        Args:
            canvas: Canvas widget
            parent: Parent widget
        """
        super().__init__(parent)
        self.canvas = canvas
        self.setWidget(canvas)
        self.setWidgetResizable(False)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    def wheelEvent(self, event: QWheelEvent):
        """Zoom with Ctrl+wheel; otherwise scroll."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            elif delta < 0:
                self.zoom_out()
            self.zoom_changed.emit()
            event.accept()
        else:
            super().wheelEvent(event)
    
    def zoom_in(self):
        """Zoom in."""
        self.canvas.set_zoom(self.canvas.zoom_level * 1.2)
    
    def zoom_out(self):
        """Zoom out."""
        self.canvas.set_zoom(self.canvas.zoom_level / 1.2)
    
    def zoom_reset(self):
        """Reset zoom to 100%."""
        self.canvas.set_zoom(1.0)
    
    def zoom_fit_to_window(self):
        """Set zoom so the entire image fits in the viewport."""
        viewport = self.viewport()
        if viewport and self.canvas.project:
            w = self.canvas.project.width
            h = self.canvas.project.height
            vw = viewport.width()
            vh = viewport.height()
            if w > 0 and h > 0 and vw > 0 and vh > 0:
                scale = min(vw / w, vh / h)
                scale = max(0.1, min(10.0, scale))
                self.canvas.set_zoom(scale)
    
    def zoom_actual_size(self):
        """Same as zoom_reset (100%)."""
        self.zoom_reset()
