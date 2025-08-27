import tkinter as tk
from tkinter import font
import sqlite3
import uuid
import os
import sys
import ctypes
from datetime import datetime

# --- Constants ---
DB_NAME = ".stogram.sqlite"
TABLE_NAME = "subscriptions"
ATTRIBUTES = '{"limited":"_BASE64_MA==","sortMode":"_BASE64_MQ==","visualIndex":"_BASE64_LTE="}'

# --- Utility Functions ---

def enable_high_dpi():
    """Enables High DPI awareness on Windows for crisp UI scaling."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

def get_db_path():
    """Returns the full path to the database file."""
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, DB_NAME)

def generate_subscription_id():
    """Generates a UUID and returns its BLOB and hex string."""
    hex_string = uuid.uuid4().hex
    return bytes.fromhex(hex_string), hex_string

def center_window(window, width, height):
    """Centers a Tkinter window on the screen."""
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = int((screen_width / 2) - (width / 2))
    y = int((screen_height / 2) - (height / 2))
    window.geometry(f"{width}x{height}+{x}+{y}")

def show_copyable_message(title, message):
    """Creates a pop-up window with copyable text."""
    window = tk.Toplevel()
    window.title(title)
    
    # Increase the width and height of the window here
    center_window(window, 800, 600) # <- Changed from 500, 300 to 600, 400

    message_font = font.Font(family="Segoe UI", size=10)

    text_widget = tk.Text(window, font=message_font, relief="flat", padx=15, pady=15)
    text_widget.insert(tk.END, message)
    text_widget.config(state="disabled", wrap="word")

    scrollbar = tk.Scrollbar(window, command=text_widget.yview)
    text_widget.config(yscrollcommand=scrollbar.set)

    scrollbar.pack(side="right", fill="y")
    text_widget.pack(side="top", fill="both", expand=True)

    ok_button = tk.Button(window, text="OK", command=window.destroy, font=("Segoe UI", 12))
    ok_button.pack(pady=10)

# --- Main Application Logic ---

def add_subscription(username_entry, root_window):
    """Adds a new subscription to the database."""
    username = username_entry.get().strip()

    if not username:
        tk.messagebox.showwarning("Input Error", "Username cannot be empty.")
        return

    db_path = get_db_path()

    if not os.path.exists(db_path):
        tk.messagebox.showerror("Database Error", f"Database '{DB_NAME}' not found.")
        return

    sub_id_blob, sub_id_hex = generate_subscription_id()
    date_added = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(f"""
            INSERT INTO {TABLE_NAME} (id, query, attributes, display_name, date_added)
            VALUES (?, ?, ?, ?, ?)
        """, (sub_id_blob, username, ATTRIBUTES, username, date_added))

        conn.commit()
        conn.close()

        success_message = f"✅ Subscription added!\n\nUser: {username}\nID (hex): {sub_id_hex}\nDate: {date_added}"
        show_copyable_message("Success", success_message)
        
        username_entry.delete(0, tk.END)

    except Exception as e:
        tk.messagebox.showerror("Database Error", str(e))

def setup_ui(root):
    """Sets up the main application window and its widgets."""
    root.title("Stogram Subscription Manager")
    window_width, window_height = 800, 600
    center_window(root, window_width, window_height)

    app_font = font.Font(family="Segoe UI", size=14)
    button_font = font.Font(family="Segoe UI", size=14, weight="bold")

    main_frame = tk.Frame(root, padx=20, pady=20)
    main_frame.pack(fill="both", expand=True)

    tk.Label(main_frame, text="Enter Username:", font=app_font).pack(pady=(10, 5))

    username_entry = tk.Entry(main_frame, font=app_font)
    username_entry.pack(fill=tk.X, padx=20, pady=5)

    add_button = tk.Button(main_frame, text="Add Subscription", font=button_font,
                           command=lambda: add_subscription(username_entry, root))
    add_button.pack(pady=20)

def main():
    enable_high_dpi()
    root = tk.Tk()
    setup_ui(root)
    root.mainloop()

if __name__ == "__main__":
    main()