"""
Protocol Handler Component
Quản lý protocol flow cho Legal Document Transfer System
Bao gồm: Message parsing, validation, state management, protocol flow control
"""

import json
import time
import uuid
from enum import Enum
from typing import Dict, Any, Optional, Tuple, List, Callable
from dataclasses import dataclass, asdict
from src.core.logger import Logger
from src.utils.validation import MessageValidator


class ProtocolState(Enum):
    """Trạng thái của protocol"""
    IDLE = "idle"
    HANDSHAKE = "handshake"
    KEY_EXCHANGE = "key_exchange"
    FILE_TRANSFER = "file_transfer"
    ACK_WAIT = "ack_wait"
    COMPLETED = "completed"
    ERROR = "error"


class MessageType(Enum):
    """Các loại message trong protocol"""
    HELLO = "HELLO"
    READY = "READY"
    PUBLIC_KEY = "PUBLIC_KEY"
    SESSION_KEY = "SESSION_KEY"
    FILE_DATA = "FILE_DATA"
    ACK = "ACK"
    NACK = "NACK"
    DISCONNECT = "DISCONNECT"
    HEARTBEAT = "HEARTBEAT"


@dataclass
class ProtocolMessage:
    """Cấu trúc message chuẩn"""
    type: str
    source: str
    destination: str
    data: Dict[str, Any]
    timestamp: float
    message_id: str
    transaction_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Chuyển đổi thành dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProtocolMessage':
        """Tạo từ dictionary"""
        return cls(**data)


class ProtocolHandler:
    """
    Protocol Handler - Quản lý toàn bộ protocol flow
    """
    
    def __init__(self, component_id: str, logger: Optional[Logger] = None):
        """
        Khởi tạo Protocol Handler
        
        Args:
            component_id: ID của component (sender, receiver, server1, server2)
            logger: Logger instance
        """
        self.component_id = component_id
        self.logger = logger or Logger(f"Protocol_{component_id}")
        self.validator = MessageValidator()
        
        # State management
        self.current_state = ProtocolState.IDLE
        self.previous_state = ProtocolState.IDLE
        self.state_history: List[Tuple[float, ProtocolState, str]] = []
        
        # Transaction management
        self.active_transactions: Dict[str, Dict[str, Any]] = {}
        self.completed_transactions: Dict[str, Dict[str, Any]] = {}
        
        # Message handlers
        self.message_handlers: Dict[str, Callable] = {
            MessageType.HELLO.value: self._handle_hello,
            MessageType.READY.value: self._handle_ready,
            MessageType.PUBLIC_KEY.value: self._handle_public_key,
            MessageType.SESSION_KEY.value: self._handle_session_key,
            MessageType.FILE_DATA.value: self._handle_file_data,
            MessageType.ACK.value: self._handle_ack,
            MessageType.NACK.value: self._handle_nack,
            MessageType.DISCONNECT.value: self._handle_disconnect,
            MessageType.HEARTBEAT.value: self._handle_heartbeat
        }
        
        # Protocol statistics
        self.stats = {
            'messages_processed': 0,
            'messages_sent': 0,
            'messages_received': 0,
            'errors': 0,
            'start_time': time.time(),
            'state_changes': 0
        }
        
        self.logger.info(f"=== PROTOCOL HANDLER KHỞI TẠO: {component_id} ===")

    def create_message(self, msg_type: str, data: Dict[str, Any], 
                      destination: str, transaction_id: str = None) -> ProtocolMessage:
        """
        Tạo message mới
        
        Args:
            msg_type: Loại message
            data: Dữ liệu message
            destination: Đích đến
            transaction_id: ID giao dịch
            
        Returns:
            ProtocolMessage: Message đã tạo
        """
        message = ProtocolMessage(
            type=msg_type,
            source=self.component_id,
            destination=destination,
            data=data,
            timestamp=time.time(),
            message_id=str(uuid.uuid4()),
            transaction_id=transaction_id
        )
        
        self.stats['messages_sent'] += 1
        self.logger.debug(f"Tạo message: {msg_type} -> {destination}")
        
        return message

    def parse_message(self, raw_data: str) -> Optional[ProtocolMessage]:
        """
        Parse message từ raw data
        
        Args:
            raw_data: Dữ liệu thô từ socket
            
        Returns:
            ProtocolMessage: Message đã parse, None nếu lỗi
        """
        try:
            data = json.loads(raw_data)
            message = ProtocolMessage.from_dict(data)
            
            is_valid, error = self.validator.validate_message_structure(data)
            if not is_valid:
                self.logger.error(f"Message structure không hợp lệ: {error}")
                return None
            
            self.stats['messages_received'] += 1
            self.logger.debug(f"Nhận message: {message.type} từ {message.source}")
            
            return message
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Lỗi parse JSON: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Lỗi parse message: {e}")
            return None

    def process_message(self, message) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Xử lý message theo protocol
        
        Args:
            message: Message cần xử lý (dict hoặc ProtocolMessage)
            
        Returns:
            Tuple[bool, str, Dict]: (success, message, response_data)
        """
        try:
            self.stats['messages_processed'] += 1
            
            if isinstance(message, dict):
                msg_type = message.get('type')
            else:
                msg_type = getattr(message, 'type', None)
            
            if msg_type not in self.message_handlers:
                self.logger.warning(f"Không có handler cho message type: {msg_type}")
                return False, f"Unknown message type: {msg_type}", None
            
            handler = self.message_handlers[msg_type]
            success, response_msg, response_data = handler(message)
            
            if success:
                self.logger.debug(f"Xử lý message {msg_type} thành công")
            else:
                self.logger.error(f"Xử lý message {msg_type} thất bại: {response_msg}")
                self.stats['errors'] += 1
            
            return success, response_msg, response_data
            
        except Exception as e:
            self.logger.error(f"Lỗi xử lý message: {e}")
            self.stats['errors'] += 1
            return False, f"Internal error: {e}", None

    def change_state(self, new_state: ProtocolState, reason: str = ""):
        """
        Thay đổi trạng thái protocol
        
        Args:
            new_state: Trạng thái mới
            reason: Lý do thay đổi
        """
        if new_state != self.current_state:
            self.previous_state = self.current_state
            self.current_state = new_state
            self.state_history.append((time.time(), new_state, reason))
            self.stats['state_changes'] += 1
            
            self.logger.info(f"State change: {self.previous_state.value} -> {new_state.value} ({reason})")

    def start_transaction(self, transaction_id: str, initiator: str, 
                         target: str, file_info: Dict[str, Any] = None) -> bool:
        """
        Bắt đầu giao dịch mới
        
        Args:
            transaction_id: ID giao dịch
            initiator: Người khởi tạo
            target: Mục tiêu
            file_info: Thông tin file (nếu có)
            
        Returns:
            bool: True nếu thành công
        """
        try:
            if transaction_id in self.active_transactions:
                self.logger.warning(f"Transaction {transaction_id} đã tồn tại")
                return False
            
            transaction = {
                'id': transaction_id,
                'initiator': initiator,
                'target': target,
                'start_time': time.time(),
                'state': ProtocolState.IDLE.value,
                'file_info': file_info or {},
                'messages': [],
                'errors': []
            }
            
            self.active_transactions[transaction_id] = transaction
            self.logger.info(f"Bắt đầu transaction: {transaction_id}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Lỗi bắt đầu transaction: {e}")
            return False

    def update_transaction(self, transaction_id: str, 
                          state: ProtocolState = None, 
                          message: ProtocolMessage = None,
                          error: str = None) -> bool:
        """
        Cập nhật thông tin giao dịch
        
        Args:
            transaction_id: ID giao dịch
            state: Trạng thái mới
            message: Message liên quan
            error: Lỗi (nếu có)
            
        Returns:
            bool: True nếu thành công
        """
        try:
            if transaction_id not in self.active_transactions:
                self.logger.warning(f"Transaction {transaction_id} không tồn tại")
                return False
            
            transaction = self.active_transactions[transaction_id]
            
            if state:
                transaction['state'] = state.value
            
            if message:
                transaction['messages'].append({
                    'timestamp': message.timestamp,
                    'type': message.type,
                    'source': message.source,
                    'destination': message.destination
                })
            
            if error:
                transaction['errors'].append({
                    'timestamp': time.time(),
                    'error': error
                })
            
            return True
            
        except Exception as e:
            self.logger.error(f"Lỗi cập nhật transaction: {e}")
            return False

    def complete_transaction(self, transaction_id: str, success: bool, 
                           result: Dict[str, Any] = None) -> bool:
        """
        Hoàn thành giao dịch
        
        Args:
            transaction_id: ID giao dịch
            success: Thành công hay thất bại
            result: Kết quả chi tiết
            
        Returns:
            bool: True nếu thành công
        """
        try:
            if transaction_id not in self.active_transactions:
                self.logger.warning(f"Transaction {transaction_id} không tồn tại")
                return False
            
            transaction = self.active_transactions.pop(transaction_id)
            transaction['end_time'] = time.time()
            transaction['duration'] = transaction['end_time'] - transaction['start_time']
            transaction['success'] = success
            transaction['result'] = result or {}
            
            self.completed_transactions[transaction_id] = transaction
            
            status = "THÀNH CÔNG" if success else "THẤT BẠI"
            self.logger.info(f"Hoàn thành transaction {transaction_id}: {status}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Lỗi hoàn thành transaction: {e}")
            return False

    # Message Handlers
    def _handle_hello(self, message) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        try:
            msg_dict = message if isinstance(message, dict) else message.to_dict()
            is_valid, error = self.validator.validate_hello_message(msg_dict)
            if not is_valid:
                return False, error, None
            if msg_dict.get('transaction_id'):
                self.update_transaction(msg_dict.get('transaction_id'), ProtocolState.HANDSHAKE, message)
            self.change_state(ProtocolState.HANDSHAKE, "Received Hello")
            response_data = {
                'message': 'Ready!',
                'receiver_id': self.component_id
            }
            return True, "Hello processed successfully", response_data
        except Exception as e:
            return False, f"Error handling Hello: {e}", None

    def _handle_ready(self, message) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        try:
            msg_dict = message if isinstance(message, dict) else message.to_dict()
            is_valid, error = self.validator.validate_ready_message(msg_dict)
            if not is_valid:
                return False, error, None
            if msg_dict.get('transaction_id'):
                self.update_transaction(msg_dict.get('transaction_id'), ProtocolState.HANDSHAKE, message)
            self.change_state(ProtocolState.KEY_EXCHANGE, "Received Ready")
            return True, "Ready processed successfully", None
        except Exception as e:
            return False, f"Error handling Ready: {e}", None

    def _handle_public_key(self, message) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        try:
            msg_dict = message if isinstance(message, dict) else message.to_dict()
            is_valid, error = self.validator.validate_public_key_message(msg_dict)
            if not is_valid:
                return False, error, None
            if msg_dict.get('transaction_id'):
                self.update_transaction(msg_dict.get('transaction_id'), ProtocolState.KEY_EXCHANGE, message)
            return True, "Public Key processed successfully", None
        except Exception as e:
            return False, f"Error handling Public Key: {e}", None

    def _handle_session_key(self, message) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        try:
            msg_dict = message if isinstance(message, dict) else message.to_dict()
            is_valid, error = self.validator.validate_session_key_message(msg_dict)
            if not is_valid:
                return False, error, None
            if msg_dict.get('transaction_id'):
                self.update_transaction(msg_dict.get('transaction_id'), ProtocolState.KEY_EXCHANGE, message)
            self.change_state(ProtocolState.FILE_TRANSFER, "Session Key received")
            return True, "Session Key processed successfully", None
        except Exception as e:
            return False, f"Error handling Session Key: {e}", None

    def _handle_file_data(self, message) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        try:
            msg_dict = message if isinstance(message, dict) else message.to_dict()
            is_valid, error = self.validator.validate_file_data_message(msg_dict)
            if not is_valid:
                return False, error, None
            if msg_dict.get('transaction_id'):
                self.update_transaction(msg_dict.get('transaction_id'), ProtocolState.FILE_TRANSFER, message)
            self.change_state(ProtocolState.ACK_WAIT, "File Data received")
            return True, "File Data processed successfully", None
        except Exception as e:
            return False, f"Error handling File Data: {e}", None

    def _handle_ack(self, message) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        try:
            msg_dict = message if isinstance(message, dict) else message.to_dict()
            is_valid, error = self.validator.validate_ack_message(msg_dict)
            if not is_valid:
                return False, error, None
            if msg_dict.get('transaction_id'):
                self.update_transaction(msg_dict.get('transaction_id'), ProtocolState.COMPLETED, message)
            self.change_state(ProtocolState.COMPLETED, "Received ACK")
            if msg_dict.get('transaction_id'):
                self.complete_transaction(msg_dict.get('transaction_id'), True, {
                    'status': 'success',
                    'message': msg_dict.get('data', {}).get('message', 'File received successfully')
                })
            return True, "ACK processed successfully", None
        except Exception as e:
            return False, f"Error handling ACK: {e}", None

    def _handle_nack(self, message) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        try:
            msg_dict = message if isinstance(message, dict) else message.to_dict()
            is_valid, error = self.validator.validate_nack_message(msg_dict)
            if not is_valid:
                return False, error, None
            if msg_dict.get('transaction_id'):
                self.update_transaction(msg_dict.get('transaction_id'), ProtocolState.ERROR, message)
            self.change_state(ProtocolState.ERROR, "Received NACK")
            if msg_dict.get('transaction_id'):
                self.complete_transaction(msg_dict.get('transaction_id'), False, {
                    'status': 'failed',
                    'error': msg_dict.get('data', {}).get('error', 'Unknown error')
                })
            return True, "NACK processed successfully", None
        except Exception as e:
            return False, f"Error handling NACK: {e}", None

    def _handle_disconnect(self, message) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        try:
            self.change_state(ProtocolState.IDLE, "Received Disconnect")
            return True, "Disconnect processed successfully", None
        except Exception as e:
            return False, f"Error handling Disconnect: {e}", None

    def _handle_heartbeat(self, message) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        try:
            response_data = {
                'timestamp': time.time(),
                'component_id': self.component_id
            }
            return True, "Heartbeat processed successfully", response_data
        except Exception as e:
            return False, f"Error handling Heartbeat: {e}", None

    def get_statistics(self) -> Dict[str, Any]:
        """Lấy thống kê protocol"""
        runtime = time.time() - self.stats['start_time']
        
        return {
            **self.stats,
            'runtime_seconds': runtime,
            'current_state': self.current_state.value,
            'active_transactions': len(self.active_transactions),
            'completed_transactions': len(self.completed_transactions),
            'messages_per_second': self.stats['messages_processed'] / runtime if runtime > 0 else 0
        }

    def get_transaction_info(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Lấy thông tin giao dịch"""
        if transaction_id in self.active_transactions:
            return self.active_transactions[transaction_id]
        elif transaction_id in self.completed_transactions:
            return self.completed_transactions[transaction_id]
        return None

    def cleanup(self):
        """Dọn dẹp protocol handler"""
        self.logger.info(f"=== PROTOCOL HANDLER CLEANUP: {self.component_id} ===")
        
        # Log statistics
        stats = self.get_statistics()
        self.logger.info(f"Messages processed: {stats['messages_processed']}")
        self.logger.info(f"Messages sent: {stats['messages_sent']}")
        self.logger.info(f"Messages received: {stats['messages_received']}")
        self.logger.info(f"Errors: {stats['errors']}")
        self.logger.info(f"State changes: {stats['state_changes']}")
        self.logger.info(f"Active transactions: {stats['active_transactions']}")
        self.logger.info(f"Completed transactions: {stats['completed_transactions']}")


# Factory function
def create_protocol_handler(component_id: str, logger: Optional[Logger] = None) -> ProtocolHandler:
    """
    Factory function để tạo Protocol Handler
    
    Args:
        component_id: ID của component
        logger: Logger instance
        
    Returns:
        ProtocolHandler instance
    """
    return ProtocolHandler(component_id, logger) 