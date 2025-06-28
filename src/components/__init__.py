"""
Components for Legal Document Transfer System
Các thành phần chính của hệ thống truyền tài liệu pháp lý
"""

# Import các components
try:
    from .sender import Sender
    from .receiver import Receiver
except ImportError:
    # Nếu import thất bại, không làm gì cả
    pass

__all__ = [
    'Sender',
    'Receiver'
]