import os
import subprocess
import time
import sqlite3
import threading
import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# === DEFAULT CONFIG VALUES ===
MEDIA_TABLE = "photos"
SUBSCRIPTIONS_TABLE = "subscriptions"
MEDIA_BASE_PATH = Path("instagram")
THUMBNAIL_FOLDER_NAME = "thumbnails"
FFMPEG_EXE = "assets/ffmpeg.exe"
GDL_EXE = "assets/gallery-dl.exe"
SETTINGS_FILE = "settings.json"

# Automatically detect database file with .stogram.sqlite extension
DB_FILE = None
for file in os.listdir():
    if file.endswith(".stogram.sqlite"):
        candidate = Path(file)
        if candidate.is_file():
            DB_FILE = candidate
            break

GDL_INCLUDE_OPTIONS = {
    "Posts": "posts",
    "Stories": "stories",
}

def fetch_users():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(f"SELECT id, query FROM {SUBSCRIPTIONS_TABLE} WHERE id IS NOT NULL AND query IS NOT NULL")
        users = cursor.fetchall()
        conn.close()
        return users
    except sqlite3.Error:
        return []

def validate_database(file_path):
    try:
        conn = sqlite3.connect(file_path)
        cursor = conn.cursor()
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{MEDIA_TABLE}'")
        if cursor.fetchone() is None:
            return False
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{SUBSCRIPTIONS_TABLE}'")
        if cursor.fetchone() is None:
            return False
        return True
    except Exception:
        return False
    finally:
        conn.close()

def download_media(subscription_id_blob, username, output_callback, media_type="Posts", post_limit=10, browser="firefox"):
    user_media_path = MEDIA_BASE_PATH / username
    user_thumb_path = user_media_path / THUMBNAIL_FOLDER_NAME
    user_media_path.mkdir(parents=True, exist_ok=True)
    user_thumb_path.mkdir(parents=True, exist_ok=True)

    output_callback(f"Downloading {media_type.lower()} from Instagram for @{username} using {browser} cookies...")

    if media_type == "Stories":
        url = f"https://www.instagram.com/stories/{username}/"
    else:
        url = f"https://www.instagram.com/{username}/"

    try:
        subprocess.run([
            GDL_EXE,
            url,
            "--cookies-from-browser", browser,
            "-o", f"include={GDL_INCLUDE_OPTIONS[media_type]}",
            "-o", f"extractor.instagram.max-posts={post_limit}",
            "-D", str(user_media_path)
        ], check=True)
    except subprocess.CalledProcessError as e:
        output_callback(f"❌ gallery-dl failed: {e}")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    created_time = int(time.time())

    cursor.execute(f"SELECT instagram_id FROM {SUBSCRIPTIONS_TABLE} WHERE query = ?", (username,))
    result = cursor.fetchone()
    owner_id = result[0] if result else None

    cutoff_time = time.time() - (30 * 60)
    output_callback(f"Scanning for new media in {user_media_path} (created within last 30 minutes)...")

    media_files = [
        f for f in os.listdir(user_media_path)
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".mp4")) and
           os.path.getctime(user_media_path / f) >= cutoff_time
    ]

    for filename in media_files:
        full_path = user_media_path / filename
        file_relative_path = str(full_path.relative_to(MEDIA_BASE_PATH.parent))

        cursor.execute(f"SELECT COUNT(*) FROM {MEDIA_TABLE} WHERE file = ?", (file_relative_path,))
        if cursor.fetchone()[0] > 0:
            output_callback(f"Skipping existing: {filename}")
            continue

        if filename.lower().endswith('.mp4'):
            thumb_name = f"{Path(filename).stem}.jpg"
            thumb_path = user_thumb_path / thumb_name
            subprocess.run([
                FFMPEG_EXE,
                "-ss", "3",
                "-i", str(full_path),
                "-vframes", "1",
                str(thumb_path)
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            thumbnail_relative_path = str(thumb_path.relative_to(MEDIA_BASE_PATH.parent))
        else:
            thumbnail_relative_path = file_relative_path

        cursor.execute(f"""
            INSERT INTO {MEDIA_TABLE} (subscriptionId, created_time, thumbnail_file, file, ownerName, ownerId)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            subscription_id_blob,
            created_time,
            thumbnail_relative_path,
            file_relative_path,
            username,
            owner_id
        ))
        output_callback(f"Inserted: {filename}")

    conn.commit()
    conn.close()
    output_callback("\n✅ Download and insert complete.")

def load_settings():
    if Path(SETTINGS_FILE).exists():
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f)
    except Exception:
        pass

class IntegerEntry(ttk.Entry):
    def __init__(self, master=None, **kwargs):
        self.var = tk.StringVar()
        super().__init__(master, textvariable=self.var, **kwargs)
        self.var.trace_add("write", self._validate)

    def _validate(self, *args):
        value = self.var.get()
        # Allow only digits (positive integers including 0)
        if not value.isdigit() and value != "":
            self.var.set(''.join(filter(str.isdigit, value)))

    def get_value(self):
        return int(self.var.get()) if self.var.get().isdigit() else 0

    def set_value(self, value):
        self.var.set(str(value))

class InstagramDownloaderApp:
    def center_window(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
    def __init__(self, root):
        self.root = root
        self.root.title("Instagram Media Downloader Pro")
        self.root.geometry("650x700")
        self.root.configure(bg="#f0f0f0")
        self.users = []
        self.media_type = tk.StringVar()
        self.browser_choice = tk.StringVar()

        self.settings = load_settings()
        self.browser_choice.set(self.settings.get("browser", "firefox"))
        self.media_type.set(self.settings.get("media_type", "Posts"))

        self.create_widgets()
        self.root.after(100, self.center_window)

        self.post_limit_entry.set_value(self.settings.get("post_limit", 10))
        if not DB_FILE or not validate_database(DB_FILE):
            messagebox.showwarning(
                "No Database Found",
                "No valid '.stogram.sqlite' database file was found in the current directory.\n"
                "Please put me and /assets folder the same directory as the 4K stogram database"
            )
            self.root.destroy()  # Gracefully close the GUI if no database is found
        if DB_FILE and validate_database(DB_FILE):
            self.db_label.config(text=str(DB_FILE))
            self.reload_users()
            self.start_button.config(state="normal")
            self.refresh_button.config(state="normal")

    def create_widgets(self):
        self.db_label = ttk.Label(self.root, text="No database selected", font=("Segoe UI", 10, "italic"))
        self.db_label.pack(pady=5)

        user_frame = ttk.LabelFrame(self.root, text="User Selection")
        user_frame.pack(pady=10, fill='x', padx=20)
        ttk.Label(user_frame, text="Instagram User:", font=("Segoe UI", 11)).pack(anchor='w', padx=10, pady=5)

        self.user_var = tk.StringVar()
        self.user_dropdown = ttk.Combobox(user_frame, textvariable=self.user_var, state="readonly", font=("Segoe UI", 10))
        self.user_dropdown.pack(pady=5, padx=10, fill='x')

        media_type_frame = ttk.LabelFrame(self.root, text="Download Type")
        media_type_frame.pack(pady=10, fill='x', padx=20)
        for mtype in GDL_INCLUDE_OPTIONS.keys():
            ttk.Radiobutton(media_type_frame, text=mtype, variable=self.media_type, value=mtype).pack(anchor='w', padx=10, pady=2)

        browser_frame = ttk.LabelFrame(self.root, text="Browser for Cookies")
        browser_frame.pack(pady=10, fill='x', padx=20)
        browser_dropdown = ttk.Combobox(browser_frame, textvariable=self.browser_choice, state="readonly", width=15)
        browser_dropdown['values'] = ("firefox", "chrome")
        browser_dropdown.pack(padx=10, pady=5)

        range_frame = ttk.LabelFrame(self.root, text="Post Limit")
        range_frame.pack(pady=10, fill='x', padx=20)
        ttk.Label(range_frame, text="Number of latest posts (0 = all):").pack(side='left', padx=10, pady=5)
        self.post_limit_entry = IntegerEntry(range_frame, width=6)
        self.post_limit_entry.pack(side='left', pady=5)

        self.start_button = ttk.Button(self.root, text="Start Download", command=self.start_download, state="disabled")
        self.start_button.pack(pady=10)

        self.refresh_button = ttk.Button(self.root, text="Reload Users", command=self.reload_users, state="disabled")
        self.refresh_button.pack(pady=5)
        
        ttk.Button(range_frame, text="Set to 0 (All)", command=lambda: self.post_limit_entry.set_value(0)).pack(side='left', padx=10)
        ttk.Button(self.root, text="Add Media Manually to DB", command=self.add_manual_media).pack(pady=5)

        self.progress = ttk.Progressbar(self.root, mode='indeterminate')
        self.progress.pack(fill='x', padx=20, pady=5)

        self.output_box = tk.Text(self.root, height=12, wrap='word', font=("Consolas", 10))
        self.output_box.pack(fill='both', expand=True, padx=10, pady=10)

    def log_output(self, text):
        self.output_box.insert(tk.END, f"{text}\n")
        self.output_box.see(tk.END)
        self.root.update_idletasks()

    def reload_users(self):
        self.users = fetch_users()
        if not self.users:
            self.user_dropdown['values'] = []
            self.user_dropdown.set("")
            messagebox.showerror("Error", "No valid users found in the selected database.")
        else:
            self.user_dropdown['values'] = [f"{u[1]}" for u in self.users]
            last_user = self.settings.get("username")
            if last_user and last_user in self.user_dropdown['values']:
                self.user_dropdown.set(last_user)
            else:
                self.user_dropdown.set(self.user_dropdown['values'][0])

    def start_download(self):
        if not self.user_var.get():
            messagebox.showwarning("Warning", "Please select a user.")
            return

        index = self.user_dropdown.current()
        if index < 0 or index >= len(self.users):
            messagebox.showerror("Error", "Invalid user selection.")
            return

        subscription_id_blob, username = self.users[index]
        media_type = self.media_type.get()
        post_limit = self.post_limit_entry.get_value()
        browser = self.browser_choice.get()

        self.settings["browser"] = browser
        self.settings["media_type"] = media_type
        self.settings["post_limit"] = post_limit
        self.settings["username"] = username
        save_settings(self.settings)

        self.start_button.config(state="disabled")
        self.progress.start()
        self.log_output(f"⏳ Starting for {username} ({media_type}) with {browser} browser...\n")

        threading.Thread(
            target=self.download_worker,
            args=(subscription_id_blob, username, media_type, post_limit, browser),
            daemon=True
        ).start()

    def download_worker(self, subscription_id_blob, username, media_type, post_limit, browser):
        try:
            download_media(subscription_id_blob, username, self.log_output, media_type, post_limit, browser)
        except Exception as e:
            self.log_output(f"❌ Error: {e}")
        finally:
            self.progress.stop()
            self.start_button.config(state="normal")

    def add_manual_media(self):
        if not self.user_var.get():
            messagebox.showwarning("Warning", "Please select a user.")
            return

        index = self.user_dropdown.current()
        if index < 0 or index >= len(self.users):
            messagebox.showerror("Error", "Invalid user selection.")
            return

        subscription_id_blob, username = self.users[index]

        # Let user select multiple files
        file_paths = filedialog.askopenfilenames(
            title="Select media files to insert",
            filetypes=[("Media Files", "*.jpg *.jpeg *.png *.mp4")]
        )
        if not file_paths:
            return

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        created_time = int(time.time())

        cursor.execute(f"SELECT instagram_id FROM {SUBSCRIPTIONS_TABLE} WHERE query = ?", (username,))
        result = cursor.fetchone()
        owner_id = result[0] if result else None

        user_media_path = MEDIA_BASE_PATH / username
        user_thumb_path = user_media_path / THUMBNAIL_FOLDER_NAME
        user_media_path.mkdir(parents=True, exist_ok=True)
        user_thumb_path.mkdir(parents=True, exist_ok=True)

        for fpath in file_paths:
            fpath = Path(fpath)

            # Copy file into user folder if not already there
            dest_path = user_media_path / fpath.name
            if not dest_path.exists():
                try:
                    import shutil
                    shutil.copy(fpath, dest_path)
                except Exception as e:
                    self.log_output(f"❌ Failed to copy {fpath}: {e}")
                    continue

            file_relative_path = str(dest_path.relative_to(MEDIA_BASE_PATH.parent))

            # Skip if already in DB
            cursor.execute(f"SELECT COUNT(*) FROM {MEDIA_TABLE} WHERE file = ?", (file_relative_path,))
            if cursor.fetchone()[0] > 0:
                self.log_output(f"Skipping existing: {fpath.name}")
                continue

            # Generate thumbnail
            if fpath.suffix.lower() == ".mp4":
                thumb_name = f"{fpath.stem}.jpg"
                thumb_path = user_thumb_path / thumb_name
                subprocess.run([
                    FFMPEG_EXE,
                    "-ss", "3",
                    "-i", str(dest_path),
                    "-vframes", "1",
                    str(thumb_path)
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                thumbnail_relative_path = str(thumb_path.relative_to(MEDIA_BASE_PATH.parent))
            else:
                thumbnail_relative_path = file_relative_path

            # Insert into DB
            cursor.execute(f"""
                INSERT INTO {MEDIA_TABLE} (subscriptionId, created_time, thumbnail_file, file, ownerName, ownerId)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                subscription_id_blob,
                created_time,
                thumbnail_relative_path,
                file_relative_path,
                username,
                owner_id
            ))
            self.log_output(f"Inserted manually: {fpath.name}")

        conn.commit()
        conn.close()
        self.log_output("\n✅ Manual insert complete.")


if __name__ == "__main__":
    root = tk.Tk()
    app = InstagramDownloaderApp(root)
    root.mainloop()