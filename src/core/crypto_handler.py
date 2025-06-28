"""
Crypto Handler - Xử lý tất cả các chức năng mã hóa và bảo mật
Yêu cầu: DES encryption, RSA 2048-bit (PKCS#1 v1.5 + SHA-512), SHA-512 hashing
"""

import os
import json
import base64
import hashlib
import secrets
from datetime import datetime
from typing import Tuple, Dict, Any, Optional

from Crypto.Cipher import DES, PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA512
from Crypto.Signature import pkcs1_15
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad


class CryptoHandler:
    """
    Xử lý tất cả các chức năng mã hóa và bảo mật cho hệ thống truyền tài liệu pháp lý
    """
    
    def __init__(self, logger=None):
        self.des_key_size = 8
        self.rsa_key_size = 2048
        self.iv_size = 8
        self.logger = logger
        
    # ==================== RSA KEY MANAGEMENT ====================
    
    def generate_rsa_keypair(self) -> Tuple[RSA.RsaKey, RSA.RsaKey]:
        """
        Tạo cặp khóa RSA 2048-bit
        Returns: (private_key, public_key)
        """
        try:
            private_key = RSA.generate(self.rsa_key_size)
            public_key = private_key.publickey()
            if self.logger:
                self.logger.info(f"[CRYPTO] Generated RSA {self.rsa_key_size}-bit keypair")
            return private_key, public_key
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[ERROR] Failed to generate RSA keypair: {e}")
            raise
    
    def export_key_to_pem(self, key: RSA.RsaKey, is_private: bool = False) -> str:
        """
        Xuất khóa RSA ra định dạng PEM
        """
        try:
            if is_private:
                return key.export_key().decode('utf-8')
            else:
                return key.publickey().export_key().decode('utf-8')
        except Exception as e:
            if self.logger:
                self.logger.error(f"[ERROR] Failed to export key to PEM: {e}")
            raise
    
    def import_key_from_pem(self, pem_data: str) -> RSA.RsaKey:
        """
        Nhập khóa RSA từ định dạng PEM
        """
        try:
            return RSA.import_key(pem_data.encode('utf-8'))
        except Exception as e:
            if self.logger:
                self.logger.error(f"[ERROR] Failed to import key from PEM: {e}")
            raise
    
    # ==================== SESSION KEY MANAGEMENT ====================
    
    def generate_session_key(self) -> bytes:
        """
        Tạo session key ngẫu nhiên cho DES (8 bytes)
        """
        try:
            session_key = get_random_bytes(self.des_key_size)
            if self.logger:
                self.logger.info(f"[CRYPTO] Generated DES session key: {len(session_key)} bytes")
            return session_key
        except Exception as e:
            if self.logger:
                self.logger.error(f"[ERROR] Failed to generate session key: {e}")
            raise
    
    def encrypt_session_key(self, session_key: bytes, public_key: RSA.RsaKey) -> bytes:
        """
        Mã hóa session key bằng RSA PKCS#1 v1.5
        """
        try:
            cipher = PKCS1_v1_5.new(public_key)
            encrypted_key = cipher.encrypt(session_key)
            
            if self.logger:
                self.logger.info(f"[CRYPTO] Encrypted session key with RSA: {len(encrypted_key)} bytes")
            return encrypted_key
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[ERROR] Failed to encrypt session key: {e}")
            raise
    
    def decrypt_session_key(self, encrypted_key: bytes, private_key: RSA.RsaKey) -> bytes:
        """
        Giải mã session key bằng RSA PKCS#1 v1.5
        """
        try:
            cipher = PKCS1_v1_5.new(private_key)
            session_key = cipher.decrypt(encrypted_key, None)
            
            if session_key is None:
                raise ValueError("Failed to decrypt session key")
            
            if self.logger:
                self.logger.info(f"[CRYPTO] Decrypted session key: {len(session_key)} bytes")
            return session_key
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[ERROR] Failed to decrypt session key: {e}")
            raise
    
    # ==================== DES ENCRYPTION/DECRYPTION ====================
    
    def generate_iv(self) -> bytes:
        """
        Tạo IV ngẫu nhiên cho DES (8 bytes)
        """
        try:
            iv = get_random_bytes(self.iv_size)
            if self.logger:
                self.logger.info(f"[CRYPTO] Generated DES IV: {len(iv)} bytes")
            return iv
        except Exception as e:
            if self.logger:
                self.logger.error(f"[ERROR] Failed to generate IV: {e}")
            raise
    
    def encrypt_file_des(self, file_data: bytes, session_key: bytes, iv: bytes) -> bytes:
        """
        Mã hóa dữ liệu file bằng DES
        """
        try:
            cipher = DES.new(session_key, DES.MODE_CBC, iv)
            padded_data = pad(file_data, DES.block_size)
            ciphertext = cipher.encrypt(padded_data)
            
            if self.logger:
                self.logger.info(f"[CRYPTO] DES encryption completed: {len(file_data)} -> {len(ciphertext)} bytes")
            return ciphertext
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[ERROR] DES encryption failed: {e}")
            raise
    
    def decrypt_file_des(self, ciphertext: bytes, session_key: bytes, iv: bytes) -> bytes:
        """
        Giải mã dữ liệu file bằng DES
        """
        try:
            cipher = DES.new(session_key, DES.MODE_CBC, iv)
            padded_data = cipher.decrypt(ciphertext)
            file_data = unpad(padded_data, DES.block_size)
            
            if self.logger:
                self.logger.info(f"[CRYPTO] DES decryption completed: {len(ciphertext)} -> {len(file_data)} bytes")
            return file_data
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[ERROR] DES decryption failed: {e}")
            raise
    
    # ==================== HASHING (SHA-512) ====================
    
    def calculate_sha512(self, data: bytes) -> str:
        """
        Tính hash SHA-512 của dữ liệu
        Returns: hex string
        """
        try:
            hash_obj = hashlib.sha512()
            hash_obj.update(data)
            hash_hex = hash_obj.hexdigest()
            
            if self.logger:
                self.logger.info(f"[CRYPTO] SHA-512 hash calculated: {len(hash_hex)} chars")
            return hash_hex
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[ERROR] SHA-512 calculation failed: {e}")
            raise
    
    def calculate_file_integrity_hash(self, iv: bytes, ciphertext: bytes) -> str:
        """
        Tính hash toàn vẹn: SHA-512(IV || ciphertext)
        """
        try:
            combined_data = iv + ciphertext
            integrity_hash = self.calculate_sha512(combined_data)
            
            if self.logger:
                self.logger.info(f"[CRYPTO] File integrity hash calculated")
            return integrity_hash
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[ERROR] File integrity hash calculation failed: {e}")
            raise
    
    def verify_file_integrity(self, iv: bytes, ciphertext: bytes, expected_hash: str) -> bool:
        """
        Kiểm tra tính toàn vẹn của file
        """
        try:
            calculated_hash = self.calculate_file_integrity_hash(iv, ciphertext)
            is_valid = calculated_hash == expected_hash
            
            if self.logger:
                self.logger.info(f"[CRYPTO] File integrity check: {'PASSED' if is_valid else 'FAILED'}")
            return is_valid
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[ERROR] File integrity verification failed: {e}")
            return False
    
    # ==================== DIGITAL SIGNATURE (RSA + SHA-512) ====================
    
    def create_metadata(self, filename: str, transaction_id: str) -> Dict[str, Any]:
        """
        Tạo metadata để ký số
        """
        metadata = {
            'filename': filename,
            'timestamp': datetime.now().isoformat(),
            'transaction_id': transaction_id
        }
        
        if self.logger:
            self.logger.info(f"[CRYPTO] Created metadata for file: {filename}")
        return metadata
    
    def sign_metadata(self, metadata: Dict[str, Any], private_key: RSA.RsaKey) -> str:
        """
        Ký metadata bằng RSA + SHA-512
        """
        try:
            # Chuyển metadata thành chuỗi JSON để ký
            metadata_str = json.dumps(metadata, sort_keys=True)
            metadata_bytes = metadata_str.encode('utf-8')
            
            hash_obj = SHA512.new(metadata_bytes)
            signature = pkcs1_15.new(private_key).sign(hash_obj)
            signature_b64 = base64.b64encode(signature).decode('utf-8')
            
            if self.logger:
                self.logger.info(f"[CRYPTO] Metadata signed successfully: {len(signature_b64)} chars")
            return signature_b64
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[ERROR] Metadata signing failed: {e}")
            raise
    
    def verify_signature(self, metadata: Dict[str, Any], signature_b64: str, public_key: RSA.RsaKey) -> bool:
        """
        Xác thực chữ ký metadata
        """
        try:
            # Khôi phục signature từ base64
            signature = base64.b64decode(signature_b64.encode('utf-8'))
            
            # Tạo lại hash từ metadata
            metadata_str = json.dumps(metadata, sort_keys=True)
            metadata_bytes = metadata_str.encode('utf-8')
            hash_obj = SHA512.new(metadata_bytes)
            
            # Xác thực chữ ký
            pkcs1_15.new(public_key).verify(hash_obj, signature)
            
            if self.logger:
                self.logger.info(f"[CRYPTO] Signature verification: PASSED")
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[CRYPTO] Signature verification: FAILED - {e}")
            return False
    
    # ==================== UTILITY FUNCTIONS ====================
    
    def encode_base64(self, data: bytes) -> str:
        """
        Mã hóa dữ liệu thành base64
        """
        return base64.b64encode(data).decode('utf-8')
    
    def decode_base64(self, data_str: str) -> bytes:
        """
        Giải mã dữ liệu từ base64
        """
        return base64.b64decode(data_str.encode('utf-8'))
    
    def generate_transaction_id(self) -> str:
        """
        Tạo ID giao dịch duy nhất
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        random_part = secrets.token_hex(4)
        transaction_id = f"TX_{timestamp}_{random_part}"
        
        if self.logger:
            self.logger.info(f"[CRYPTO] Generated transaction ID: {transaction_id}")
        return transaction_id
    
    # ==================== HIGH-LEVEL FUNCTIONS ====================
    
    def encrypt_file_complete(self, file_data: bytes, public_key: RSA.RsaKey, 
                            filename: str, sender_private_key: RSA.RsaKey) -> Dict[str, Any]:
        """
        Mã hóa file hoàn chỉnh theo quy trình của đề tài
        Returns: Dictionary chứa tất cả dữ liệu cần thiết để truyền
        """
        try:
            if self.logger:
                self.logger.info(f"[CRYPTO] Starting complete file encryption for: {filename}")
            
            # 1. Tạo session key và IV
            session_key = self.generate_session_key()
            iv = self.generate_iv()
            
            # 2. Mã hóa file bằng DES
            ciphertext = self.encrypt_file_des(file_data, session_key, iv)
            
            # 3. Tính hash toàn vẹn
            integrity_hash = self.calculate_file_integrity_hash(iv, ciphertext)
            
            # 4. Mã hóa session key bằng RSA
            encrypted_session_key = self.encrypt_session_key(session_key, public_key)
            
            # 5. Tạo metadata và ký
            transaction_id = self.generate_transaction_id()
            metadata = self.create_metadata(filename, transaction_id)
            signature = self.sign_metadata(metadata, sender_private_key)
            
            # 6. Tạo gói tin hoàn chỉnh
            packet = {
                'metadata': metadata,
                'encrypted_session_key': self.encode_base64(encrypted_session_key),
                'iv': self.encode_base64(iv),
                'cipher': self.encode_base64(ciphertext),
                'hash': integrity_hash,
                'signature': signature
            }
            
            if self.logger:
                self.logger.info(f"[CRYPTO] File encryption completed successfully")
            return packet
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[ERROR] Complete file encryption failed: {e}")
            raise
    
    def decrypt_file_complete(self, packet: Dict[str, Any], private_key: RSA.RsaKey,
                            sender_public_key: RSA.RsaKey) -> Tuple[bytes, bool]:
        """
        Giải mã file hoàn chỉnh và xác thực
        Returns: (file_data, is_valid)
        """
        try:
            if self.logger:
                self.logger.info(f"[CRYPTO] Starting complete file decryption")
            
            # 1. Giải mã các thành phần từ base64
            encrypted_session_key = self.decode_base64(packet['encrypted_session_key'])
            iv = self.decode_base64(packet['iv'])
            ciphertext = self.decode_base64(packet['cipher'])
            
            # 2. Xác thực chữ ký metadata
            signature_valid = self.verify_signature(
                packet['metadata'], 
                packet['signature'], 
                sender_public_key
            )
            
            if not signature_valid:
                if self.logger:
                    self.logger.error("[ERROR] Signature verification failed")
                return b'', False
            
            # 3. Kiểm tra tính toàn vẹn
            integrity_valid = self.verify_file_integrity(iv, ciphertext, packet['hash'])
            
            if not integrity_valid:
                if self.logger:
                    self.logger.error("[ERROR] File integrity check failed")
                return b'', False
            
            # 4. Giải mã session key
            session_key = self.decrypt_session_key(encrypted_session_key, private_key)
            
            # 5. Giải mã file
            file_data = self.decrypt_file_des(ciphertext, session_key, iv)
            
            if self.logger:
                self.logger.info(f"[CRYPTO] File decryption completed successfully")
            return file_data, True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[ERROR] Complete file decryption failed: {e}")
            return b'', False