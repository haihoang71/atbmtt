"""
Server Intermediate Component
Server trung gian cho Legal Document Transfer System
Bao gồm: Server 1 và Server 2, message forwarding, transaction logging
"""

import socket
import threading
import time
import json
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from src.core.logger import Logger
from src.core.socket_handler import ServerSocketHandler
from src.components.protocol_handler import ProtocolHandler, ProtocolState, MessageType


@dataclass
class ConnectionInfo:
    """Thông tin kết nối"""
    client_id: str
    socket: socket.socket
    address: Tuple[str, int]
    connected_time: float
    last_activity: float
    transaction_id: Optional[str] = None


class IntermediateServer:
    """
    Server trung gian - Chuyển tiếp message giữa các components
    """
    
    def __init__(self, server_id: str, host: str = 'localhost', port: int = 8001,
                 upstream_host: str = None, upstream_port: int = None,
                 log_dir: str = None, log_callback=None):
        """
        Khởi tạo Intermediate Server
        
        Args:
            server_id: ID của server (server1, server2)
            host: Host để bind
            port: Port để bind
            upstream_host: Host của server upstream (nếu có)
            upstream_port: Port của server upstream (nếu có)
            log_dir: Thư mục lưu log (nếu có)
        """
        self.server_id = server_id
        self.host = host
        self.port = port
        self.upstream_host = upstream_host
        self.upstream_port = upstream_port
        
        # Logger
        log_name = f"{server_id}"
        if log_dir:
            self.logger = Logger(log_name, log_dir=log_dir, enable_console_logging=False)
        else:
            self.logger = Logger(log_name, enable_console_logging=False)
        
        self.log_callback = log_callback
        self.protocol_handler = ProtocolHandler(server_id, self.logger)
        self.socket_handler = ServerSocketHandler(host, port, timeout=30, logger_name=f"{server_id}_socket")
        
        
        # Connection management
        self.connections: Dict[str, ConnectionInfo] = {}
        self.connection_lock = threading.Lock()
        
        # Message queue for forwarding
        self.message_queue: List[Dict[str, Any]] = []
        self.queue_lock = threading.Lock()
        
        # Server state
        self.is_running = False
        self.is_forwarding = False
        
        # Statistics
        self.stats = {
            'connections_accepted': 0,
            'connections_closed': 0,
            'messages_received': 0,
            'messages_forwarded': 0,
            'messages_dropped': 0,
            'errors': 0,
            'start_time': time.time()
        }
        
        self.logger.info(f"=== INTERMEDIATE SERVER KHỞI TẠO: {server_id} ===")
        self.logger.info(f"Bind: {host}:{port}")
        if upstream_host and upstream_port:
            self.logger.info(f"Upstream: {upstream_host}:{upstream_port}")

    def start(self) -> bool:
        """
        Khởi động server
        
        Returns:
            bool: True nếu thành công
        """
        try:
            self.logger.info(f"Khởi động {self.server_id}...")
            
            # Khởi động socket server với callback
            if not self.socket_handler.start_server(message_callback=self._handle_message):
                self.logger.error("Không thể khởi động socket server")
                return False
            
            self.is_running = True
            
            # Khởi động forwarding thread
            if self.upstream_host and self.upstream_port:
                self.is_forwarding = True
                forwarding_thread = threading.Thread(target=self._forwarding_worker, daemon=True)
                forwarding_thread.start()
                self.logger.info("Đã khởi động forwarding thread")
            
            # Khởi động connection cleanup thread
            cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
            cleanup_thread.start()
            self.logger.info("Đã khởi động cleanup thread")
            
            self.logger.info(f"{self.server_id} ĐÃ KHỞI ĐỘNG THÀNH CÔNG!")
            return True
            
        except Exception as e:
            self.logger.error(f"Lỗi khởi động server: {e}")
            return False

    def stop(self):
        """Dừng server"""
        self.logger.info(f"Dừng {self.server_id}...")
        
        self.is_running = False
        self.is_forwarding = False
        
        # Đóng tất cả connections
        with self.connection_lock:
            for conn_info in list(self.connections.values()):
                self._close_connection(conn_info)
        
        # Dừng socket server
        self.socket_handler.stop_server()
        
        # Cleanup protocol handler
        self.protocol_handler.cleanup()
        
        self.logger.info(f"{self.server_id} Server stop")

    def run(self):
        """Chạy server main loop"""
        self.logger.info(f"Bắt đầu main loop của {self.server_id}")
        
        try:
            while self.is_running:
                time.sleep(1)
                
        except Exception as e:
            self.logger.error(f"Lỗi trong main loop: {e}")
        finally:
            self.stop()

    def _handle_message(self, message: Dict[str, Any], client_id: str) -> Optional[Any]:
        try:
            self.stats['messages_received'] += 1
            msg_type = message.get('type', 'UNKNOWN')
            self._log("info", f"[RECV] Nhận từ {client_id}: {msg_type}")
            if msg_type == 'HELLO':
                self._log("info", f"[HANDSHAKE] Đã nhận gói HELLO từ {client_id}, forward tới Server2...")
            destination = message.get('destination')
            if destination and destination != self.server_id:
                response = self._forward_message(message)
                if response is None:
                    self._log("error", f"[HANDSHAKE] Forward message HELLO thất bại (có thể Server2 chưa khởi động hoặc không phản hồi)")
                    return None
                if msg_type == 'HELLO':
                    self._log("info", f"[HANDSHAKE] Đã nhận phản hồi cho HELLO từ Server2, gửi lại cho {client_id}")
                return response
            return None
        except Exception as e:
            self._log("error", f"Lỗi xử lý message từ {client_id}: {e}")
            self.stats['errors'] += 1
            return None

    def _queue_message_for_forwarding(self, message):
        """Thêm message vào queue để forward"""
        with self.queue_lock:
            self.message_queue.append({
                'message': message,
                'timestamp': time.time(),
                'retry_count': 0
            })
            self.logger.debug(f"Thêm message {message.get('type')} vào forwarding queue")

    def _forwarding_worker(self):
        """Worker thread để forward messages"""
        self.logger.info("Bắt đầu forwarding worker")
        
        while self.is_forwarding:
            try:
                with self.queue_lock:
                    if not self.message_queue:
                        time.sleep(0.1)
                        continue
                    
                    queue_item = self.message_queue.pop(0)
                
                success = self._forward_message(queue_item['message'])
                
                if success:
                    self.stats['messages_forwarded'] += 1
                    self.logger.debug(f"Forward message {queue_item['message'].get('type')} thành công")
                else:
                    if queue_item['retry_count'] < 3:
                        queue_item['retry_count'] += 1
                        with self.queue_lock:
                            self.message_queue.append(queue_item)
                        self.logger.warning(f"Retry forward message {queue_item['message'].get('type')}")
                    else:
                        self.stats['messages_dropped'] += 1
                        self.logger.error(f"Drop message {queue_item['message'].get('type')} sau 3 lần retry")
                
            except Exception as e:
                self.logger.error(f"Lỗi trong forwarding worker: {e}")
                time.sleep(1)

    def _receive_exact(self, sock, length):
        data = b''
        while len(data) < length:
            chunk = sock.recv(length - len(data))
            if not chunk:
                return None
            data += chunk
        return data

    def _forward_message(self, message) -> Optional[Dict[str, Any]]:
        try:
            self._log("info", f"[FORWARD] Bắt đầu forward message '{message.get('type')}' tới Server2 ({self.upstream_host}:{self.upstream_port})")
            upstream_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            upstream_socket.settimeout(10)
            try:
                upstream_socket.connect((self.upstream_host, self.upstream_port))
                self._log("info", f"[FORWARD] Kết nối tới Server2 thành công.")
            except Exception as e:
                self._log("error", f"[FORWARD] Không thể kết nối tới Server2 ({self.upstream_host}:{self.upstream_port}): {e}")
                upstream_socket.close()
                return None

            # Send message (length-prefixed)
            if isinstance(message, dict):
                message_json = json.dumps(message)
            else:
                message_json = json.dumps(message.to_dict())
            message_bytes = message_json.encode('utf-8')
            message_length = len(message_bytes)
            length_bytes = message_length.to_bytes(4, byteorder='big')
            try:
                upstream_socket.sendall(length_bytes)
                upstream_socket.sendall(message_bytes)
                self._log("info", f"[FORWARD] Đã gửi message '{message.get('type')}' tới Server2.")
            except Exception as e:
                self._log("error", f"[FORWARD] Lỗi khi gửi message tới Server2: {e}")
                upstream_socket.close()
                return None

            # Receive response (length-prefixed)
            try:
                length_bytes = self._receive_exact(upstream_socket, 4)
                if not length_bytes:
                    self._log("error", "[FORWARD] Không nhận được độ dài phản hồi từ Server2.")
                    upstream_socket.close()
                    return None
                response_length = int.from_bytes(length_bytes, byteorder='big')
                response_bytes = self._receive_exact(upstream_socket, response_length)
                if not response_bytes:
                    self._log("error", "[FORWARD] Không nhận được phản hồi từ Server2.")
                    upstream_socket.close()
                    return None
                response = json.loads(response_bytes.decode('utf-8'))
                self._log("info", f"[FORWARD] Nhận phản hồi từ Server2 thành công.")
                upstream_socket.close()
                return response
            except Exception as e:
                self._log("error", f"[FORWARD] Lỗi khi nhận phản hồi từ Server2: {e}")
                upstream_socket.close()
                return None

        except Exception as e:
            self._log("error", f'[FORWARD] Lỗi forward/wait response: {e}')
            return None

    def _send_to_client(self, client_id: str, message):
        """Gửi message đến client"""
        try:
            with self.connection_lock:
                if client_id not in self.connections:
                    self.logger.warning(f"Client {client_id} không tồn tại")
                    return False
                
                conn_info = self.connections[client_id]
                if isinstance(message, dict):
                    message_json = json.dumps(message)
                else:
                    message_json = json.dumps(message.to_dict())
                conn_info.socket.sendall(message_json.encode('utf-8'))
                
                return True
                
        except Exception as e:
            self.logger.error(f"Lỗi gửi message đến {client_id}: {e}")
            return False

    def _close_connection(self, conn_info: ConnectionInfo):
        """Đóng connection"""
        try:
            conn_info.socket.close()
            self.stats['connections_closed'] += 1
            self.logger.info(f"Đóng connection {conn_info.client_id}")
        except Exception as e:
            self.logger.error(f"Lỗi đóng connection {conn_info.client_id}: {e}")

    def _cleanup_worker(self):
        """Worker thread để cleanup connections cũ"""
        self.logger.info("Bắt đầu cleanup worker")
        
        while self.is_running:
            try:
                current_time = time.time()
                timeout = 300  # 5 phút
                
                with self.connection_lock:
                    expired_connections = []
                    
                    for client_id, conn_info in self.connections.items():
                        if current_time - conn_info.last_activity > timeout:
                            expired_connections.append(client_id)
                    
                    # Đóng expired connections
                    for client_id in expired_connections:
                        self._close_connection(self.connections[client_id])
                        del self.connections[client_id]
                        self.logger.info(f"Đóng expired connection: {client_id}")
                
                time.sleep(60)
                
            except Exception as e:
                self.logger.error(f"Lỗi trong cleanup worker: {e}")
                time.sleep(60)

    def get_statistics(self) -> Dict[str, Any]:
        """Lấy thống kê server"""
        runtime = time.time() - self.stats['start_time']
        
        return {
            **self.stats,
            'runtime_seconds': runtime,
            'active_connections': len(self.connections),
            'queue_size': len(self.message_queue),
            'messages_per_second': self.stats['messages_received'] / runtime if runtime > 0 else 0
        }

    def get_connection_info(self) -> List[Dict[str, Any]]:
        """Lấy thông tin connections"""
        with self.connection_lock:
            return [
                {
                    'client_id': conn.client_id,
                    'address': conn.address,
                    'connected_time': conn.connected_time,
                    'last_activity': conn.last_activity,
                    'transaction_id': conn.transaction_id
                }
                for conn in self.connections.values()
            ]
            
    def _log(self, level, msg):
        if self.log_callback:
            self.log_callback(level, msg)
        else:
            if level == "info":
                self.logger.info(msg)
            else:
                self.logger.error(msg)


# Factory functions
def create_server1(host: str = 'localhost', port: int = 8001, 
                  upstream_host: str = 'localhost', upstream_port: int = 8002, log_callback=None) -> 'IntermediateServer':
    """
    Tạo Server 1 (kết nối Sender -> Server 2)
    """
    return IntermediateServer(
        server_id="server1",
        host=host,
        port=port,
        upstream_host=upstream_host,
        upstream_port=upstream_port,
        log_dir="./logs",
        log_callback=log_callback
    )


def create_server2(host: str = 'localhost', port: int = 8002,
                  upstream_host: str = 'localhost', upstream_port: int = 8003, log_callback=None) -> 'IntermediateServer':
    """
    Tạo Server 2 (kết nối Server 1 -> Receiver)
    """
    return IntermediateServer(
        server_id="server2",
        host=host,
        port=port,
        upstream_host=upstream_host,
        upstream_port=upstream_port,
        log_dir="./logs",
        log_callback=log_callback
    )


if __name__ == "__main__":
    print("=== TEST SERVER ===")
    server1 = create_server1()
    
    try:
        if server1.start():
            print("Server khởi động thành công")
            server1.run()
        else:
            print("Server khởi động thất bại")
    except KeyboardInterrupt:
        print("\nServer stop")
    finally:
        server1.stop() 