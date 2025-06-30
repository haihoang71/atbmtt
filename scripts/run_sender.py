#!/usr/bin/env python3
"""
Script chạy Sender với GUI liên tục
"""

import sys
import os
from pathlib import Path
import argparse
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(str(Path(__file__).parent.parent / "src"))

from src.components.sender import Sender
from src.gui.sender_gui import SenderGUI

class SenderApp:
    def __init__(self, server1_host="127.0.0.1", server1_port=8001):
        self.server1_host = server1_host
        self.server1_port = server1_port
        self.sender = None
        self.is_connected = False
        
        # Tạo GUI
        self.gui = SenderGUI({
            "server1_host": server1_host,
            "server1_port": server1_port
        })
        
        # Kết nối GUI với logic
        self.gui.set_handshake_callback(self.perform_handshake)
        self.gui.set_send_file_callback(self.send_file)

    def perform_handshake(self):
        """Thực hiện handshake khi nhấn nút"""
        def do_handshake():
            try:
                self.gui.log("info", "Bắt đầu handshake...")
                self.sender = Sender(
                    server1_host=self.server1_host,
                    server1_port=self.server1_port,
                    log_callback=self.gui.log
                )
                
                # Thực hiện handshake
                if self.sender.perform_handshake():
                    self.is_connected = True
                    self.gui.log("info", "Handshake thành công! Sẵn sàng gửi file.")
                    self.gui.enable_file_send(True)
                else:
                    self.gui.log("error", "Handshake thất bại. Hãy thử lại.")
                    self.gui.enable_file_send(False)
            except Exception as e:
                self.gui.log("error", f"Lỗi handshake: {e}")
                self.gui.enable_file_send(False)
        
        threading.Thread(target=do_handshake, daemon=True).start()

    def send_file(self, file_path):
        """Gửi file khi được chọn"""
        if not self.sender:
            self.gui.log("error", "Sender chưa khởi tạo. Hãy thực hiện handshake trước!")
            return
        def do_send():
            try:
                self.gui.log("info", f"Bắt đầu gửi file: {file_path}")
                # Lấy public key từ receiver
                if not self.sender.request_public_key():
                    self.gui.log("error", "Không thể lấy public key từ receiver")
                    return
                # Trao đổi khóa
                if not self.sender.exchange_keys():
                    self.gui.log("error", "Trao đổi khóa thất bại")
                    return
                # Mã hóa và gửi file
                if not self.sender.encrypt_and_send_file(file_path):
                    self.gui.log("error", "Gửi file thất bại")
                    return
                # Chờ ACK/NACK
                success, message = self.sender.wait_for_acknowledgment()
                if success:
                    self.gui.log("info", "Gửi file thành công!")
                else:
                    self.gui.log("error", f"Gửi file thất bại: {message}")
            except Exception as e:
                self.gui.log("error", f"Lỗi gửi file: {e}")
        threading.Thread(target=do_send, daemon=True).start()

    def run(self):
        """Chạy ứng dụng"""
        self.gui.run()

def main():
    parser = argparse.ArgumentParser(description="Sender with GUI")
    parser.add_argument("--server1-host", default="127.0.0.1")
    parser.add_argument("--server1-port", type=int, default=8001)
    args = parser.parse_args()

    app = SenderApp(args.server1_host, args.server1_port)
    app.run()

if __name__ == "__main__":
    main() 