import tkinter as tk
from tkinter import scrolledtext, messagebox
import os

class ReceiverGUI:
    def __init__(self, output_dir="data/output"):
        self.output_dir = output_dir
        self.root = tk.Tk()
        self.root.title("Receiver GUI")
        self.root.geometry("900x600")

        # Frame chính chia 2 cột (trái: danh sách file, phải: nội dung file)
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Cửa sổ dọc bên trái: danh sách file
        left_frame = tk.Frame(main_frame)
        left_frame.pack(side="left", fill="y")
        tk.Label(left_frame, text="Các file đã nhận:").pack(anchor="w")
        self.file_listbox = tk.Listbox(left_frame, width=40, height=25)
        self.file_listbox.pack(fill="y", expand=True)
        self.file_listbox.bind("<<ListboxSelect>>", self.open_file_content)
        tk.Button(left_frame, text="Làm mới danh sách file", command=self.refresh_file_list).pack(pady=5)

        # Cửa sổ lớn bên phải: nội dung file
        right_frame = tk.Frame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True)
        tk.Label(right_frame, text="Nội dung file:").pack(anchor="w")
        self.content_text = scrolledtext.ScrolledText(right_frame, width=70, height=30, state="disabled")
        self.content_text.pack(fill="both", expand=True)

        # Cửa sổ ngang bên dưới: log
        self.log_text = scrolledtext.ScrolledText(self.root, height=10, width=120, state="disabled")  # tăng chiều cao log
        self.log_text.pack(fill="x", padx=10, pady=5)

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