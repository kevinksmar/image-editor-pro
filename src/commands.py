"""Command pattern implementation for undo/redo functionality.

This module provides:
- Command base class
- Specific command implementations for all operations
- CommandHistory manager for undo/redo stack
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from PIL import Image
from PyQt6.QtCore import QObject, pyqtSignal


class Command(ABC):
    """Abstract base class for all commands.
    
    Commands encapsulate actions that can be undone/redone.
    Each command must implement execute() and undo() methods.
    """
    
    @abstractmethod
    def execute(self):
        """Execute the command."""
        pass
    
    @abstractmethod
    def undo(self):
        """Undo the command."""
        pass
    
    def get_name(self) -> str:
        """Get command name for display.
        
        Returns:
            Human-readable command name
        """
        return self.__class__.__name__


class DrawCommand(Command):
    """Command for drawing operations (brush, eraser, transparency, shape, etc.)."""

    DISPLAY_NAMES = {
        "brush": "Brush",
        "eraser": "Eraser",
        "transparency": "Transparency",
        "shape": "Shape",
        "paint_bucket": "Paint bucket",
    }

    def __init__(
        self,
        project,
        layer_index: int,
        old_image: Image.Image,
        new_image: Image.Image,
        action_name: Optional[str] = None,
    ):
        """Initialize draw command.

        Args:
            project: Project instance
            layer_index: Index of layer being drawn on
            old_image: Layer image before drawing
            new_image: Layer image after drawing
            action_name: Display name for history (e.g. 'Brush', 'Eraser'). If None, uses 'Draw'.
        """
        self.project = project
        self.layer_index = layer_index
        self.old_image = old_image.copy()
        self.new_image = new_image.copy()
        self.action_name = action_name if action_name else "Draw"

    def execute(self):
        """Apply the drawing."""
        layer = self.project.get_layer(self.layer_index)
        if layer:
            layer.image = self.new_image.copy()
            self.project.layer_modified.emit(self.layer_index)

    def undo(self):
        """Revert the drawing."""
        layer = self.project.get_layer(self.layer_index)
        if layer:
            layer.image = self.old_image.copy()
            self.project.layer_modified.emit(self.layer_index)

    def get_name(self) -> str:
        return self.action_name


class AddLayerCommand(Command):
    """Command for adding a new layer."""
    
    def __init__(self, project, layer_name: str, fill_white: bool = False):
        """Initialize add layer command.
        
        Args:
            project: Project instance
            layer_name: Name for the new layer
            fill_white: Whether to fill with white
        """
        self.project = project
        self.layer_name = layer_name
        self.fill_white = fill_white
        self.layer_index = None
        self.layer = None
    
    def execute(self):
        """Add the layer."""
        self.layer = self.project.add_layer(self.layer_name, self.fill_white)
        self.layer_index = len(self.project.layers) - 1
    
    def undo(self):
        """Remove the layer."""
        if self.layer_index is not None:
            self.project.remove_layer(self.layer_index)
    
    def get_name(self) -> str:
        return "Add Layer"


class RemoveLayerCommand(Command):
    """Command for removing a layer."""
    
    def __init__(self, project, layer_index: int):
        """Initialize remove layer command.
        
        Args:
            project: Project instance
            layer_index: Index of layer to remove
        """
        self.project = project
        self.layer_index = layer_index
        self.layer = None
    
    def execute(self):
        """Remove the layer."""
        self.layer = self.project.get_layer(self.layer_index).copy()
        self.project.remove_layer(self.layer_index)
    
    def undo(self):
        """Restore the layer."""
        if self.layer:
            self.project.layers.insert(self.layer_index, self.layer)
            self.project.layers_changed.emit()
    
    def get_name(self) -> str:
        return "Remove Layer"


class MoveLayerCommand(Command):
    """Command for moving a layer."""
    
    def __init__(self, project, from_index: int, to_index: int):
        """Initialize move layer command.
        
        Args:
            project: Project instance
            from_index: Current layer index
            to_index: Target layer index
        """
        self.project = project
        self.from_index = from_index
        self.to_index = to_index
    
    def execute(self):
        """Move the layer."""
        self.project.move_layer(self.from_index, self.to_index)
    
    def undo(self):
        """Move the layer back."""
        self.project.move_layer(self.to_index, self.from_index)
    
    def get_name(self) -> str:
        return "Move Layer"


class SetLayerOpacityCommand(Command):
    """Command for changing layer opacity."""
    
    def __init__(self, project, layer_index: int, old_opacity: int, new_opacity: int):
        """Initialize opacity command.
        
        Args:
            project: Project instance
            layer_index: Index of layer
            old_opacity: Previous opacity value
            new_opacity: New opacity value
        """
        self.project = project
        self.layer_index = layer_index
        self.old_opacity = old_opacity
        self.new_opacity = new_opacity
    
    def execute(self):
        """Set new opacity."""
        self.project.set_layer_opacity(self.layer_index, self.new_opacity)
    
    def undo(self):
        """Restore old opacity."""
        self.project.set_layer_opacity(self.layer_index, self.old_opacity)
    
    def get_name(self) -> str:
        return "Change Opacity"


class SetLayerVisibilityCommand(Command):
    """Command for toggling layer visibility."""
    
    def __init__(self, project, layer_index: int):
        """Initialize visibility command.
        
        Args:
            project: Project instance
            layer_index: Index of layer
        """
        self.project = project
        self.layer_index = layer_index
        layer = project.get_layer(layer_index)
        self.old_visibility = layer.visible if layer else True
    
    def execute(self):
        """Toggle visibility."""
        layer = self.project.get_layer(self.layer_index)
        if layer:
            layer.visible = not self.old_visibility
            self.project.layer_modified.emit(self.layer_index)
    
    def undo(self):
        """Restore visibility."""
        layer = self.project.get_layer(self.layer_index)
        if layer:
            layer.visible = self.old_visibility
            self.project.layer_modified.emit(self.layer_index)
    
    def get_name(self) -> str:
        return "Toggle Visibility"


class FilterCommand(Command):
    """Command for applying image filters."""
    
    def __init__(self, project, layer_index: int, filter_name: str, old_image: Image.Image, new_image: Image.Image):
        """Initialize filter command.
        
        Args:
            project: Project instance
            layer_index: Index of layer
            filter_name: Name of applied filter
            old_image: Layer image before filter
            new_image: Layer image after filter
        """
        self.project = project
        self.layer_index = layer_index
        self.filter_name = filter_name
        self.old_image = old_image.copy()
        self.new_image = new_image.copy()
    
    def execute(self):
        """Apply the filter."""
        layer = self.project.get_layer(self.layer_index)
        if layer:
            layer.image = self.new_image.copy()
            self.project.layer_modified.emit(self.layer_index)
    
    def undo(self):
        """Revert the filter."""
        layer = self.project.get_layer(self.layer_index)
        if layer:
            layer.image = self.old_image.copy()
            self.project.layer_modified.emit(self.layer_index)
    
    def get_name(self) -> str:
        return f"Apply {self.filter_name}"


class RemoveLastFilterCommand(Command):
    """Command for reverting the last filter on a layer (per-layer filter history)."""
    
    def __init__(self, project, layer_index: int, image_before_restore: Image.Image, restored_image: Image.Image):
        """Initialize remove-last-filter command.
        
        Args:
            project: Project instance
            layer_index: Index of layer
            image_before_restore: Current image (before we revert)
            restored_image: Image to restore to (from layer's filter_history pop)
        """
        self.project = project
        self.layer_index = layer_index
        self.image_before_restore = image_before_restore.copy()
        self.restored_image = restored_image.copy()
    
    def execute(self):
        """Restore layer to state before last filter."""
        layer = self.project.get_layer(self.layer_index)
        if layer:
            layer.image = self.restored_image.copy()
            self.project.layer_modified.emit(self.layer_index)
    
    def undo(self):
        """Put the filtered image back."""
        layer = self.project.get_layer(self.layer_index)
        if layer:
            layer.image = self.image_before_restore.copy()
            layer.filter_history.append(self.image_before_restore.copy())
            self.project.layer_modified.emit(self.layer_index)
    
    def get_name(self) -> str:
        return "Remove last filter from layer"


class ResizeProjectCommand(Command):
    """Command for resizing the project canvas and all layers."""
    
    def __init__(self, project, new_width: int, new_height: int):
        self.project = project
        self.new_width = new_width
        self.new_height = new_height
        self.old_width = project.width
        self.old_height = project.height
        self.old_layer_images = [layer.image.copy() for layer in project.layers]
    
    def execute(self):
        self.project.width = self.new_width
        self.project.height = self.new_height
        for i, layer in enumerate(self.project.layers):
            layer.image = self.old_layer_images[i].copy().resize(
                (self.new_width, self.new_height),
                Image.Resampling.LANCZOS
            )
        self.project.layers_changed.emit()
    
    def undo(self):
        self.project.width = self.old_width
        self.project.height = self.old_height
        for i, layer in enumerate(self.project.layers):
            layer.image = self.old_layer_images[i].copy()
        self.project.layers_changed.emit()
    
    def get_name(self) -> str:
        return "Resize Image"


class ClearLayerCommand(Command):
    """Command for clearing the current layer to transparent."""
    
    def __init__(self, project, layer_index: int, old_image: Image.Image):
        self.project = project
        self.layer_index = layer_index
        self.old_image = old_image.copy()
    
    def execute(self):
        layer = self.project.get_layer(self.layer_index)
        if layer:
            w, h = layer.image.size
            layer.image = Image.new('RGBA', (w, h), (0, 0, 0, 0))
            self.project.layer_modified.emit(self.layer_index)
    
    def undo(self):
        layer = self.project.get_layer(self.layer_index)
        if layer:
            layer.image = self.old_image.copy()
            self.project.layer_modified.emit(self.layer_index)
    
    def get_name(self) -> str:
        return "Clear Layer"


class CropProjectCommand(Command):
    """Command for cropping the project and all layers to a rectangle."""
    
    def __init__(self, project, left: int, top: int, width: int, height: int):
        self.project = project
        self.left = left
        self.top = top
        self.crop_width = width
        self.crop_height = height
        self.old_width = project.width
        self.old_height = project.height
        self.old_layer_images = [layer.image.copy() for layer in project.layers]
    
    def execute(self):
        box = (self.left, self.top, self.left + self.crop_width, self.top + self.crop_height)
        self.project.width = self.crop_width
        self.project.height = self.crop_height
        for i, layer in enumerate(self.project.layers):
            layer.image = self.old_layer_images[i].crop(box).copy()
        self.project.layers_changed.emit()
    
    def undo(self):
        self.project.width = self.old_width
        self.project.height = self.old_height
        for i, layer in enumerate(self.project.layers):
            layer.image = self.old_layer_images[i].copy()
        self.project.layers_changed.emit()
    
    def get_name(self) -> str:
        return "Crop"


class FillLayerCommand(Command):
    """Command for filling the current layer with a color."""
    
    def __init__(self, project, layer_index: int, old_image: Image.Image, new_image: Image.Image):
        self.project = project
        self.layer_index = layer_index
        self.old_image = old_image.copy()
        self.new_image = new_image.copy()
    
    def execute(self):
        layer = self.project.get_layer(self.layer_index)
        if layer:
            layer.image = self.new_image.copy()
            self.project.layer_modified.emit(self.layer_index)
    
    def undo(self):
        layer = self.project.get_layer(self.layer_index)
        if layer:
            layer.image = self.old_image.copy()
            self.project.layer_modified.emit(self.layer_index)
    
    def get_name(self) -> str:
        return "Fill Layer"


class CanvasSizeCommand(Command):
    """Command for changing canvas size (expand or shrink) with anchor positioning."""
    
    def __init__(self, project, new_width: int, new_height: int, anchor_h: int, anchor_v: int):
        # anchor_h: 0=left, 1=center, 2=right; anchor_v: 0=top, 1=center, 2=bottom
        self.project = project
        self.new_width = new_width
        self.new_height = new_height
        self.anchor_h = anchor_h
        self.anchor_v = anchor_v
        self.old_width = project.width
        self.old_height = project.height
        self.old_layer_images = [layer.image.copy() for layer in project.layers]
    
    def execute(self):
        ow, oh = self.old_width, self.old_height
        nw, nh = self.new_width, self.new_height
        for i, layer in enumerate(self.project.layers):
            old_img = self.old_layer_images[i]
            new_img = Image.new('RGBA', (nw, nh), (0, 0, 0, 0))
            if nw >= ow and nh >= oh:
                # Expand: paste old at offset
                ox = [0, (nw - ow) // 2, nw - ow][self.anchor_h]
                oy = [0, (nh - oh) // 2, nh - oh][self.anchor_v]
                new_img.paste(old_img, (ox, oy))
            else:
                # Shrink: crop
                cx = [0, (ow - nw) // 2, ow - nw][self.anchor_h]
                cy = [0, (oh - nh) // 2, oh - nh][self.anchor_v]
                box = (cx, cy, cx + nw, cy + nh)
                new_img.paste(old_img.crop(box), (0, 0))
            layer.image = new_img
        self.project.width = nw
        self.project.height = nh
        self.project.layers_changed.emit()
    
    def undo(self):
        self.project.width = self.old_width
        self.project.height = self.old_height
        for i, layer in enumerate(self.project.layers):
            layer.image = self.old_layer_images[i].copy()
        self.project.layers_changed.emit()
    
    def get_name(self) -> str:
        return "Canvas Size"


class FlattenImageCommand(Command):
    """Command for flattening all layers into one."""
    
    def __init__(self, project):
        self.project = project
        self.old_layers = [layer.copy() for layer in project.layers]
        self.old_width = project.width
        self.old_height = project.height
    
    def execute(self):
        merged = self.project.render()
        self.project.layers.clear()
        self.project.add_layer("Background", image=merged)
        self.project.layers[0].name = "Flattened"
        self.project.layers_changed.emit()
    
    def undo(self):
        self.project.layers.clear()
        self.project.width = self.old_width
        self.project.height = self.old_height
        for L in self.old_layers:
            self.project.layers.append(L.copy())
        self.project.layers_changed.emit()
    
    def get_name(self) -> str:
        return "Flatten Image"


class CommandHistory(QObject):
    """Manages command history for undo/redo functionality.
    
    The CommandHistory maintains two stacks:
    - undo_stack: Commands that can be undone
    - redo_stack: Commands that can be redone
    
    Signals:
        history_changed: Emitted when undo/redo state changes
    """
    
    history_changed = pyqtSignal()
    
    def __init__(self, max_history: int = 50):
        """Initialize command history.
        
        Args:
            max_history: Maximum number of commands to keep in history
        """
        super().__init__()
        self.undo_stack: List[Command] = []
        self.redo_stack: List[Command] = []
        self.max_history = max_history
    
    def execute(self, command: Command):
        """Execute a command and add it to history.
        
        Args:
            command: Command to execute
        """
        command.execute()
        self.undo_stack.append(command)
        
        # Clear redo stack when new command is executed
        self.redo_stack.clear()
        
        # Limit history size
        if len(self.undo_stack) > self.max_history:
            self.undo_stack.pop(0)
        
        self.history_changed.emit()
    
    def undo(self):
        """Undo the last command."""
        if self.can_undo():
            command = self.undo_stack.pop()
            command.undo()
            self.redo_stack.append(command)
            self.history_changed.emit()
    
    def redo(self):
        """Redo the last undone command."""
        if self.can_redo():
            command = self.redo_stack.pop()
            command.execute()
            self.undo_stack.append(command)
            self.history_changed.emit()
    
    def can_undo(self) -> bool:
        """Check if undo is available.
        
        Returns:
            True if there are commands to undo
        """
        return len(self.undo_stack) > 0
    
    def can_redo(self) -> bool:
        """Check if redo is available.
        
        Returns:
            True if there are commands to redo
        """
        return len(self.redo_stack) > 0
    
    def clear(self):
        """Clear all history."""
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.history_changed.emit()
    
    def get_undo_text(self) -> Optional[str]:
        """Get text for undo action.
        
        Returns:
            Text describing what will be undone, or None
        """
        if self.can_undo():
            return f"Undo {self.undo_stack[-1].get_name()}"
        return None
    
    def get_redo_text(self) -> Optional[str]:
        """Get text for redo action.
        
        Returns:
            Text describing what will be redone, or None
        """
        if self.can_redo():
            return f"Redo {self.redo_stack[-1].get_name()}"
        return None
