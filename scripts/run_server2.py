

import sys
import os
from pathlib import Path
import argparse
import threading

# Thêm thư mục gốc vào Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(str(Path(__file__).parent.parent / "src"))

from src.components.server_intermediate import create_server2
from src.gui.server_gui import ServerGUI

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Server 2")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8002)
    parser.add_argument("--upstream-host", required=True)
    parser.add_argument("--upstream-port", type=int, required=True)
    args = parser.parse_args()

    gui = ServerGUI(server_name="Server 2")
    server = create_server2(
        host=args.host,
        port=args.port,
        upstream_host=args.upstream_host,
        upstream_port=args.upstream_port,
        log_callback=gui.log
    )

    if server.start():
        threading.Thread(target=server.run, daemon=True).start()
        gui.run()
    else:
        print("Không thể khởi động Server 2.")

if __name__ == '__main__':
    main() 