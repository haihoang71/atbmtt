"""
Message Validator Component
Validate các message và data cho Legal Document Transfer System
Hỗ trợ: Message validation, data validation, format checking
"""

import re
import json
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime


class MessageValidator:
    """
    Message validator class cho hệ thống truyền tài liệu pháp lý
    Validate các message và data với các rules cụ thể
    """
    
    def __init__(self):
        """Khởi tạo MessageValidator"""
        # Regex patterns
        self.patterns = {
            'transaction_id': r'^tx_\d+_[a-zA-Z0-9_]+$',
            'sender_id': r'^[a-zA-Z0-9_]+$',
            'receiver_id': r'^[a-zA-Z0-9_]+$',
            'filename': r'^[a-zA-Z0-9_.-]+$',
            'base64': r'^[A-Za-z0-9+/]*={0,2}$',
            'hex': r'^[0-9a-fA-F]+$',
            'ip_address': r'^(\d{1,3}\.){3}\d{1,3}$',
            'port': r'^\d{1,5}$'
        }
        
        # Validation rules
        self.rules = {
            'max_filename_length': 255,
            'max_message_size': 10 * 1024 * 1024,  # 10MB
            'max_transaction_id_length': 100,
            'max_sender_id_length': 50,
            'max_receiver_id_length': 50,
            'min_port': 1024,
            'max_port': 65535
        }

    def validate_message_structure(self, message: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate cấu trúc message cơ bản
        
        Args:
            message: Message cần validate
            
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        try:
            # Kiểm tra message có phải dict không
            if not isinstance(message, dict):
                return False, "Message phải là dictionary"
            
            # Kiểm tra các field bắt buộc
            required_fields = ['type', 'source', 'destination', 'data']
            for field in required_fields:
                if field not in message:
                    return False, f"Thiếu field bắt buộc: {field}"
            
            # Kiểm tra type
            if not isinstance(message['type'], str):
                return False, "Field 'type' phải là string"
            
            # Kiểm tra source và destination
            if not isinstance(message['source'], str):
                return False, "Field 'source' phải là string"
            
            if not isinstance(message['destination'], str):
                return False, "Field 'destination' phải là string"
            
            # Kiểm tra data
            if not isinstance(message['data'], dict):
                return False, "Field 'data' phải là dictionary"
            
            return True, "Message structure hợp lệ"
            
        except Exception as e:
            return False, f"Lỗi validate message structure: {e}"

    def validate_hello_message(self, message: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate Hello message
        
        Args:
            message: Hello message
            
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        try:
            # Validate structure cơ bản
            is_valid, error = self.validate_message_structure(message)
            if not is_valid:
                return False, error
            
            # Kiểm tra type
            if message['type'] != 'HELLO':
                return False, "Message type phải là HELLO"
            
            # Kiểm tra data
            data = message['data']
            if 'message' not in data:
                return False, "Thiếu field 'message' trong data"
            
            if data['message'] != 'Hello!':
                return False, "Message phải là 'Hello!'"
            
            if 'sender_id' not in data:
                return False, "Thiếu field 'sender_id' trong data"
            
            # Validate sender_id
            if not self.validate_sender_id(data['sender_id']):
                return False, "sender_id không hợp lệ"
            
            return True, "Hello message hợp lệ"
            
        except Exception as e:
            return False, f"Lỗi validate Hello message: {e}"

    def validate_ready_message(self, message: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate Ready message
        
        Args:
            message: Ready message
            
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        try:
            # Validate structure cơ bản
            is_valid, error = self.validate_message_structure(message)
            if not is_valid:
                return False, error
            
            # Kiểm tra type
            if message['type'] != 'READY':
                return False, "Message type phải là READY"
            
            # Kiểm tra data
            data = message['data']
            if 'message' not in data:
                return False, "Thiếu field 'message' trong data"
            
            if data['message'] != 'Ready!':
                return False, "Message phải là 'Ready!'"
            
            if 'receiver_id' not in data:
                return False, "Thiếu field 'receiver_id' trong data"
            
            # Validate receiver_id
            if not self.validate_receiver_id(data['receiver_id']):
                return False, "receiver_id không hợp lệ"
            
            return True, "Ready message hợp lệ"
            
        except Exception as e:
            return False, f"Lỗi validate Ready message: {e}"

    def validate_public_key_message(self, message: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate Public Key message
        
        Args:
            message: Public Key message
            
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        try:
            # Validate structure cơ bản
            is_valid, error = self.validate_message_structure(message)
            if not is_valid:
                return False, error
            
            # Kiểm tra type
            if message['type'] != 'PUBLIC_KEY':
                return False, "Message type phải là PUBLIC_KEY"
            
            # Kiểm tra data
            data = message['data']
            if 'public_key' not in data:
                return False, "Thiếu field 'public_key' trong data"
            
            # Validate public key format (PEM)
            public_key = data['public_key']
            if not isinstance(public_key, str):
                return False, "public_key phải là string"
            
            if not public_key.startswith('-----BEGIN PUBLIC KEY-----'):
                return False, "public_key phải có format PEM"
            
            if not public_key.endswith('-----END PUBLIC KEY-----'):
                return False, "public_key phải có format PEM"
            
            return True, "Public Key message hợp lệ"
            
        except Exception as e:
            return False, f"Lỗi validate Public Key message: {e}"

    def validate_session_key_message(self, message: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate Session Key message
        
        Args:
            message: Session Key message
            
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        try:
            # Validate structure cơ bản
            is_valid, error = self.validate_message_structure(message)
            if not is_valid:
                return False, error
            
            # Kiểm tra type
            if message['type'] != 'SESSION_KEY':
                return False, "Message type phải là SESSION_KEY"
            
            # Kiểm tra data
            data = message['data']
            if 'encrypted_session_key' not in data:
                return False, "Thiếu field 'encrypted_session_key' trong data"
            
            # Validate encrypted session key (base64)
            encrypted_key = data['encrypted_session_key']
            if not isinstance(encrypted_key, str):
                return False, "encrypted_session_key phải là string"
            
            if not self.validate_base64(encrypted_key):
                return False, "encrypted_session_key phải có format base64"
            
            return True, "Session Key message hợp lệ"
            
        except Exception as e:
            return False, f"Lỗi validate Session Key message: {e}"

    def validate_file_data_message(self, message: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate File Data message
        
        Args:
            message: File Data message
            
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        try:
            # Validate structure cơ bản
            is_valid, error = self.validate_message_structure(message)
            if not is_valid:
                return False, error
            
            # Kiểm tra type
            if message['type'] != 'FILE_DATA':
                return False, "Message type phải là FILE_DATA"
            
            # Kiểm tra data
            data = message['data']
            required_fields = ['iv', 'cipher', 'hash', 'sig', 'metadata']
            
            for field in required_fields:
                if field not in data:
                    return False, f"Thiếu field '{field}' trong data"
            
            # Validate IV (base64)
            if not self.validate_base64(data['iv']):
                return False, "IV phải có format base64"
            
            # Validate cipher (base64)
            if not self.validate_base64(data['cipher']):
                return False, "Cipher phải có format base64"
            
            # Validate hash (hex)
            if not self.validate_hex(data['hash']):
                return False, "Hash phải có format hex"
            
            # Validate signature (base64)
            if not self.validate_base64(data['sig']):
                return False, "Signature phải có format base64"
            
            # Validate metadata
            metadata = data['metadata']
            if not isinstance(metadata, dict):
                return False, "Metadata phải là dictionary"
            
            # Validate metadata fields
            metadata_validation = self.validate_metadata(metadata)
            if not metadata_validation[0]:
                return metadata_validation
            
            return True, "File Data message hợp lệ"
            
        except Exception as e:
            return False, f"Lỗi validate File Data message: {e}"

    def validate_ack_message(self, message: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate ACK message
        
        Args:
            message: ACK message
            
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        try:
            # Validate structure cơ bản
            is_valid, error = self.validate_message_structure(message)
            if not is_valid:
                return False, error
            
            # Kiểm tra type
            if message['type'] != 'ACK':
                return False, "Message type phải là ACK"
            
            # Kiểm tra data
            data = message['data']
            if 'message' not in data:
                return False, "Thiếu field 'message' trong data"
            
            if 'transaction_id' not in data:
                return False, "Thiếu field 'transaction_id' trong data"
            
            # Validate transaction_id
            if not self.validate_transaction_id(data['transaction_id']):
                return False, "transaction_id không hợp lệ"
            
            return True, "ACK message hợp lệ"
            
        except Exception as e:
            return False, f"Lỗi validate ACK message: {e}"

    def validate_nack_message(self, message: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate NACK message
        
        Args:
            message: NACK message
            
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        try:
            # Validate structure cơ bản
            is_valid, error = self.validate_message_structure(message)
            if not is_valid:
                return False, error
            
            # Kiểm tra type
            if message['type'] != 'NACK':
                return False, "Message type phải là NACK"
            
            # Kiểm tra data
            data = message['data']
            if 'error' not in data:
                return False, "Thiếu field 'error' trong data"
            
            if 'transaction_id' not in data:
                return False, "Thiếu field 'transaction_id' trong data"
            
            # Validate transaction_id
            if not self.validate_transaction_id(data['transaction_id']):
                return False, "transaction_id không hợp lệ"
            
            return True, "NACK message hợp lệ"
            
        except Exception as e:
            return False, f"Lỗi validate NACK message: {e}"

    def validate_metadata(self, metadata: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate metadata
        
        Args:
            metadata: Metadata dictionary
            
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        try:
            required_fields = ['filename', 'timestamp', 'transaction_id', 'file_size', 'sender_id']
            
            for field in required_fields:
                if field not in metadata:
                    return False, f"Thiếu field '{field}' trong metadata"
            
            # Validate filename
            if not self.validate_filename(metadata['filename']):
                return False, "filename không hợp lệ"
            
            # Validate timestamp
            if not isinstance(metadata['timestamp'], (int, float)):
                return False, "timestamp phải là số"
            
            # Validate transaction_id
            if not self.validate_transaction_id(metadata['transaction_id']):
                return False, "transaction_id không hợp lệ"
            
            # Validate file_size
            if not isinstance(metadata['file_size'], int) or metadata['file_size'] < 0:
                return False, "file_size phải là số nguyên không âm"
            
            # Validate sender_id
            if not self.validate_sender_id(metadata['sender_id']):
                return False, "sender_id không hợp lệ"
            
            return True, "Metadata hợp lệ"
            
        except Exception as e:
            return False, f"Lỗi validate metadata: {e}"

    # Helper validation methods
    def validate_transaction_id(self, transaction_id: str) -> bool:
        """Validate transaction ID"""
        if not isinstance(transaction_id, str):
            return False
        if len(transaction_id) > self.rules['max_transaction_id_length']:
            return False
        return bool(re.match(self.patterns['transaction_id'], transaction_id))

    def validate_sender_id(self, sender_id: str) -> bool:
        """Validate sender ID"""
        if not isinstance(sender_id, str):
            return False
        if len(sender_id) > self.rules['max_sender_id_length']:
            return False
        return bool(re.match(self.patterns['sender_id'], sender_id))

    def validate_receiver_id(self, receiver_id: str) -> bool:
        """Validate receiver ID"""
        if not isinstance(receiver_id, str):
            return False
        if len(receiver_id) > self.rules['max_receiver_id_length']:
            return False
        return bool(re.match(self.patterns['receiver_id'], receiver_id))

    def validate_filename(self, filename: str) -> bool:
        """Validate filename"""
        if not isinstance(filename, str):
            return False
        if len(filename) > self.rules['max_filename_length']:
            return False
        return bool(re.match(self.patterns['filename'], filename))

    def validate_base64(self, data: str) -> bool:
        """Validate base64 format"""
        if not isinstance(data, str):
            return False
        return bool(re.match(self.patterns['base64'], data))

    def validate_hex(self, data: str) -> bool:
        """Validate hex format"""
        if not isinstance(data, str):
            return False
        return bool(re.match(self.patterns['hex'], data))

    def validate_ip_address(self, ip: str) -> bool:
        """Validate IP address"""
        if not isinstance(ip, str):
            return False
        if not re.match(self.patterns['ip_address'], ip):
            return False
        
        # Kiểm tra từng octet
        octets = ip.split('.')
        for octet in octets:
            if not (0 <= int(octet) <= 255):
                return False
        
        return True

    def validate_port(self, port: str) -> bool:
        """Validate port number"""
        if not isinstance(port, str):
            return False
        if not re.match(self.patterns['port'], port):
            return False
        
        port_num = int(port)
        return self.rules['min_port'] <= port_num <= self.rules['max_port']


# Factory function
def create_validator() -> MessageValidator:
    """
    Factory function để tạo MessageValidator
    
    Returns:
        MessageValidator instance
    """
    return MessageValidator()
