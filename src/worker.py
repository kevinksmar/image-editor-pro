"""Background worker for heavy image operations (filters, etc.).

Runs filter processing in a QThread so the UI stays responsive.
"""

from PyQt6.QtCore import QObject, pyqtSignal
from PIL import Image

# Lazy import to avoid circular imports; filters are used only in worker thread
_filters_module = None


def _get_filters():
    global _filters_module
    if _filters_module is None:
        from filters import Filters
        _filters_module = Filters
    return _filters_module


class FilterWorker(QObject):
    """Worker that runs a single filter in a background thread.
    
    Pass a copy of the layer image and params; emits result_ready(new_image)
    or error_occurred(message). Must be used with moveToThread(thread).
    """
    run_requested = pyqtSignal(str, object, dict)  # filter_name, image, params
    result_ready = pyqtSignal(object)              # new PIL Image
    error_occurred = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.run_requested.connect(self._run_filter)
    
    def _run_filter(self, filter_name: str, image: Image.Image, params: dict):
        """Run the filter in the worker thread. Emit result or error."""
        try:
            Filters = _get_filters()
            if filter_name == "Blur":
                out = Filters.blur(image, **params)
            elif filter_name == "Sharpen":
                out = Filters.sharpen(image, **params)
            elif filter_name == "Brightness":
                out = Filters.adjust_brightness(image, **params)
            elif filter_name == "Contrast":
                out = Filters.adjust_contrast(image, **params)
            elif filter_name == "Hue/Saturation":
                out = Filters.adjust_hue_saturation(image, **params)
            elif filter_name == "Posterize":
                out = Filters.posterize(image, **params)
            elif filter_name == "Sepia":
                out = Filters.sepia(image)
            elif filter_name == "Grayscale":
                out = Filters.grayscale(image)
            elif filter_name == "Desaturate":
                out = Filters.desaturate(image)
            elif filter_name == "Invert":
                out = Filters.invert(image)
            elif filter_name == "Edge Detect":
                out = Filters.edge_detect(image)
            elif filter_name == "Emboss":
                out = Filters.emboss(image)
            elif filter_name == "Smooth":
                out = Filters.smooth(image)
            elif filter_name == "Detail":
                out = Filters.detail(image)
            else:
                self.error_occurred.emit(f"Unknown filter: {filter_name}")
                return
            self.result_ready.emit(out)
        except Exception as e:
            self.error_occurred.emit(str(e))
