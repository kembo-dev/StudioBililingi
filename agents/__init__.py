"""StudioBililingi agent layer.

Roles are stable. Vendors live behind backends.
"""

from .protocols import AudioBackend, ImageBackend, TextBackend, VideoBackend

__all__ = ["AudioBackend", "ImageBackend", "TextBackend", "VideoBackend"]
