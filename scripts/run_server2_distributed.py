"""
Script chạy Server 2
Server trung gian thứ hai: Server 1 -> Server 2 -> Receiver
"""

import sys
from pathlib import Path
import argparse
import threading
import logging
sys.path.append(str(Path(__file__).parent.parent / "src"))
sys.path.append(str(Path(__file__).parent.parent))

from config.network_config import get_config
from src.components.server_intermediate import create_server2
from src.gui.server_gui import ServerGUI, TkinterLogHandler

def main():
    parser = argparse.ArgumentParser(description="Server2 (Distributed)")
    parser.add_argument("--host", default=None, help="IP lắng nghe của Server2")
    parser.add_argument("--upstream-host", default=None, help="IP của Receiver")
    args = parser.parse_args()

    config = get_config("distributed_4machines")["server2"]
    if args.host:
        config["host"] = args.host
    if args.upstream_host:
        config["upstream_host"] = args.upstream_host

    gui = ServerGUI(server_name="Server 2")
    tk_handler = TkinterLogHandler(gui.log)
    tk_handler.setLevel(logging.DEBUG)
    server = create_server2(
        host=config["host"],
        port=config["port"],
        upstream_host=config["upstream_host"],
        upstream_port=config["upstream_port"],
        log_callback=gui.log
    )
    server.logger.logger.addHandler(tk_handler)
    server.logger.logger.propagate = True
    server.socket_handler.logger.logger.addHandler(tk_handler)
    server.socket_handler.logger.logger.propagate = True
    server.protocol_handler.logger.logger.addHandler(tk_handler)
    server.protocol_handler.logger.logger.propagate = True
    if not server.start():
        print("Không thể khởi động Server 2")
        return
    threading.Thread(target=server.run, daemon=True).start()
    gui.run()

if __name__ == "__main__":
    main() 