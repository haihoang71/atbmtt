import tkinter as tk
from tkinter import filedialog

def file_selector(parent, callback):
    def select():
        file_path = filedialog.askopenfilename()
        if file_path:
            callback(file_path)
    btn = tk.Button(parent, text="Chọn file", command=select)
    return btn 