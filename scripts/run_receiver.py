#!/usr/bin/env python3
"""
Script chạy Receiver
Người nhận tài liệu pháp lý: Server 2 -> Receiver
"""

import sys
import os
import argparse
from pathlib import Path
import threading

# Thêm thư mục gốc vào Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(str(Path(__file__).parent.parent / "src"))

from config.network_config import get_config
from src.components.receiver import Receiver
from src.gui.receiver_gui import ReceiverGUI


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Receiver")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8003)
    
    args = parser.parse_args()
    
    output_dir = "./data/output"

    gui = ReceiverGUI(output_dir=output_dir)
    receiver = Receiver(
        host=args.host,
        port=args.port,
        output_dir=output_dir,
        log_callback=gui.log,
        on_new_file=lambda: gui.root.after(0, gui.refresh_file_list)
    )

    threading.Thread(target=receiver.start_receiver, daemon=True).start()
    gui.run()


class ReceiverApp:
    def __init__(self, config):
        self.gui = ReceiverGUI(output_dir="data/output")
        self.receiver = Receiver(
            host=config["host"],
            port=config["port"],
            output_dir="data/output",
            log_callback=self.log_to_gui
        )

    def log_to_gui(self, level, msg):
        self.gui.log(level, msg)

    def run(self):
        threading.Thread(target=self.receiver.start_receiver, daemon=True).start()
        self.gui.run()


if __name__ == "__main__":
    main() 