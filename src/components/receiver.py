"""
Receiver Component  
Thực hiện việc nhận tài liệu pháp lý qua hai server trung gian tuần tự
Bao gồm: Handshake → Key Exchange → Receive & Decrypt → Send ACK/NACK
"""

import os
import time
import base64
from typing import Dict, Any, Optional, Tuple
from src.core.crypto_handler import CryptoHandler
from src.core.socket_handler import ServerSocketHandler, MessageTypes, create_message, ClientSocketHandler
from src.core.logger import Logger
from src.utils.file_handler import FileHandler
from src.utils.validation import MessageValidator


class Receiver:
    """
    Người nhận tài liệu pháp lý
    Thực hiện luồng: Handshake → Key Exchange → Receive & Decrypt → Send ACK/NACK
    """
    
    def __init__(self, host: str = '0.0.0.0', port: int = 8000,
                 receiver_id: str = 'receiver', output_dir: str = './data/output',
                 timeout: int = 30, log_callback=None, on_new_file=None):
        """
        Khởi tạo Receiver
        
        Args:
            host: IP của Server 2 (server trung gian thứ hai)
            port: Port của Server 2
            receiver_id: ID của receiver
            output_dir: Thư mục lưu file nhận được
            timeout: Timeout cho các thao tác
            log_callback: Callback function for logging
            on_new_file: Callback function for handling new file
        """
        self.receiver_id = receiver_id
        self.output_dir = output_dir
        self.timeout = timeout
        self.log_callback = log_callback
        self.on_new_file = on_new_file
        self.logger = Logger(
            name="receiver",
            log_dir="./logs",
            log_level="INFO",
            enable_console_logging=False
        )
        
        # Tạo thư mục output nếu chưa tồn tại
        os.makedirs(output_dir, exist_ok=True)
        
        # ServerSocketHandler để lắng nghe kết nối từ Server2
        self.socket_handler = ServerSocketHandler(host, port, timeout, logger_name="receiver_socket")
        
        self.crypto = CryptoHandler(logger=self.logger)
        self.file_handler = FileHandler()
        self.validator = MessageValidator()
        
        
        self.private_key, self.public_key = self.crypto.generate_rsa_keypair()
        
        # Trạng thái
        self.is_running = False
        self.session_key = None
        self.current_transaction_id = None
        
        # Thống kê
        self.stats = {
            'handshake_time': 0,
            'key_exchange_time': 0,
            'decryption_time': 0,
            'verification_time': 0,
            'total_time': 0,
            'received_file_size': 0,
            'decrypted_size': 0,
            'files_received': 0,
            'files_rejected': 0,
            'messages_received': 0,
            'errors': 0
        }

    def _log(self, level, msg):
        if self.log_callback:
            self.log_callback(level, msg)
        else:
            if level == "info":
                self.logger.info(msg)
            else:
                self.logger.error(msg)

    def start_receiver(self):
        """
        Khởi động receiver
        Kết nối đến server và bắt đầu lắng nghe
        """
        self._log("info", f"=== KHỞI ĐỘNG RECEIVER: {self.receiver_id} ===")
        
        try:
            if not self.socket_handler.start_server(message_callback=self._handle_message):
                self._log("error", "Không thể khởi động server socket")
                return False
            self.is_running = True
            self._log("info", "Receiver đang lắng nghe kết nối từ Server2...")
            while self.is_running:
                time.sleep(1)
            return True
        except Exception as e:
            self._log("error", f"Lỗi khởi động receiver: {e}")
            return False
        finally:
            self.socket_handler.stop_server()
            self._log("info", "Receiver đã dừng")

    def _handle_message(self, message: Dict[str, Any], client_id: str) -> Optional[Any]:
        try:
            self.stats['messages_received'] += 1
            self._log("info", f"Nhận từ {client_id}: {message.get('type', 'UNKNOWN')}")
            # Validate message structure
            is_valid, error = self.validator.validate_message_structure(message)
            if not is_valid:
                self._log("error", f"Message structure không hợp lệ: {error}")
                return None

            msg_type = message.get('type')
            transaction_id = message.get('transaction_id')

            # Handle HELLO message
            if msg_type == MessageTypes.HELLO:
                start_time = time.time()
                # Validate HELLO message
                is_valid, error = self.validator.validate_hello_message(message)
                if not is_valid:
                    self._log("error", f"HELLO message không hợp lệ: {error}")
                    return None

                # Create READY response
                ready_message = create_message(
                    MessageTypes.READY,
                    data={
                        'message': 'Ready!',
                        'receiver_id': self.receiver_id
                    },
                    source=self.receiver_id,
                    destination=message.get('source'),
                    transaction_id=transaction_id
                )
                self.stats['handshake_time'] = time.time() - start_time
                self._log("info", f"Gửi READY đến {message.get('source')}")
                return ready_message

            # Handle GET_PUBLIC_KEY message
            elif msg_type == "GET_PUBLIC_KEY":
                public_key_pem = self.crypto.export_key_to_pem(self.public_key)
                public_key_message = create_message(
                    MessageTypes.PUBLIC_KEY,
                    data={'public_key': public_key_pem},
                    source=self.receiver_id,
                    destination=message.get('source'),
                    transaction_id=transaction_id
                )
                self._log("info", f"Gửi PUBLIC_KEY đến {message.get('source')}")
                return public_key_message
            
            elif msg_type == MessageTypes.FILE_DATA:
                # Validate file data message
                is_valid, error = self.validator.validate_file_data_message(message)
                if not is_valid:
                    self._log("error", f"FILE_DATA message không hợp lệ: {error}")
                    nack_message = create_message(
                        MessageTypes.NACK,
                        data={'error': error},
                        source=self.receiver_id,
                        destination=message.get('source'),
                        transaction_id=transaction_id
                    )
                    return nack_message

                # Extract file packet
                file_packet = message.get('data', {})
                try:
                    # Lấy public key của sender từ metadata
                    metadata = file_packet.get('metadata', {})
                    public_key_sender_pem = metadata.get('public_key_sender')
                    signature = file_packet.get('sig')

                    if not public_key_sender_pem:
                        self._log("error", "Không nhận được public key của sender trong metadata")
                        nack_message = create_message(
                            MessageTypes.NACK,
                            data={'error': 'Thiếu public key của sender trong metadata'},
                            source=self.receiver_id,
                            destination=message.get('source'),
                            transaction_id=transaction_id
                        )
                        return nack_message

                    sender_public_key = self.crypto.import_key_from_pem(public_key_sender_pem)

                    self._log("info", "Bắt đầu kiểm tra hash và chữ ký số của gói tin...")

                    # 1. Kiểm tra chữ ký số
                    if not self.crypto.verify_signature(metadata, signature, sender_public_key):
                        self._log("error", "Chữ ký số không hợp lệ!")
                        nack_message = create_message(
                            MessageTypes.NACK,
                            data={'error': 'File không hợp lệ: Sai chữ ký số!'},
                            source=self.receiver_id,
                            destination=message.get('source'),
                            transaction_id=transaction_id
                        )
                        return nack_message

                    # 2. Kiểm tra hash toàn vẹn
                    iv = base64.b64decode(file_packet['iv'])
                    cipher = base64.b64decode(file_packet['cipher'])
                    if not self.crypto.verify_file_integrity(iv, cipher, file_packet['hash']):
                        self._log("error", "Hash toàn vẹn không hợp lệ!")
                        nack_message = create_message(
                            MessageTypes.NACK,
                            data={'error': 'File không hợp lệ: Sai hash toàn vẹn!'},
                            source=self.receiver_id,
                            destination=message.get('source'),
                            transaction_id=transaction_id
                        )
                        return nack_message

                    # 3. Giải mã file
                    file_data = self.crypto.decrypt_file_des(cipher, self.session_key, iv)
                    filename = metadata['filename']
                    output_path = os.path.join(self.output_dir, filename)
                    with open(output_path, "wb") as f:
                        f.write(file_data)
                    self._log("info", f"Đã lưu file giải mã: {output_path}")
                    ack_message = create_message(
                        MessageTypes.ACK,
                        data={'message': 'File received and verified successfully!'},
                        source=self.receiver_id,
                        destination=message.get('source'),
                        transaction_id=transaction_id
                    )
                    self._log("info", "Đã gửi ACK cho FILE_DATA")
                    if self.on_new_file:
                        self.on_new_file()
                    return ack_message
                except Exception as e:
                    nack_message = create_message(
                        MessageTypes.NACK,
                        data={'error': str(e)},
                        source=self.receiver_id,
                        destination=message.get('source'),
                        transaction_id=transaction_id
                    )
                    self._log("error", f"Lỗi xử lý FILE_DATA: {e}")
                    return nack_message

            elif msg_type == MessageTypes.SESSION_KEY:
                encrypted_session_key_b64 = message['data']['encrypted_session_key']
                encrypted_session_key = base64.b64decode(encrypted_session_key_b64)
                self.session_key = self.crypto.decrypt_session_key(encrypted_session_key, self.private_key)
                self._log("info", "Đã nhận và giải mã session key")
                return None

            return None

        except Exception as e:
            self._log("error", f"Lỗi xử lý message: {e}")
            self.stats['errors'] += 1
            return None

    def _log_statistics(self):
        """Ghi log thống kê hiệu suất"""
        self._log("info", "=== THỐNG KÊ HIỆU SUẤT ===")
        self._log("info", f"Handshake time: {self.stats['handshake_time']:.3f}s")
        self._log("info", f"Key exchange time: {self.stats['key_exchange_time']:.3f}s")
        self._log("info", f"Verification time: {self.stats['verification_time']:.3f}s")
        self._log("info", f"Decryption time: {self.stats['decryption_time']:.3f}s")
        self._log("info", f"Total time: {self.stats['total_time']:.3f}s")
        self._log("info", f"Files received: {self.stats['files_received']}")
        self._log("info", f"Files rejected: {self.stats['files_rejected']}")
        self._log("info", f"Received file size: {self.stats['received_file_size']} bytes")
        self._log("info", f"Decrypted size: {self.stats['decrypted_size']} bytes")
        self._log("info", f"Messages received: {self.stats['messages_received']}")
        self._log("info", f"Errors: {self.stats['errors']}")

    def get_statistics(self) -> Dict[str, Any]:
        """Lấy thống kê hiệu suất"""
        return self.stats.copy()

    def reset_statistics(self):
        """Reset thống kê"""
        self.stats = {
            'handshake_time': 0,
            'key_exchange_time': 0,
            'decryption_time': 0,
            'verification_time': 0,
            'total_time': 0,
            'received_file_size': 0,
            'decrypted_size': 0,
            'files_received': 0,
            'files_rejected': 0,
            'messages_received': 0,
            'errors': 0
        }

    def start(self):
        self._main_loop()