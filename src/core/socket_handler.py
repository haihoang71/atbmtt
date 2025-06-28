"""
Socket Handler Module
Xử lý các kết nối socket TCP cho hệ thống truyền tài liệu pháp lý
Hỗ trợ giao tiếp qua hai server trung gian tuần tự
"""

import socket
import json
import threading
import time
from typing import Dict, Any, Optional, Tuple, Callable
from src.core.logger import Logger


class SocketHandler:
    """Base class cho xử lý socket TCP"""
    
    def __init__(self, host: str = 'localhost', port: int = 8080, 
                 timeout: int = 30, buffer_size: int = 4096, logger_name: str = None):
        """
        Khởi tạo Socket Handler
        
        Args:
            host: Địa chỉ IP
            port: Cổng kết nối
            timeout: Timeout cho socket (giây)
            buffer_size: Kích thước buffer
            logger_name: Tên logger (nếu có)
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.buffer_size = buffer_size
        self.socket = None
        self.is_connected = False
        self.logger = Logger(logger_name or f"Socket_{host}_{port}", enable_console_logging=False)
        
    def create_socket(self) -> socket.socket:
        """Tạo socket TCP"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return sock
        except Exception as e:
            self.logger.error(f"Lỗi tạo socket: {e}")
            raise
    
    def send_message(self, sock: socket.socket, message: Dict[str, Any]) -> bool:
        """
        Gửi tin nhắn JSON qua socket
        
        Args:
            sock: Socket để gửi
            message: Dictionary chứa tin nhắn
            
        Returns:
            bool: True nếu gửi thành công
        """
        try:
            # Chuyển đổi message thành JSON
            json_message = json.dumps(message, ensure_ascii=False)
            message_bytes = json_message.encode('utf-8')
            
            # Gửi độ dài message trước
            message_length = len(message_bytes)
            length_bytes = message_length.to_bytes(4, byteorder='big')
            sock.send(length_bytes)
            
            # Gửi message
            total_sent = 0
            while total_sent < message_length:
                sent = sock.send(message_bytes[total_sent:])
                if sent == 0:
                    raise ConnectionError("Socket connection broken")
                total_sent += sent
                
            self.logger.info(f"Đã gửi message: {message.get('type', 'unknown')}")
            return True
            
        except Exception as e:
            self.logger.error(f"Lỗi gửi message: {e}")
            return False
    
    def receive_message(self, sock: socket.socket) -> Optional[Dict[str, Any]]:
        """
        Nhận tin nhắn JSON từ socket
        
        Args:
            sock: Socket để nhận
            
        Returns:
            Dict hoặc None nếu lỗi
        """
        try:
            # Nhận độ dài message trước
            length_bytes = self._receive_exact(sock, 4)
            if not length_bytes:
                return None
                
            message_length = int.from_bytes(length_bytes, byteorder='big')
            
            # Nhận message
            message_bytes = self._receive_exact(sock, message_length)
            if not message_bytes:
                return None
                
            # Decode JSON
            json_message = message_bytes.decode('utf-8')
            message = json.loads(json_message)
            
            self.logger.info(f"Đã nhận message: {message.get('type', 'unknown')}")
            return message
            
        except Exception as e:
            self.logger.error(f"Lỗi nhận message: {e}")
            return None
    
    def _receive_exact(self, sock: socket.socket, length: int) -> Optional[bytes]:
        """
        Nhận chính xác số byte được chỉ định
        
        Args:
            sock: Socket
            length: Số byte cần nhận
            
        Returns:
            bytes hoặc None nếu lỗi
        """
        data = b''
        while len(data) < length:
            try:
                chunk = sock.recv(length - len(data))
                if not chunk:
                    return None
                data += chunk
            except socket.timeout:
                self.logger.warning("Socket timeout khi nhận dữ liệu")
                return None
            except Exception as e:
                self.logger.error(f"Lỗi nhận dữ liệu: {e}")
                return None
        return data
    
    def close_socket(self, sock: socket.socket):
        """Đóng socket an toàn"""
        try:
            if sock:
                sock.close()
                self.logger.info("Đã đóng socket")
        except Exception as e:
            self.logger.error(f"Lỗi đóng socket: {e}")


class ClientSocketHandler(SocketHandler):
    """Socket handler cho client (Sender và Receiver)"""
    
    def connect(self) -> bool:
        """
        Kết nối đến server
        
        Returns:
            bool: True nếu kết nối thành công
        """
        try:
            self.socket = self.create_socket()
            self.socket.connect((self.host, self.port))
            self.is_connected = True
            self.logger.info(f"Đã kết nối đến {self.host}:{self.port}")
            return True
            
        except Exception as e:
            self.logger.error(f"Lỗi kết nối: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self):
        """Ngắt kết nối"""
        if self.socket:
            self.close_socket(self.socket)
            self.socket = None
            self.is_connected = False
    
    def send(self, message: Dict[str, Any]) -> bool:
        """Gửi message qua socket đã kết nối"""
        if not self.is_connected or not self.socket:
            self.logger.error("Socket chưa kết nối")
            return False
        return self.send_message(self.socket, message)
    
    def receive(self) -> Optional[Dict[str, Any]]:
        """Nhận message từ socket đã kết nối"""
        if not self.is_connected or not self.socket:
            self.logger.error("Socket chưa kết nối")
            return None
        return self.receive_message(self.socket)


class ServerSocketHandler(SocketHandler):
    """Socket handler cho server (Server trung gian)"""
    
    def __init__(self, host: str = 'localhost', port: int = 8080, 
                 timeout: int = 30, buffer_size: int = 4096, logger_name: str = None):
        super().__init__(host, port, timeout, buffer_size, logger_name)
        self.server_socket = None
        self.is_running = False
        self.client_handlers = {}  # Dict lưu các client handler
        self.message_callback = None  # Callback xử lý message
        
    def start_server(self, message_callback: Callable = None) -> bool:
        """
        Khởi động server
        
        Args:
            message_callback: Hàm callback xử lý message
            
        Returns:
            bool: True nếu khởi động thành công
        """
        try:
            self.server_socket = self.create_socket()
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.is_running = True
            self.message_callback = message_callback
            
            self.logger.info(f"Server đang lắng nghe tại {self.host}:{self.port}")
            
            # Chạy server trong thread riêng
            server_thread = threading.Thread(target=self._accept_connections)
            server_thread.daemon = True
            server_thread.start()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Lỗi khởi động server: {e}")
            return False
    
    def _accept_connections(self):
        """Chấp nhận kết nối từ client"""
        while self.is_running:
            try:
                client_socket, client_address = self.server_socket.accept()
                client_id = f"{client_address[0]}_{client_address[1]}_{int(time.time())}"
                
                self.logger.info(f"Client kết nối: {client_address} - ID: {client_id}")
                
                # Tạo thread xử lý client
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, client_id, client_address)
                )
                client_thread.daemon = True
                client_thread.start()
                
            except Exception as e:
                if self.is_running:
                    self.logger.error(f"Lỗi chấp nhận kết nối: {e}")
    
    def _handle_client(self, client_socket: socket.socket, 
                      client_id: str, client_address: Tuple[str, int]):
        """
        Xử lý client kết nối
        
        Args:
            client_socket: Socket của client
            client_id: ID của client
            client_address: Địa chỉ client
        """
        self.client_handlers[client_id] = {
            'socket': client_socket,
            'address': client_address,
            'connected_time': time.time()
        }
        
        try:
            while self.is_running:
                message = self.receive_message(client_socket)
                if message is None:
                    break
                
                # Gọi callback xử lý message nếu có
                if self.message_callback:
                    response = self.message_callback(message, client_id)
                    if response:
                        # If response is a list, send all
                        if isinstance(response, list):
                            for resp in response:
                                response_json = json.dumps(resp, ensure_ascii=False)
                                response_bytes = response_json.encode('utf-8')
                                response_length = len(response_bytes)
                                length_bytes = response_length.to_bytes(4, byteorder='big')
                                client_socket.sendall(length_bytes)
                                client_socket.sendall(response_bytes)
                                self.logger.info(f"Đã gửi response: {resp.get('type', 'unknown')}")
                        else:
                            response_json = json.dumps(response, ensure_ascii=False)
                            response_bytes = response_json.encode('utf-8')
                            response_length = len(response_bytes)
                            length_bytes = response_length.to_bytes(4, byteorder='big')
                            client_socket.sendall(length_bytes)
                            client_socket.sendall(response_bytes)
                            self.logger.info(f"Đã gửi response: {response.get('type', 'unknown')}")
                # Do not break after sending a response; allow the loop to continue for more messages
        except Exception as e:
            self.logger.error(f"Lỗi xử lý client {client_id}: {e}")
            
        finally:
            # Dọn dẹp khi client ngắt kết nối
            self.close_socket(client_socket)
            if client_id in self.client_handlers:
                del self.client_handlers[client_id]
            self.logger.info(f"Client {client_id} đã ngắt kết nối")
    
    def broadcast_message(self, message: Dict[str, Any], 
                         exclude_client: str = None) -> int:
        """
        Broadcast message đến tất cả client
        
        Args:
            message: Message cần gửi
            exclude_client: ID client không gửi
            
        Returns:
            int: Số client đã gửi thành công
        """
        sent_count = 0
        for client_id, client_info in self.client_handlers.items():
            if exclude_client and client_id == exclude_client:
                continue
                
            if self.send_message(client_info['socket'], message):
                sent_count += 1
                
        return sent_count
    
    def send_to_client(self, client_id: str, message: Dict[str, Any]) -> bool:
        """
        Gửi message đến client cụ thể
        
        Args:
            client_id: ID của client
            message: Message cần gửi
            
        Returns:
            bool: True nếu gửi thành công
        """
        if client_id not in self.client_handlers:
            self.logger.error(f"Client {client_id} không tồn tại")
            return False
            
        client_socket = self.client_handlers[client_id]['socket']
        return self.send_message(client_socket, message)
    
    def get_connected_clients(self) -> Dict[str, Dict]:
        """Lấy danh sách client đang kết nối"""
        return self.client_handlers.copy()
    
    def stop_server(self):
        """Dừng server"""
        self.is_running = False
        
        # Đóng tất cả client connections
        for client_id, client_info in self.client_handlers.items():
            self.close_socket(client_info['socket'])
        self.client_handlers.clear()
        
        # Đóng server socket
        if self.server_socket:
            self.close_socket(self.server_socket)
            self.server_socket = None
            
        self.logger.info("Server đã dừng")


class MessageTypes:
    """Định nghĩa các loại message trong giao thức"""
    
    # Handshake messages
    HELLO = "HELLO"
    READY = "READY"
    
    # Key exchange messages
    PUBLIC_KEY = "PUBLIC_KEY"
    SESSION_KEY = "SESSION_KEY"
    
    # Data transfer messages
    FILE_DATA = "FILE_DATA"
    FILE_METADATA = "FILE_METADATA"
    
    # Response messages
    ACK = "ACK"
    NACK = "NACK"
    
    # Server relay messages
    RELAY = "RELAY"
    
    # Error messages
    ERROR = "ERROR"


def create_message(msg_type: str, data: Dict[str, Any] = None, 
                  source: str = None, destination: str = None, transaction_id: str = None) -> Dict[str, Any]:
    """
    Tạo message theo format chuẩn
    
    Args:
        msg_type: Loại message (từ MessageTypes)
        data: Dữ liệu message
        source: Nguồn gửi
        destination: Đích nhận
        transaction_id: ID giao dịch (nếu có)
        
    Returns:
        Dict: Message đã format
    """
    message = {
        'type': msg_type,
        'timestamp': time.time(),
        'data': data or {}
    }
    
    if source:
        message['source'] = source
    if destination:
        message['destination'] = destination
    if transaction_id:
        message['transaction_id'] = transaction_id
        
    return message


# Utility functions cho socket handling
def test_connection(host: str, port: int, timeout: int = 5) -> bool:
    """
    Test kết nối đến host:port
    
    Args:
        host: Địa chỉ IP
        port: Cổng
        timeout: Timeout (giây)
        
    Returns:
        bool: True nếu kết nối được
    """
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except:
        return False


def get_local_ip() -> str:
    """Lấy IP local của máy"""
    try:
        # Tạo connection đến một địa chỉ bên ngoài để lấy IP local
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except:
        return "127.0.0.1"


def find_free_port(start_port: int = 8000, max_attempts: int = 100) -> int:
    """
    Tìm port trống
    
    Args:
        start_port: Port bắt đầu tìm
        max_attempts: Số port tối đa để thử
        
    Returns:
        int: Port trống hoặc -1 nếu không tìm được
    """
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    return -1

def _forward_message(self, message) -> Optional[Dict[str, Any]]:
    try:
        upstream_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        upstream_socket.settimeout(10)
        upstream_socket.connect((self.upstream_host, self.upstream_port))

        # Send message (length-prefixed)
        if isinstance(message, dict):
            message_json = json.dumps(message)
        else:
            message_json = json.dumps(message.to_dict())
        message_bytes = message_json.encode('utf-8')
        message_length = len(message_bytes)
        length_bytes = message_length.to_bytes(4, byteorder='big')
        upstream_socket.sendall(length_bytes)
        upstream_socket.sendall(message_bytes)

        # Receive first response
        length_bytes = self._receive_exact(upstream_socket, 4)
        if not length_bytes:
            upstream_socket.close()
            return None
        response_length = int.from_bytes(length_bytes, byteorder='big')
        response_bytes = self._receive_exact(upstream_socket, response_length)
        if not response_bytes:
            upstream_socket.close()
            return None
        response1 = json.loads(response_bytes.decode('utf-8'))

        # Try to receive a second response (with a short timeout)
        upstream_socket.settimeout(0.5)
        try:
            length_bytes2 = self._receive_exact(upstream_socket, 4)
            if length_bytes2:
                response_length2 = int.from_bytes(length_bytes2, byteorder='big')
                response_bytes2 = self._receive_exact(upstream_socket, response_length2)
                if response_bytes2:
                    response2 = json.loads(response_bytes2.decode('utf-8'))
                    upstream_socket.close()
                    return [response1, response2]
        except socket.timeout:
            pass

        upstream_socket.close()
        return response1

    except Exception as e:
        self.logger.error(f'Lỗi forward/wait response: {e}')
        return None