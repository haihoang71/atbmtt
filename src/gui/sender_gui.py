import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from src.gui.components.progress_bar import progress_bar
from src.gui.components.log_viewer import log_viewer
from src.components.sender import Sender
import logging
import threading
import time

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
        self.root.minsize(650, 420)
        self.theme = "light"
        self._set_theme()
        self._setup_style()

        self.file_path = tk.StringVar(value="Chưa chọn file")
        self.server_ip = tk.StringVar(value=config["server1_host"])
        self.server_port = tk.StringVar(value=str(config["server1_port"]))
        self.status = tk.StringVar(value="Chưa kết nối")
        self.status_color = "#BDBDBD"  # xám
        self.last_connect_time = tk.StringVar(value="-")

        # Callbacks
        self.handshake_callback = None
        self.send_file_callback = None

        # --- Top bar: Theme toggle ---
        topbar = ttk.Frame(self.root, style="Topbar.TFrame")
        topbar.pack(fill="x", pady=(0, 2))
        theme_btn = ttk.Button(topbar, text="Đổi theme", width=10, command=self.toggle_theme, style="Theme.TButton")
        theme_btn.pack(side="right", padx=8, pady=4)

        # --- Thông tin kết nối ---
        info_frame = ttk.Frame(self.root, style="Info.TFrame", padding=(10, 8))
        info_frame.pack(fill="x", pady=(0, 8), padx=0)
        ttk.Label(info_frame, text="Server:", style="Info.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(info_frame, textvariable=self.server_ip, style="Info.TLabel").grid(row=0, column=1, sticky="w", padx=(2, 10))
        ttk.Label(info_frame, text=":", style="Info.TLabel").grid(row=0, column=2)
        ttk.Label(info_frame, textvariable=self.server_port, style="Info.TLabel").grid(row=0, column=3, sticky="w")
        ttk.Label(info_frame, text="| Trạng thái:", style="Info.TLabel").grid(row=0, column=4, padx=(10,0))
        self.status_light = tk.Canvas(info_frame, width=16, height=16, bg=self.bg, highlightthickness=0, bd=0)
        self.status_light.grid(row=0, column=5, padx=(0,2))
        self._draw_status_light(self.status_color)
        ttk.Label(info_frame, textvariable=self.status, style="Status.TLabel").grid(row=0, column=6, padx=(2,10))
        ttk.Label(info_frame, text="| Lần kết nối:", style="Info.TLabel").grid(row=0, column=7)
        ttk.Label(info_frame, textvariable=self.last_connect_time, style="Info.TLabel").grid(row=0, column=8)

        # --- Log viewer ---
        log_frame = ttk.Frame(self.root, style="Log.TFrame", padding=(10, 0, 10, 10))
        log_frame.pack(fill="both", expand=True, padx=0)
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, width=90, state="disabled", bg=self.bg2, fg=self.fg, font=("Arial", 11), borderwidth=1, relief="solid")
        self.log_text.pack(fill="both", expand=True, pady=(0, 0))

        # --- Action bar ---
        action_frame = ttk.Frame(self.root, style="Action.TFrame", padding=(10, 8))
        action_frame.pack(fill="x", pady=(0, 8))
        self.handshake_btn = ttk.Button(action_frame, text="Handshake", command=self._on_handshake, width=16, style="Action.TButton")
        self.handshake_btn.grid(row=0, column=0, padx=5, pady=2)
        self.retry_btn = ttk.Button(action_frame, text="Retry", command=self._on_handshake, width=10, style="Retry.TButton", state="disabled")
        self.retry_btn.grid(row=0, column=1, padx=5, pady=2)
        self.send_btn = ttk.Button(action_frame, text="Gửi file", command=self._on_send_file, width=16, style="Send.TButton", state="disabled")
        self.send_btn.grid(row=0, column=2, padx=5, pady=2)

        # --- File select ---
        file_frame = ttk.Frame(self.root, style="File.TFrame", padding=(10, 8))
        file_frame.pack(fill="x", pady=(0, 8))
        ttk.Label(file_frame, text="File:", style="Info.TLabel").grid(row=0, column=0, padx=(0,5))
        self.file_label = ttk.Label(file_frame, textvariable=self.file_path, style="File.TLabel", width=50)
        self.file_label.grid(row=0, column=1, padx=(0,5))
        self.select_btn = ttk.Button(file_frame, text="Chọn file", command=self.select_file, state="disabled", style="File.TButton")
        self.select_btn.grid(row=0, column=2, padx=5)

        # Drag & drop file (nếu khả thi)
        self.root.drop_target_register = getattr(self.root, 'drop_target_register', lambda *a, **k: None)
        self.root.dnd_bind = getattr(self.root, 'dnd_bind', lambda *a, **k: None)
        try:
            import tkinterdnd2 as tkdnd
            self.root = tkdnd.TkinterDnD.Tk()
            self.root.drop_target_register('DND_Files')
            self.root.dnd_bind('<<Drop>>', self._on_drop_file)
        except ImportError:
            pass

    def _setup_style(self):
        style = ttk.Style(self.root)
        style.theme_use('clam')
        style.configure("Topbar.TFrame", background=self.bg)
        style.configure("Info.TFrame", background=self.bg)
        style.configure("Info.TLabel", background=self.bg, foreground=self.fg, font=("Arial", 10))
        style.configure("Status.TLabel", background=self.bg, foreground="#1976D2", font=("Arial", 10, "bold"))
        style.configure("Log.TFrame", background=self.bg2)
        style.configure("Action.TFrame", background=self.bg)
        style.configure("Action.TButton", font=("Arial", 10, "bold"), padding=6)
        style.configure("Retry.TButton", font=("Arial", 10), background="#FFC107", foreground="#222", padding=6)
        style.map("Retry.TButton", background=[('active', '#FFD54F')])
        style.configure("Send.TButton", font=("Arial", 11, "bold"), background="#4CAF50", foreground="white", padding=6)
        style.map("Send.TButton", background=[('active', '#388E3C')])
        style.configure("File.TFrame", background=self.bg)
        style.configure("File.TLabel", background=self.bg, foreground="#1976D2", font=("Arial", 10, "italic"))
        style.configure("File.TButton", font=("Arial", 10), background="#E0E0E0", foreground="#333", padding=6)
        style.map("File.TButton", background=[('active', '#BDBDBD')])
        style.configure("Theme.TButton", font=("Arial", 10), background=self.bg2, foreground=self.fg, padding=4)

    def _set_theme(self):
        if self.theme == "light":
            self.bg = "#F5F5F5"
            self.bg2 = "#FFFFFF"
            self.fg = "#222"
        else:
            self.bg = "#23272E"
            self.bg2 = "#2C313A"
            self.fg = "#F5F5F5"
        if hasattr(self, 'root'):
            self.root.configure(bg=self.bg)

    def toggle_theme(self):
        self.theme = "dark" if self.theme == "light" else "light"
        self._set_theme()
        self._setup_style()

    def _draw_status_light(self, color):
        self.status_light.delete("all")
        self.status_light.create_oval(3,3,13,13, fill=color, outline="#888", width=2)

    def set_handshake_callback(self, callback):
        self.handshake_callback = callback

    def set_send_file_callback(self, callback):
        self.send_file_callback = callback

    def select_file(self):
        path = filedialog.askopenfilename()
        if path:
            self.file_path.set(path)

    def _on_drop_file(self, event):
        files = self.root.tk.splitlist(event.data)
        if files:
            self.file_path.set(files[0])

    def _on_handshake(self):
        self.status.set("Đang handshake...")
        self.status_color = "#FFC107"  # vàng
        self._draw_status_light(self.status_color)
        self.handshake_btn.config(state="disabled")
        self.retry_btn.config(state="disabled")
        threading.Thread(target=self._do_handshake, daemon=True).start()

    def _do_handshake(self):
        if self.handshake_callback:
            ok = self.handshake_callback()
            if ok:
                self.status.set("Đã kết nối")
                self.status_color = "#4CAF50"  # xanh
                self.last_connect_time.set(time.strftime("%H:%M:%S"))
                self.enable_file_send(True)
                self.retry_btn.config(state="disabled")
            else:
                self.status.set("Lỗi handshake")
                self.status_color = "#F44336"  # đỏ
                self.enable_file_send(False)
                self.retry_btn.config(state="normal")
        else:
            self.log("error", "Chưa gán callback handshake!")
        self._draw_status_light(self.status_color)
        self.handshake_btn.config(state="normal")

    def _on_send_file(self):
        file_path = self.file_path.get()
        if file_path == "Chưa chọn file":
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn file trước!")
            return
        if self.send_file_callback:
            self.send_file_callback(file_path)
        else:
            self.log("error", "Chưa gán callback gửi file!")

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