"""
Logger Component
Hệ thống ghi log cho Legal Document Transfer System
Hỗ trợ: Console logging, File logging, với timestamp và log levels
"""

import os
import sys
import time
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path


class Logger:
    """
    Logger class cho hệ thống truyền tài liệu pháp lý
    Hỗ trợ ghi log ra console và file với nhiều levels
    """
    
    def __init__(self, name: str = "LegalDocTransfer", 
                 log_dir: str = "./logs",
                 log_level: str = "INFO",
                 enable_file_logging: bool = True,
                 enable_console_logging: bool = False,
                 max_file_size: int = 10 * 1024 * 1024,  # 10MB
                 backup_count: int = 5):
        """
        Khởi tạo Logger
        
        Args:
            name: Tên logger
            log_dir: Thư mục lưu log files
            log_level: Level của log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            enable_file_logging: Bật ghi log ra file
            enable_console_logging: Bật ghi log ra console
            max_file_size: Kích thước tối đa file log (bytes)
            backup_count: Số file backup tối đa
        """
        self.name = name
        self.log_dir = log_dir
        self.log_level = getattr(logging, log_level.upper())
        self.enable_file_logging = enable_file_logging
        self.enable_console_logging = enable_console_logging
        
        # Tạo thư mục log nếu chưa tồn tại
        if enable_file_logging:
            os.makedirs(log_dir, exist_ok=True)
        
        # Khởi tạo logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(self.log_level)
        
        self.logger.handlers.clear()

        self.formatter = self._create_formatter()
        
        if enable_console_logging:
            self._add_console_handler()
        
        if enable_file_logging:
            self._add_file_handler(max_file_size, backup_count)
        
        # Thống kê
        self.stats = {
            'debug_count': 0,
            'info_count': 0,
            'warning_count': 0,
            'error_count': 0,
            'critical_count': 0,
            'start_time': time.time()
        }
        
        # Log khởi tạo
        self.info(f"=== LOGGER KHỞI TẠO: {name} ===")
        self.info(f"Log directory: {os.path.abspath(log_dir)}")
        self.info(f"Log level: {log_level}")
        self.info(f"File logging: {enable_file_logging}")
        self.info(f"Console logging: {enable_console_logging}")

    def _create_formatter(self) -> logging.Formatter:
        """Tạo formatter cho log messages"""
        # Format: [2024-01-15 14:30:25.123] [INFO] [Sender_sender] Message
        format_string = (
            '[%(asctime)s] '
            '[%(levelname)s] '
            '[%(name)s] '
            '%(message)s'
        )
        return logging.Formatter(
            format_string,
            datefmt='%Y-%m-%d %H:%M:%S.%f'[:-3]
        )

    def _add_console_handler(self):
        """Thêm console handler"""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level)
        console_handler.setFormatter(self.formatter)
        self.logger.addHandler(console_handler)

    def _add_file_handler(self, max_file_size: int, backup_count: int):
        """Thêm file handler với rotation"""
        from logging.handlers import RotatingFileHandler
        
        # Tạo tên file log với timestamp
        timestamp = datetime.now().strftime("%Y%m%d")
        log_filename = f"{self.name}_{timestamp}.log"
        log_filepath = os.path.join(self.log_dir, log_filename)
        
        # Tạo rotating file handler
        file_handler = RotatingFileHandler(
            log_filepath,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(self.log_level)
        file_handler.setFormatter(self.formatter)
        self.logger.addHandler(file_handler)

    def _update_stats(self, level: str):
        """Cập nhật thống kê log"""
        if level == 'DEBUG':
            self.stats['debug_count'] += 1
        elif level == 'INFO':
            self.stats['info_count'] += 1
        elif level == 'WARNING':
            self.stats['warning_count'] += 1
        elif level == 'ERROR':
            self.stats['error_count'] += 1
        elif level == 'CRITICAL':
            self.stats['critical_count'] += 1

    def debug(self, message: str, **kwargs):
        """Ghi log DEBUG level"""
        self._update_stats('DEBUG')
        self.logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs):
        """Ghi log INFO level"""
        self._update_stats('INFO')
        self.logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Ghi log WARNING level"""
        self._update_stats('WARNING')
        self.logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs):
        """Ghi log ERROR level"""
        self._update_stats('ERROR')
        self.logger.error(message, **kwargs)

    def critical(self, message: str, **kwargs):
        """Ghi log CRITICAL level"""
        self._update_stats('CRITICAL')
        self.logger.critical(message, **kwargs)

    def log_transaction(self, transaction_id: str, action: str, 
                       details: Dict[str, Any] = None, status: str = "INFO"):
        """
        Ghi log cho giao dịch cụ thể
        
        Args:
            transaction_id: ID giao dịch
            action: Hành động (handshake, key_exchange, file_transfer, etc.)
            details: Chi tiết bổ sung
            status: Trạng thái (SUCCESS, FAILED, PENDING)
        """
        message = f"[TX:{transaction_id}] {action}"
        if details:
            details_str = ", ".join([f"{k}={v}" for k, v in details.items()])
            message += f" | {details_str}"
        
        if status == "SUCCESS":
            self.info(f"{message}")
        elif status == "FAILED":
            self.error(f"{message}")
        elif status == "PENDING":
            self.warning(f"{message}")
        else:
            self.info(message)

    def log_security_event(self, event_type: str, details: Dict[str, Any] = None):
        """
        Ghi log cho các sự kiện bảo mật
        
        Args:
            event_type: Loại sự kiện (encryption, decryption, signature_verify, etc.)
            details: Chi tiết sự kiện
        """
        message = f"[SECURITY] {event_type}"
        if details:
            details_str = ", ".join([f"{k}={v}" for k, v in details.items()])
            message += f" | {details_str}"
        
        self.info(message)

    def log_performance(self, operation: str, duration: float, 
                       data_size: int = None, throughput: float = None):
        """
        Ghi log hiệu suất
        
        Args:
            operation: Tên thao tác
            duration: Thời gian thực hiện (giây)
            data_size: Kích thước dữ liệu (bytes)
            throughput: Tốc độ truyền (bytes/s)
        """
        message = f"[PERF] {operation}: {duration:.3f}s"
        if data_size:
            message += f", Size: {data_size} bytes"
        if throughput:
            message += f", Throughput: {throughput:.2f} bytes/s"
        
        self.info(message)

    def log_network_event(self, event_type: str, host: str = None, 
                         port: int = None, details: Dict[str, Any] = None):
        """
        Ghi log cho các sự kiện mạng
        
        Args:
            event_type: Loại sự kiện (connect, disconnect, send, receive, etc.)
            host: Host address
            port: Port number
            details: Chi tiết bổ sung
        """
        message = f"[NETWORK] {event_type}"
        if host and port:
            message += f" | {host}:{port}"
        if details:
            details_str = ", ".join([f"{k}={v}" for k, v in details.items()])
            message += f" | {details_str}"
        
        self.info(message)

    def log_file_operation(self, operation: str, file_path: str, 
                          file_size: int = None, status: str = "SUCCESS"):
        """
        Ghi log cho các thao tác file
        
        Args:
            operation: Thao tác (read, write, encrypt, decrypt, etc.)
            file_path: Đường dẫn file
            file_size: Kích thước file (bytes)
            status: Trạng thái (SUCCESS, FAILED)
        """
        filename = os.path.basename(file_path)
        message = f"[FILE] {operation}: {filename}"
        if file_size:
            message += f" ({file_size} bytes)"
        
        if status == "SUCCESS":
            self.info(f"{message}")
        elif status == "FAILED":
            self.error(f"{message}")
        else:
            self.info(message)

    def get_statistics(self) -> Dict[str, Any]:
        """Lấy thống kê log"""
        runtime = time.time() - self.stats['start_time']
        total_logs = sum([
            self.stats['debug_count'],
            self.stats['info_count'],
            self.stats['warning_count'],
            self.stats['error_count'],
            self.stats['critical_count']
        ])
        
        return {
            **self.stats,
            'runtime_seconds': runtime,
            'total_logs': total_logs,
            'logs_per_second': total_logs / runtime if runtime > 0 else 0
        }

    def print_statistics(self):
        """In thống kê log ra console"""
        stats = self.get_statistics()
        self.info(f"=== LOG STATISTICS ===")
        self.info(f"Logger: {self.name}")
        self.info(f"Runtime: {stats['runtime_seconds']:.2f} seconds")
        self.info(f"Total logs: {stats['total_logs']}")
        self.info(f"Logs per second: {stats['logs_per_second']:.2f}")
        self.info(f"DEBUG: {stats['debug_count']}")
        self.info(f"INFO: {stats['info_count']}")
        self.info(f"WARNING: {stats['warning_count']}")
        self.info(f"ERROR: {stats['error_count']}")
        self.info(f"CRITICAL: {stats['critical_count']}")

    def cleanup(self):
        """Dọn dẹp logger"""
        self.info(f"=== LOGGER CLEANUP: {self.name} ===")
        self.print_statistics()
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)


# Factory function để tạo logger dễ dàng
def create_logger(name: str, **kwargs) -> Logger:
    """
    Factory function để tạo logger
    
    Args:
        name: Tên logger
        **kwargs: Các tham số khác cho Logger
        
    Returns:
        Logger instance
    """
    return Logger(name, **kwargs)


# Logger mặc định cho toàn bộ hệ thống
default_logger = create_logger("LegalDocTransfer")


if __name__ == "__main__":
    # Test logger
    logger = create_logger("TestLogger", log_level="DEBUG")
    
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    
    logger.log_transaction("tx_123", "handshake", {"status": "success"})
    logger.log_security_event("encryption", {"algorithm": "DES", "key_size": 64})
    logger.log_performance("file_encryption", 0.5, 1024, 2048)
    logger.log_network_event("connect", "localhost", 8001)
    logger.log_file_operation("read", "/path/to/file.txt", 1024)
    
    logger.print_statistics()
    logger.cleanup() 