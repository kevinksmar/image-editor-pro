"""Core data models for the Image Editor Pro application.

This module contains the fundamental data structures:
- Layer: Represents a single layer with image data, opacity, visibility
- Project: Manages multiple layers and canvas properties
"""

import json
import base64
from io import BytesIO
from typing import List, Tuple, Optional
from PIL import Image
import numpy as np
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import QObject, pyqtSignal


class Layer:
    """Represents a single layer in the image editor.
    
    A layer contains:
    - Image data (PIL Image)
    - Name
    - Visibility flag
    - Opacity (0-100)
    - Position in layer stack
    
    Attributes:
        name (str): Layer name
        image (Image.Image): PIL Image object containing layer data
        visible (bool): Whether the layer is visible
        opacity (int): Layer opacity (0-100)
    """
    
    def __init__(self, name: str, width: int, height: int, image: Optional[Image.Image] = None):
        """Initialize a new layer.
        
        Args:
            name: Layer name
            width: Layer width in pixels
            height: Layer height in pixels
            image: Optional PIL Image to use. If None, creates transparent layer
        """
        self.name = name
        self.visible = True
        self.opacity = 100
        # Per-layer history of images before each filter (for "Remove last filter from layer")
        self.filter_history: List[Image.Image] = []
        
        if image is not None:
            # Use provided image, ensure it's RGBA
            self.image = image.convert('RGBA')
        else:
            # Create transparent layer
            self.image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    
    def get_size(self) -> Tuple[int, int]:
        """Get layer dimensions.
        
        Returns:
            Tuple of (width, height)
        """
        return self.image.size
    
    def resize(self, width: int, height: int):
        """Resize the layer.
        
        Args:
            width: New width
            height: New height
        """
        self.image = self.image.resize((width, height), Image.Resampling.LANCZOS)
    
    def get_thumbnail(self, size: Tuple[int, int] = (64, 64)) -> QPixmap:
        """Generate a thumbnail for the layer.
        
        Args:
            size: Thumbnail size (width, height)
            
        Returns:
            QPixmap thumbnail
        """
        # Create thumbnail
        thumb = self.image.copy()
        thumb.thumbnail(size, Image.Resampling.LANCZOS)
        
        # Convert to QPixmap
        return self._pil_to_qpixmap(thumb)
    
    def _pil_to_qpixmap(self, pil_image: Image.Image) -> QPixmap:
        """Convert PIL Image to QPixmap.
        
        Args:
            pil_image: PIL Image object
            
        Returns:
            QPixmap object
        """
        # Convert PIL image to bytes
        img_array = np.array(pil_image)
        height, width, channel = img_array.shape
        bytes_per_line = channel * width
        
        # Create QImage
        q_image = QImage(img_array.data, width, height, bytes_per_line, QImage.Format.Format_RGBA8888)
        
        return QPixmap.fromImage(q_image)
    
    def copy(self) -> 'Layer':
        """Create a deep copy of this layer.
        
        Returns:
            New Layer instance with copied data
        """
        new_layer = Layer(self.name, *self.get_size(), self.image.copy())
        new_layer.visible = self.visible
        new_layer.opacity = self.opacity
        # filter_history not copied; new layer starts with empty filter history
        return new_layer
    
    def to_dict(self) -> dict:
        """Serialize layer to dictionary for saving.
        
        Returns:
            Dictionary representation of layer
        """
        # Convert image to base64
        buffer = BytesIO()
        self.image.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return {
            'name': self.name,
            'visible': self.visible,
            'opacity': self.opacity,
            'image': img_str,
            'size': self.get_size()
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'Layer':
        """Deserialize layer from dictionary.
        
        Args:
            data: Dictionary containing layer data
            
        Returns:
            Layer instance
        """
        # Decode base64 image
        img_data = base64.b64decode(data['image'])
        image = Image.open(BytesIO(img_data))
        
        # Create layer
        layer = Layer(data['name'], *data['size'], image)
        layer.visible = data['visible']
        layer.opacity = data['opacity']
        
        return layer


class Project(QObject):
    """Manages the entire project including all layers and canvas properties.
    
    The Project class handles:
    - Layer management (add, remove, reorder)
    - Canvas dimensions
    - Project metadata
    - Rendering the final composited image
    
    Signals:
        layers_changed: Emitted when layers are added, removed, or reordered
        layer_modified: Emitted when a layer's properties change
    """
    
    layers_changed = pyqtSignal()
    layer_modified = pyqtSignal(int)  # layer index
    
    def __init__(self, width: int = 800, height: int = 600, initial_background_white: bool = True):
        """Initialize a new project.
        
        Args:
            width: Canvas width in pixels
            height: Canvas height in pixels
            initial_background_white: If True, first layer is white; if False, transparent
        """
        super().__init__()
        self.width = width
        self.height = height
        self.layers: List[Layer] = []
        self.file_path: Optional[str] = None
        
        # Create initial background layer
        self.add_layer("Background", fill_white=initial_background_white)
    
    def add_layer(self, name: str = "New Layer", fill_white: bool = False, image: Optional[Image.Image] = None) -> Layer:
        """Add a new layer to the project.
        
        Args:
            name: Layer name
            fill_white: If True, fill with white; otherwise transparent
            image: Optional PIL Image to use for the layer
            
        Returns:
            The created Layer object
        """
        if image is not None:
            # Resize image to canvas size if needed
            if image.size != (self.width, self.height):
                image = image.resize((self.width, self.height), Image.Resampling.LANCZOS)
            layer = Layer(name, self.width, self.height, image)
        else:
            layer = Layer(name, self.width, self.height)
            if fill_white:
                layer.image = Image.new('RGBA', (self.width, self.height), (255, 255, 255, 255))
        
        self.layers.append(layer)
        self.layers_changed.emit()
        return layer
    
    def remove_layer(self, index: int):
        """Remove a layer from the project.
        
        Args:
            index: Index of layer to remove
        """
        if 0 <= index < len(self.layers):
            self.layers.pop(index)
            self.layers_changed.emit()
    
    def move_layer(self, from_index: int, to_index: int):
        """Move a layer to a different position.
        
        Args:
            from_index: Current layer index
            to_index: Target layer index
        """
        if 0 <= from_index < len(self.layers) and 0 <= to_index < len(self.layers):
            layer = self.layers.pop(from_index)
            self.layers.insert(to_index, layer)
            self.layers_changed.emit()
    
    def get_layer(self, index: int) -> Optional[Layer]:
        """Get a layer by index.
        
        Args:
            index: Layer index
            
        Returns:
            Layer object or None if index is invalid
        """
        if 0 <= index < len(self.layers):
            return self.layers[index]
        return None
    
    def set_layer_opacity(self, index: int, opacity: int):
        """Set layer opacity.
        
        Args:
            index: Layer index
            opacity: Opacity value (0-100)
        """
        layer = self.get_layer(index)
        if layer:
            layer.opacity = max(0, min(100, opacity))
            self.layer_modified.emit(index)
    
    def set_layer_visibility(self, index: int, visible: bool):
        """Set layer visibility.
        
        Args:
            index: Layer index
            visible: Visibility flag
        """
        layer = self.get_layer(index)
        if layer:
            layer.visible = visible
            self.layer_modified.emit(index)
    
    def render(self) -> Image.Image:
        """Render all visible layers into a single composite image.
        
        Returns:
            PIL Image with all layers composited
        """
        # Create base image
        result = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        
        # Composite layers from bottom to top
        for layer in self.layers:
            if not layer.visible:
                continue
            
            # Apply opacity
            if layer.opacity < 100:
                layer_img = layer.image.copy()
                # Adjust alpha channel
                alpha = layer_img.split()[3]
                alpha = alpha.point(lambda p: int(p * layer.opacity / 100))
                layer_img.putalpha(alpha)
            else:
                layer_img = layer.image
            
            # Composite
            result = Image.alpha_composite(result, layer_img)
        
        return result
    
    def render_below(self, layer_index: int) -> Image.Image:
        """Render the composite of all layers below the given index (what would show through).
        
        Used by the eraser to "remove paint" by replacing pixels with the color that would
        be visible if the current layer were transparent at that point. Uses white as the
        canvas background so erasing never becomes black.
        
        Args:
            layer_index: Current layer index; layers 0..layer_index-1 are composited.
            
        Returns:
            PIL RGBA image of the same size as the project.
        """
        # White background so transparent areas and "nothing below" restore to white, not black
        result = Image.new('RGBA', (self.width, self.height), (255, 255, 255, 255))
        for i in range(0, layer_index):
            layer = self.layers[i]
            if not layer.visible:
                continue
            if layer.opacity < 100:
                layer_img = layer.image.copy()
                alpha = layer_img.split()[3]
                alpha = alpha.point(lambda p: int(p * layer.opacity / 100))
                layer_img.putalpha(alpha)
            else:
                layer_img = layer.image
            result = Image.alpha_composite(result, layer_img)
        return result
    
    def to_dict(self) -> dict:
        """Serialize project to dictionary for saving.
        
        Returns:
            Dictionary representation of project
        """
        return {
            'version': '1.0',
            'width': self.width,
            'height': self.height,
            'layers': [layer.to_dict() for layer in self.layers]
        }
    
    def save_project(self, file_path: str):
        """Save project to .iep file (Image Editor Pro format).
        
        Args:
            file_path: Path to save the project
            
        Raises:
            PermissionError: If the file cannot be written (e.g. read-only or in use).
            OSError: For other write failures (disk full, path invalid).
        """
        data = self.to_dict()
        with open(file_path, 'w') as f:
            json.dump(data, f)
        self.file_path = file_path
    
    @staticmethod
    def load_project(file_path: str) -> 'Project':
        """Load project from .iep file.
        
        Args:
            file_path: Path to the project file
            
        Returns:
            Project instance
            
        Raises:
            FileNotFoundError: If the file does not exist.
            PermissionError: If the file cannot be read.
            json.JSONDecodeError: If the file is not valid JSON (corrupted).
            (KeyError, TypeError): If the file structure is invalid.
        """
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Validate required structure
        if not isinstance(data, dict) or 'width' not in data or 'height' not in data or 'layers' not in data:
            raise ValueError("Invalid project file: missing width, height, or layers.")
        
        # Create project
        project = Project(data['width'], data['height'])
        project.layers = []  # Clear default layer
        
        # Load layers
        for layer_data in data['layers']:
            layer = Layer.from_dict(layer_data)
            project.layers.append(layer)
        
        project.file_path = file_path
        project.layers_changed.emit()
        
        return project
