import sys
from pathlib import Path
import argparse
import threading
sys.path.append(str(Path(__file__).parent.parent / "src"))
sys.path.append(str(Path(__file__).parent.parent))

from config.network_config import get_config
from src.components.server_intermediate import create_server1
from src.gui.server_gui import ServerGUI

def main():
    parser = argparse.ArgumentParser(description="Server1 (Distributed)")
    parser.add_argument("--host", default=None, help="IP lắng nghe của Server1")
    parser.add_argument("--upstream-host", default=None, help="IP của Server2")
    args = parser.parse_args()

    config = get_config("distributed_4machines")["server1"]
    if args.host:
        config["host"] = args.host
    if args.upstream_host:
        config["upstream_host"] = args.upstream_host

    server = create_server1(
        host=config["host"],
        port=config["port"],
        upstream_host=config["upstream_host"],
        upstream_port=config["upstream_port"]
    )
    
    if not server.start():
        print("Không thể khởi động Server 1")
        return
        
    threading.Thread(target=server.run, daemon=True).start()
    gui = ServerGUI(server_name="Server 1")
    gui.run()

if __name__ == "__main__":
    main() 