"""
File Handler Component
Xử lý đọc/ghi file cho Legal Document Transfer System
Hỗ trợ: Binary files, text files, với validation và error handling
"""

import os
import hashlib
from typing import Optional, Union, Tuple
from pathlib import Path


class FileHandler:
    """
    File handler class cho hệ thống truyền tài liệu pháp lý
    Xử lý đọc/ghi file với validation và error handling
    """
    
    def __init__(self, chunk_size: int = 8192):
        """
        Khởi tạo FileHandler
        
        Args:
            chunk_size: Kích thước chunk khi đọc file lớn (bytes)
        """
        self.chunk_size = chunk_size

    def read_file(self, file_path: str) -> Optional[bytes]:
        """
        Đọc file và trả về nội dung dưới dạng bytes
        
        Args:
            file_path: Đường dẫn file cần đọc
            
        Returns:
            bytes: Nội dung file, None nếu lỗi
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File không tồn tại: {file_path}")
            
            if not os.path.isfile(file_path):
                raise ValueError(f"Đường dẫn không phải file: {file_path}")
            
            # Kiểm tra quyền đọc
            if not os.access(file_path, os.R_OK):
                raise PermissionError(f"Không có quyền đọc file: {file_path}")
            
            # Đọc file
            with open(file_path, 'rb') as file:
                content = file.read()
            
            return content
            
        except Exception as e:
            print(f"Lỗi đọc file {file_path}: {e}")
            return None

    def read_file_chunked(self, file_path: str) -> Optional[bytes]:
        """
        Đọc file theo chunks (cho file lớn)
        
        Args:
            file_path: Đường dẫn file cần đọc
            
        Returns:
            bytes: Nội dung file, None nếu lỗi
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File không tồn tại: {file_path}")
            
            content = b''
            with open(file_path, 'rb') as file:
                while True:
                    chunk = file.read(self.chunk_size)
                    if not chunk:
                        break
                    content += chunk
            
            return content
            
        except Exception as e:
            print(f"Lỗi đọc file {file_path}: {e}")
            return None

    def write_file(self, file_path: str, content: Union[bytes, str]) -> bool:
        """
        Ghi nội dung vào file
        
        Args:
            file_path: Đường dẫn file cần ghi
            content: Nội dung cần ghi (bytes hoặc str)
            
        Returns:
            bool: True nếu ghi thành công
        """
        try:
            # Tạo thư mục nếu chưa tồn tại
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            # Chuyển content thành bytes nếu cần
            if isinstance(content, str):
                content = content.encode('utf-8')
            
            # Ghi file
            with open(file_path, 'wb') as file:
                file.write(content)
            
            return True
            
        except Exception as e:
            print(f"Lỗi ghi file {file_path}: {e}")
            return False

    def write_file_chunked(self, file_path: str, content: bytes) -> bool:
        """
        Ghi file theo chunks (cho file lớn)
        
        Args:
            file_path: Đường dẫn file cần ghi
            content: Nội dung cần ghi (bytes)
            
        Returns:
            bool: True nếu ghi thành công
        """
        try:
            # Tạo thư mục nếu chưa tồn tại
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            with open(file_path, 'wb') as file:
                for i in range(0, len(content), self.chunk_size):
                    chunk = content[i:i + self.chunk_size]
                    file.write(chunk)
            
            return True
            
        except Exception as e:
            print(f"Lỗi ghi file {file_path}: {e}")
            return False

    def get_file_info(self, file_path: str) -> Optional[dict]:
        """
        Lấy thông tin file
        
        Args:
            file_path: Đường dẫn file
            
        Returns:
            dict: Thông tin file, None nếu lỗi
        """
        try:
            if not os.path.exists(file_path):
                return None
            
            stat = os.stat(file_path)
            
            return {
                'size': stat.st_size,
                'created': stat.st_ctime,
                'modified': stat.st_mtime,
                'accessed': stat.st_atime,
                'is_file': os.path.isfile(file_path),
                'is_dir': os.path.isdir(file_path),
                'readable': os.access(file_path, os.R_OK),
                'writable': os.access(file_path, os.W_OK),
                'executable': os.access(file_path, os.X_OK)
            }
            
        except Exception as e:
            print(f"Lỗi lấy thông tin file {file_path}: {e}")
            return None

    def calculate_file_hash(self, file_path: str, algorithm: str = 'sha256') -> Optional[str]:
        """
        Tính hash của file
        
        Args:
            file_path: Đường dẫn file
            algorithm: Thuật toán hash (md5, sha1, sha256, sha512)
            
        Returns:
            str: Hash của file, None nếu lỗi
        """
        try:
            if not os.path.exists(file_path):
                return None
            
            hash_func = getattr(hashlib, algorithm.lower())()
            
            with open(file_path, 'rb') as file:
                for chunk in iter(lambda: file.read(self.chunk_size), b''):
                    hash_func.update(chunk)
            
            return hash_func.hexdigest()
            
        except Exception as e:
            print(f"Lỗi tính hash file {file_path}: {e}")
            return None

    def copy_file(self, src_path: str, dst_path: str) -> bool:
        """
        Copy file
        
        Args:
            src_path: Đường dẫn file nguồn
            dst_path: Đường dẫn file đích
            
        Returns:
            bool: True nếu copy thành công
        """
        try:
            if not os.path.exists(src_path):
                raise FileNotFoundError(f"File nguồn không tồn tại: {src_path}")
            
            # Tạo thư mục đích nếu chưa tồn tại
            directory = os.path.dirname(dst_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            # Copy file
            with open(src_path, 'rb') as src_file:
                with open(dst_path, 'wb') as dst_file:
                    while True:
                        chunk = src_file.read(self.chunk_size)
                        if not chunk:
                            break
                        dst_file.write(chunk)
            
            return True
            
        except Exception as e:
            print(f"Lỗi copy file {src_path} -> {dst_path}: {e}")
            return False

    def delete_file(self, file_path: str) -> bool:
        """
        Xóa file
        
        Args:
            file_path: Đường dẫn file cần xóa
            
        Returns:
            bool: True nếu xóa thành công
        """
        try:
            if not os.path.exists(file_path):
                return True
            
            os.remove(file_path)
            return True
            
        except Exception as e:
            print(f"Lỗi xóa file {file_path}: {e}")
            return False

    def list_files(self, directory: str, pattern: str = "*") -> list:
        """
        Liệt kê files trong thư mục
        
        Args:
            directory: Đường dẫn thư mục
            pattern: Pattern để lọc files (ví dụ: "*.txt")
            
        Returns:
            list: Danh sách files
        """
        try:
            if not os.path.exists(directory):
                return []
            
            if not os.path.isdir(directory):
                return []
            
            files = []
            for file_path in Path(directory).glob(pattern):
                if file_path.is_file():
                    files.append(str(file_path))
            
            return files
            
        except Exception as e:
            print(f"Lỗi liệt kê files trong {directory}: {e}")
            return []

    def validate_file(self, file_path: str, max_size: int = None) -> Tuple[bool, str]:
        """
        Validate file
        
        Args:
            file_path: Đường dẫn file
            max_size: Kích thước tối đa cho phép (bytes)
            
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        try:
            if not os.path.exists(file_path):
                return False, "File không tồn tại"
            
            if not os.path.isfile(file_path):
                return False, "Đường dẫn không phải file"
            
            if not os.access(file_path, os.R_OK):
                return False, "Không có quyền đọc file"
            
            if max_size is not None:
                file_size = os.path.getsize(file_path)
                if file_size > max_size:
                    return False, f"File quá lớn ({file_size} > {max_size} bytes)"
            
            return True, "File hợp lệ"
            
        except Exception as e:
            return False, f"Lỗi validate file: {e}"


# Factory function
def create_file_handler(chunk_size: int = 8192) -> FileHandler:
    """
    Factory function để tạo FileHandler
    
    Args:
        chunk_size: Kích thước chunk
        
    Returns:
        FileHandler instance
    """
    return FileHandler(chunk_size)
