import sys
import os
from pathlib import Path
import argparse

project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

from config.network_config import get_config
from src.components.receiver import Receiver
from src.gui.receiver_gui import ReceiverGUI

def main():
    parser = argparse.ArgumentParser(description="Receiver (Distributed)")
    parser.add_argument("--host", default=None, help="IP lắng nghe của Receiver")
    args = parser.parse_args()

    config = get_config("distributed_4machines")["receiver"]
    if args.host:
        config["host"] = args.host

    gui = ReceiverGUI(output_dir="data/output")
    receiver = Receiver(
        host=config["host"],
        port=config["port"],
        output_dir="data/output",
        log_callback=gui.log,
        on_new_file=lambda: gui.root.after(0, gui.refresh_file_list)
    )
    import threading
    threading.Thread(target=receiver.start_receiver, daemon=True).start()
    gui.run()

if __name__ == "__main__":
    main() 