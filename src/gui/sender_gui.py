import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from src.gui.components.progress_bar import progress_bar
from src.gui.components.log_viewer import log_viewer

from src.components.sender import Sender
import logging
import threading

# Thêm class handler để log ra GUI
class TkinterLogHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        self.text_widget.config(state="normal")
        self.text_widget.insert("end", msg + "\n")
        self.text_widget.see("end")
        self.text_widget.config(state="disabled")

class SenderGUI:
    def __init__(self, config):
        self.root = tk.Tk()
        self.root.title("Sender GUI")
        self.root.geometry("600x450")

        self.file_path = tk.StringVar(value="Chưa chọn file")
        self.server_ip = tk.StringVar(value=config["server1_host"])
        self.server_port = tk.StringVar(value=str(config["server1_port"]))

        # Khởi tạo Sender với log_callback
        self.sender = Sender(
            server1_host=config["server1_host"],
            server1_port=config["server1_port"],
            log_callback=self.log
        )

        # Callbacks
        self.handshake_callback = None
        self.send_file_callback = None

        # Log viewer
        self.log_text = scrolledtext.ScrolledText(self.root, height=10, width=70, state="disabled")
        self.log_text.pack(pady=10)

        # Handshake button
        self.handshake_btn = tk.Button(self.root, text="Handshake", command=self._on_handshake, width=20, bg="#2196F3", fg="white")
        self.handshake_btn.pack(pady=5)

        # File select
        file_frame = tk.Frame(self.root)
        file_frame.pack(pady=10)
        tk.Label(file_frame, text="File:").grid(row=0, column=0)
        self.file_label = tk.Label(file_frame, textvariable=self.file_path, fg="blue", width=40, anchor="w")
        self.file_label.grid(row=0, column=1)
        self.select_btn = tk.Button(file_frame, text="Chọn file", command=self.select_file, state="disabled")
        self.select_btn.grid(row=0, column=2, padx=5)

        # Send button
        self.send_btn = tk.Button(self.root, text="Gửi file", command=self._on_send_file, width=20, bg="#4CAF50", fg="white", state="disabled")
        self.send_btn.pack(pady=10)

    def set_handshake_callback(self, callback):
        self.handshake_callback = callback

    def set_send_file_callback(self, callback):
        self.send_file_callback = callback

    def select_file(self):
        path = filedialog.askopenfilename()
        if path:
            self.file_path.set(path)

    def _on_handshake(self):
        # Gọi trực tiếp Sender.perform_handshake trong thread để log ra GUI
        threading.Thread(target=self.sender.perform_handshake, daemon=True).start()

    def _on_send_file(self):
        file_path = self.file_path.get()
        if file_path == "Chưa chọn file":
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn file trước!")
            return
        if self.send_file_callback:
            self.send_file_callback(file_path)

    def enable_file_send(self, enable=True):
        state = "normal" if enable else "disabled"
        self.select_btn.config(state=state)
        self.send_btn.config(state=state)

    def log(self, level, msg):
        self.log_text.config(state="normal")
        self.log_text.insert("end", f"[{level.upper()}] {msg}\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def run(self):
        self.root.mainloop() 