"""
Sender Component
Thực hiện việc gửi tài liệu pháp lý qua hai server trung gian tuần tự
Bao gồm: Handshake → Key Exchange → Data Transfer → Wait for ACK/NACK
"""

import os
import time
import base64
from typing import Dict, Any, Optional, Tuple
from src.core.crypto_handler import CryptoHandler
from src.core.socket_handler import ClientSocketHandler, MessageTypes, create_message
from src.core.logger import Logger
from src.utils.file_handler import FileHandler
from src.utils.validation import MessageValidator


class Sender:
    """
    Người gửi tài liệu pháp lý
    Thực hiện luồng: Handshake → Key Exchange → Encrypt & Send → Wait ACK
    """
    
    def __init__(self, server1_host: str = 'localhost', server1_port: int = 8000,
                 sender_id: str = 'sender', timeout: int = 30, log_callback=None):
        """
        Khởi tạo Sender
        
        Args:
            server1_host: IP của Server 1 (server trung gian đầu tiên)
            server1_port: Port của Server 1
            sender_id: ID của sender
            timeout: Timeout cho các thao tác
            log_callback: Callback function for logging
        """
        self.sender_id = sender_id
        self.logger = Logger(
            name="sender",
            log_dir="./logs",
            log_level="INFO",
            enable_console_logging=False
        )
        self.crypto = CryptoHandler(logger=self.logger)
        self.private_key, self.public_key = self.crypto.generate_rsa_keypair()
        self.timeout = timeout
        self.socket_handler = ClientSocketHandler(server1_host, server1_port, timeout, logger_name="sender_socket")
        self.crypto = CryptoHandler()
        self.file_handler = FileHandler()
        
        self.validator = MessageValidator()
        
        # Trạng thái
        self.is_connected = False
        self.receiver_public_key = None
        self.session_key = None
        self.current_transaction_id = None
        
        # Thống kê
        self.stats = {
            'handshake_time': 0,
            'key_exchange_time': 0,
            'encryption_time': 0,
            'transmission_time': 0,
            'total_time': 0,
            'file_size': 0,
            'encrypted_size': 0
        }

        self.log_callback = log_callback

    def _log(self, level, msg):
        if self.log_callback:
            self.log_callback(level, msg)
        else:
            if level == "info":
                self.logger.info(msg)
            else:
                self.logger.error(msg)

    def connect_to_server(self) -> bool:
        """
        Kết nối đến Server 1
        
        Returns:
            bool: True nếu kết nối thành công
        """
        self._log("info", f"[CONNECT] Đang kết nối tới Server1 ({self.socket_handler.host}:{self.socket_handler.port})...")
        try:
            if self.socket_handler.connect():
                self.is_connected = True
                self._log("info", "[CONNECT] Đã kết nối đến Server 1 thành công.")
                return True
            else:
                self._log("error", "[CONNECT] Không thể kết nối đến Server 1.")
                return False
        except Exception as e:
            self._log("error", f"[CONNECT] Lỗi kết nối: {e}")
            return False

    def disconnect(self):
        """Ngắt kết nối"""
        if self.socket_handler:
            self.socket_handler.disconnect()
            self.is_connected = False
            self._log("info", "Đã ngắt kết nối khỏi Server 1")

    def perform_handshake(self) -> bool:
        """
        Thực hiện bước Handshake
        Sender → Server1 → Server2 → Receiver: "Hello!"
        Receiver → Server2 → Server1 → Sender: "Ready!"
        """
        start_time = time.time()
        self._log("info", "=== BẮT ĐẦU HANDSHAKE ===")
        try:
            if not self.is_connected:
                if not self.connect_to_server():
                    self._log("error", "[HANDSHAKE] Không thể kết nối tới Server1 để handshake.")
                    return False
            # Bước 1: Gửi "Hello" qua Server 1
            if not self.current_transaction_id:
                self.current_transaction_id = f"tx_{int(time.time())}_{self.sender_id}"
            hello_message = create_message(
                MessageTypes.HELLO,
                data={
                    'message': 'Hello!',
                    'sender_id': self.sender_id
                },
                source=self.sender_id,
                destination='receiver',
                transaction_id=self.current_transaction_id
            )
            self._log("info", "[HANDSHAKE] Gửi Hello! đến Receiver qua Server 1 → Server 2")
            if not self.socket_handler.send(hello_message):
                self._log("error", "[HANDSHAKE] Không thể gửi Hello!")
                return False

            # Bước 2: Chờ nhận "Ready" từ Receiver
            self._log("info", "[HANDSHAKE] Chờ nhận Ready! từ Receiver...")
            ready_message = self.socket_handler.receive()
            if not ready_message:
                self._log("error", "[HANDSHAKE] Không nhận được phản hồi Ready! (có thể Server1 hoặc Server2 hoặc Receiver không phản hồi)")
                return False
            if ready_message.get('type') != MessageTypes.READY:
                self._log("error", f"[HANDSHAKE] Nhận được message không mong đợi: {ready_message.get('type')}")
                return False
            if ready_message.get('data', {}).get('message') != 'Ready!':
                self._log("error", "[HANDSHAKE] Message Ready! không đúng format")
                return False
            if ready_message.get('transaction_id') != self.current_transaction_id:
                self._log("error", "[HANDSHAKE] Transaction ID không khớp trong READY!")
                return False

            self._log("info", "[HANDSHAKE] HANDSHAKE thành công")
            self.stats['handshake_time'] = time.time() - start_time
            return True
        except Exception as e:
            self._log("error", f"[HANDSHAKE] Lỗi trong quá trình handshake: {e}")
            return False
        
    def request_public_key(self) -> bool:
        """
        Kết nối đến receiver và lấy public key.
        Returns True nếu thành công, False nếu thất bại.
        """
        self._log("info", "Kết nối để lấy Public Key từ Receiver...")
        if not self.connect_to_server():
            self._log("error", "Không thể kết nối để lấy Public Key")
            return False

        get_key_message = create_message(
            "GET_PUBLIC_KEY",
            data={},
            source=self.sender_id,
            destination='receiver',
            transaction_id=self.current_transaction_id
        )
        if not self.socket_handler.send(get_key_message):
            self._log("error", "Không thể gửi GET_PUBLIC_KEY")
            return False

        pubkey_message = self.socket_handler.receive()
        if not pubkey_message or pubkey_message.get('type') != MessageTypes.PUBLIC_KEY:
            self._log("error", "Không nhận được Public Key từ Receiver")
            return False
        if pubkey_message.get('transaction_id') != self.current_transaction_id:
            self._log("error", "Transaction ID không khớp trong PUBLIC_KEY!")
            return False
        receiver_pubkey_pem = pubkey_message.get('data', {}).get('public_key')
        if not receiver_pubkey_pem:
            self._log("error", "Public Key rỗng")
            return False
        self.receiver_public_key = self.crypto.import_key_from_pem(receiver_pubkey_pem)
        self._log("info", "Đã nhận Public Key từ Receiver")
        return True

    def exchange_keys(self) -> bool:
        """
        Thực hiện trao đổi khóa
        1. Tạo session key và mã hóa bằng RSA public key
        2. Gửi session key đã mã hóa đến Receiver
        
        Returns:
            bool: True nếu trao đổi khóa thành công
        """
        start_time = time.time()
        self._log("info", "=== BẮT ĐẦU TRAO ĐỔI KHÓA ===")
        try:
            # Bước 1: Tạo session key cho mã hóa DES
            self.session_key = self.crypto.generate_session_key()
            self._log("info", "Đã tạo Session Key")
            # Bước 2: Mã hóa session key bằng RSA public key của receiver
            encrypted_session_key = self.crypto.encrypt_session_key(
                self.session_key, 
                self.receiver_public_key
            )
            # Bước 3: Gửi session key đã mã hóa
            session_key_message = create_message(
                MessageTypes.SESSION_KEY,
                data={
                    'encrypted_session_key': base64.b64encode(encrypted_session_key).decode('utf-8')
                },
                source=self.sender_id,
                destination='receiver',
                transaction_id=self.current_transaction_id
            )
            self._log("info", "Gửi Session Key đã mã hóa đến Receiver...")
            if not self.socket_handler.send(session_key_message):
                self._log("error", "Không thể gửi Session Key")
                return False
            self.stats['key_exchange_time'] = time.time() - start_time
            self._log("info", f"TRAO ĐỔI KHÓA THÀNH CÔNG! ({self.stats['key_exchange_time']:.3f}s)")
            return True
        except Exception as e:
            self._log("error", f"Lỗi trao đổi khóa: {e}")
            return False

    def encrypt_and_send_file(self, file_path: str, transaction_id: str = None) -> bool:
        """
        Mã hóa và gửi file

        
        Args:
            file_path: Đường dẫn file cần gửi
            transaction_id: ID giao dịch
            
        Returns:
            bool: True nếu gửi thành công
        """
        start_time = time.time()
        self._log("info", "=== BẮT ĐẦU MÃ HÓA VÀ GỬI FILE ===")
        
        try:
            # Bước 1: Kiểm tra file tồn tại
            if not os.path.exists(file_path):
                self._log("error", f"File không tồn tại: {file_path}")
                return False
            
            # Bước 2: Đọc file
            self._log("info", f"Đọc file: {file_path}")
            file_data = self.file_handler.read_file(file_path)
            if file_data is None:
                self._log("error", "Không thể đọc file")
                return False
            
            file_name = os.path.basename(file_path)
            self.stats['file_size'] = len(file_data)
            self._log("info", f"Đã đọc file: {file_name} ({self.stats['file_size']} bytes)")
            
            # Bước 3: Tạo IV ngẫu nhiên
            iv = self.crypto.generate_iv()
            self._log("info", "Đã tạo IV")
            
            # Bước 4: Mã hóa file bằng DES
            encryption_start = time.time()
            ciphertext = self.crypto.encrypt_file_des(file_data, self.session_key, iv)
            self.stats['encryption_time'] = time.time() - encryption_start
            self.stats['encrypted_size'] = len(ciphertext)
            
            self._log("info", f"Đã mã hóa file DES ({self.stats['encryption_time']:.3f}s)")
            
            # Bước 5: Tính hash SHA-512(IV || ciphertext)
            hash_data = iv + ciphertext
            file_hash = self.crypto.calculate_sha512(hash_data)
            self._log("info", "Đã tính hash SHA-512")
            
            # Bước 6: Tạo metadata và ký số
            if not transaction_id:
                transaction_id = self.current_transaction_id or f"tx_{int(time.time())}_{self.sender_id}"
            self.current_transaction_id = transaction_id
            
            metadata = {
                'filename': file_name,
                'timestamp': time.time(),
                'transaction_id': transaction_id,
                'file_size': self.stats['file_size'],
                'sender_id': self.sender_id,
                'public_key_sender': self.crypto.export_key_to_pem(self.public_key)
            }

            # Ký metadata bằng RSA/SHA-512
            signature = self.crypto.sign_metadata(metadata, self.private_key)
            
            # Bước 7: Tạo gói tin gửi
            file_packet = {
                'iv': base64.b64encode(iv).decode('utf-8'),
                'cipher': base64.b64encode(ciphertext).decode('utf-8'),
                'hash': file_hash,
                'sig': signature,
                'metadata': metadata
            }
            
            file_message = create_message(
                MessageTypes.FILE_DATA,
                data=file_packet,
                source=self.sender_id,
                destination='receiver',
                transaction_id=transaction_id
            )
            
            # Bước 8: Gửi gói tin
            transmission_start = time.time()
            self._log("info", "Gửi gói tin file đến Receiver...")
            
            if not self.socket_handler.send(file_message):
                self._log("error", "Không thể gửi file data")
                return False
            
            self.stats['transmission_time'] = time.time() - transmission_start
            self.stats['total_time'] = time.time() - start_time
            
            self._log("info", f"ĐÃ GỬI FILE THÀNH CÔNG!")
            self._log("info", f"  - Thời gian mã hóa: {self.stats['encryption_time']:.3f}s")
            self._log("info", f"  - Thời gian truyền: {self.stats['transmission_time']:.3f}s")
            self._log("info", f"  - Tổng thời gian: {self.stats['total_time']:.3f}s")
            
            return True
            
        except Exception as e:
            self._log("error", f"Lỗi mã hóa và gửi file: {e}")
            return False

    def wait_for_acknowledgment(self, timeout: int = None) -> Tuple[bool, str]:
        """
        Chờ nhận ACK/NACK từ Receiver
        
        Args:
            timeout: Timeout chờ ACK (giây)
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        if timeout is None:
            timeout = self.timeout
            
        self._log("info", "Chờ nhận ACK/NACK từ Receiver...")
        
        try:
            # Đặt timeout cho socket
            original_timeout = self.socket_handler.timeout
            self.socket_handler.socket.settimeout(timeout)
            
            ack_message = self.socket_handler.receive()

            self.socket_handler.socket.settimeout(original_timeout)
            
            if not ack_message:
                return False, "Không nhận được phản hồi từ Receiver"
            
            msg_type = ack_message.get('type')
            
            if msg_type == MessageTypes.ACK:
                self._log("info", "NHẬN ĐƯỢC ACK - FILE ĐÃ ĐƯỢC NHẬN THÀNH CÔNG!")
                return True, "File đã được nhận và xác minh thành công"
                
            elif msg_type == MessageTypes.NACK:
                error_reason = ack_message.get('data', {}).get('error', 'Unknown error')
                self._log("error", f"✗ NHẬN ĐƯỢC NACK - LỖI: {error_reason}")
                return False, f"File bị từ chối: {error_reason}"
                
            else:
                self._log("error", f"Nhận được message không mong đợi: {msg_type}")
                return False, f"Message không hợp lệ: {msg_type}"
                
        except Exception as e:
            self._log("error", f"Lỗi chờ ACK: {e}")
            return False, f"Lỗi: {e}"

    def send_file_complete_flow(self, file_path: str, transaction_id: str = None) -> bool:
        """
        Thực hiện toàn bộ luồng gửi file
        1. Handshake
        2. Key Exchange  
        3. Encrypt & Send File
        4. Wait for ACK
        
        Args:
            file_path: Đường dẫn file cần gửi
            transaction_id: ID giao dịch
            
        Returns:
            bool: True nếu toàn bộ luồng thành công
        """
        total_start_time = time.time()
        self._log("info", f"=== BẮT ĐẦU QUÁ TRÌNH GỬI FILE: {file_path} ===")
        
        try:
            # Bước 1: Kết nối đến server
            if not self.is_connected:
                if not self.connect_to_server():
                    return False
            
            # Bước 2: Handshake
            if not self.perform_handshake():
                self._log("error", "Handshake thất bại")
                return False
            
            # Bước 2.5: Lấy public key từ Receiver
            if not self.request_public_key():
                self._log("error", "Lấy public key thất bại")
                return False
            
            # Bước 3: Trao đổi khóa
            if not self.exchange_keys():
                self._log("error", "Trao đổi khóa thất bại")
                return False
            
            # Bước 4: Mã hóa và gửi file
            if not self.encrypt_and_send_file(file_path, transaction_id):
                self._log("error", "Gửi file thất bại")
                return False
            
            # Bước 5: Chờ ACK/NACK
            success, message = self.wait_for_acknowledgment()
            
            total_time = time.time() - total_start_time
            
            if success:
                self._log("info", f"HOÀN THÀNH GỬI FILE THÀNH CÔNG! (Tổng: {total_time:.3f}s)")
                self._log("info", f"Transaction ID: {self.current_transaction_id}")
                return True
            else:
                self._log("error", f"GỬI FILE THẤT BẠI: {message}")
                return False
                
        except Exception as e:
            self._log("error", f"Lỗi trong quá trình gửi file: {e}")
            return False
        finally:
            # Log thống kê cuối cùng
            self._log_statistics()

    def _log_statistics(self):
        """Ghi log thống kê hiệu suất"""
        self._log("info", "=== THỐNG KÊ HIỆU SUẤT ===")
        self._log("info", f"Handshake time: {self.stats['handshake_time']:.3f}s")
        self._log("info", f"Key exchange time: {self.stats['key_exchange_time']:.3f}s")
        self._log("info", f"Encryption time: {self.stats['encryption_time']:.3f}s")
        self._log("info", f"Transmission time: {self.stats['transmission_time']:.3f}s")
        self._log("info", f"Total time: {self.stats['total_time']:.3f}s")
        self._log("info", f"File size: {self.stats['file_size']} bytes")
        self._log("info", f"Encrypted size: {self.stats['encrypted_size']} bytes")
        
        if self.stats['encryption_time'] > 0:
            throughput = self.stats['file_size'] / self.stats['encryption_time']
            self._log("info", f"Encryption throughput: {throughput:.2f} bytes/s")

    def get_statistics(self) -> Dict[str, Any]:
        """Lấy thống kê hiệu suất"""
        return self.stats.copy()

    def reset_statistics(self):
        """Reset thống kê"""
        self.stats = {
            'handshake_time': 0,
            'key_exchange_time': 0,
            'encryption_time': 0,
            'transmission_time': 0,
            'total_time': 0,
            'file_size': 0,
            'encrypted_size': 0
        }