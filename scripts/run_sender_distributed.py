import sys
from pathlib import Path
import argparse
sys.path.append(str(Path(__file__).parent.parent / "src"))
sys.path.append(str(Path(__file__).parent.parent))  # Add root directory for config module

from config.network_config import get_config
from src.gui.sender_gui import SenderGUI

def main():
    parser = argparse.ArgumentParser(description="Sender (Distributed)")
    parser.add_argument("--server1-host", default=None, help="IP của Server1")
    args = parser.parse_args()

    config = get_config("distributed_4machines")["sender"]
    if args.server1_host:
        config["server1_host"] = args.server1_host

    gui = SenderGUI(config)
    gui.run()

if __name__ == "__main__":
    main() 