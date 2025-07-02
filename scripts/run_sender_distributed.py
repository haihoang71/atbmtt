import sys
from pathlib import Path
import argparse
sys.path.append(str(Path(__file__).parent.parent / "src"))
sys.path.append(str(Path(__file__).parent.parent))

from config.network_config import get_config
from src.components.sender import Sender
from src.gui.sender_gui import SenderGUI

def main():
    parser = argparse.ArgumentParser(description="Sender (Distributed)")
    parser.add_argument("--server1-host", default=None, help="IP của Server1")
    args = parser.parse_args()

    config = get_config("distributed_4machines")["sender"]
    if args.server1_host:
        config["server1_host"] = args.server1_host

    gui = SenderGUI(config)
    sender = Sender(
        server1_host=config["server1_host"],
        server1_port=config["server1_port"],
        sender_id=config.get("sender_id", "sender"),
        timeout=config.get("timeout", 30),
        log_callback=gui.log
    )

    # Gán callback handshake và gửi file cho GUI
    gui.set_handshake_callback(sender.perform_handshake)
    gui.set_send_file_callback(sender.send_file_complete_flow)

    gui.run()

if __name__ == "__main__":
    main() 