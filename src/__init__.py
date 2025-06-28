"""
Legal Document Transfer System
Hệ thống truyền tài liệu pháp lý an toàn qua hai server trung gian

Package này chứa các thành phần chính:
- core: Xử lý mã hóa, socket, logging
- components: Sender và Receiver components  
- utils: File handling, validation utilities
"""

__version__ = "1.0.0"
__author__ = "Legal Document Transfer Team"
__description__ = "Secure legal document transfer system with intermediate servers"

# Import các module chính để dễ dàng truy cập
try:
    from .core.crypto_handler import CryptoHandler
    from .core.socket_handler import ClientSocketHandler, ServerSocketHandler, MessageTypes
    from .core.logger import Logger
    from .components.sender import Sender
    from .components.receiver import Receiver
    from .utils.file_handler import FileHandler
    from .utils.validation import MessageValidator
except ImportError:
    # Nếu import thất bại, không làm gì cả
    pass

# Định nghĩa những gì được export khi import *
__all__ = [
    'CryptoHandler',
    'ClientSocketHandler', 
    'ServerSocketHandler',
    'MessageTypes',
    'Logger',
    'Sender',
    'Receiver', 
    'FileHandler',
    'MessageValidator'
]