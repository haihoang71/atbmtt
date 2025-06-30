import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import os

class ReceiverGUI:
    def __init__(self, output_dir="data/output"):
        self.output_dir = output_dir
        self.root = tk.Tk()
        self.root.title("Receiver GUI")
        self.root.minsize(900, 600)
        self.theme = "light"
        self._set_theme()
        self._setup_style()

        # --- Top bar: Theme toggle ---
        topbar = ttk.Frame(self.root, style="Topbar.TFrame")
        topbar.pack(fill="x", pady=(0, 2))
        theme_btn = ttk.Button(topbar, text="Đổi theme", width=10, command=self.toggle_theme, style="Theme.TButton")
        theme_btn.pack(side="right", padx=8, pady=4)
        ttk.Label(topbar, text="Receiver đang lắng nghe...", style="Info.TLabel").pack(side="left", padx=10, pady=4)

        # --- Main frame: 2 cột ---
        main_frame = ttk.Frame(self.root, style="Main.TFrame", padding=(10, 10))
        main_frame.pack(fill="both", expand=True)

        # --- Left: Danh sách file ---
        left_frame = ttk.Frame(main_frame, style="Left.TFrame")
        left_frame.pack(side="left", fill="y", padx=(0, 10), anchor="n")
        ttk.Label(left_frame, text="Các file đã nhận:", style="Info.TLabel").pack(anchor="w", pady=(0,4))
        self.file_listbox = tk.Listbox(left_frame, width=40, height=25, font=("Arial", 10))
        self.file_listbox.pack(fill="y", expand=True, pady=(0,4))
        self.file_listbox.bind("<<ListboxSelect>>", self.open_file_content)
        ttk.Button(left_frame, text="Làm mới danh sách file", command=self.refresh_file_list, style="File.TButton").pack(pady=4, fill="x")

        # --- Right: Nội dung file ---
        right_frame = ttk.Frame(main_frame, style="Right.TFrame")
        right_frame.pack(side="right", fill="both", expand=True)
        ttk.Label(right_frame, text="Nội dung file:", style="Info.TLabel").pack(anchor="w", pady=(0,4))
        self.content_text = scrolledtext.ScrolledText(right_frame, width=70, height=30, state="disabled", font=("Arial", 11), borderwidth=1, relief="solid", bg=self.bg2, fg=self.fg)
        self.content_text.pack(fill="both", expand=True)

        # --- Log dưới cùng ---
        log_frame = ttk.Frame(self.root, style="Log.TFrame", padding=(10, 0, 10, 10))
        log_frame.pack(fill="x")
        self.log_text = scrolledtext.ScrolledText(log_frame, height=7, width=120, state="disabled", font=("Arial", 10), borderwidth=1, relief="solid", bg=self.bg2, fg=self.fg)
        self.log_text.pack(fill="x", expand=True)

    def _setup_style(self):
        style = ttk.Style(self.root)
        style.theme_use('clam')
        style.configure("Topbar.TFrame", background=self.bg)
        style.configure("Main.TFrame", background=self.bg)
        style.configure("Left.TFrame", background=self.bg2)
        style.configure("Right.TFrame", background=self.bg2)
        style.configure("Info.TLabel", background=self.bg, foreground=self.fg, font=("Arial", 10, "bold"))
        style.configure("File.TButton", font=("Arial", 10), background="#E0E0E0", foreground="#333", padding=6)
        style.map("File.TButton", background=[('active', '#BDBDBD')])
        style.configure("Theme.TButton", font=("Arial", 10), background=self.bg2, foreground=self.fg, padding=4)
        style.configure("Log.TFrame", background=self.bg2)

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
        # Đổi màu cho các vùng text
        self.content_text.config(bg=self.bg2, fg=self.fg)
        self.log_text.config(bg=self.bg2, fg=self.fg)

    def log(self, level, msg):
        self.log_text.config(state="normal")
        self.log_text.insert("end", f"[{level.upper()}] {msg}\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def refresh_file_list(self):
        self.file_listbox.delete(0, tk.END)
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        files = os.listdir(self.output_dir)
        for f in files:
            self.file_listbox.insert(tk.END, f)

    def open_file_content(self, event):
        selection = self.file_listbox.curselection()
        if not selection:
            return
        filename = self.file_listbox.get(selection[0])
        filepath = os.path.join(self.output_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể đọc file: {e}")
            return
        self.content_text.config(state="normal")
        self.content_text.delete("1.0", tk.END)
        self.content_text.insert("1.0", content)
        self.content_text.config(state="disabled")

    def run(self):
        self.refresh_file_list()
        self.root.mainloop() 