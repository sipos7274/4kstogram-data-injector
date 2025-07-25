import os
import subprocess
import time
import sqlite3
import threading
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

def download_media(subscription_id_blob, username, output_callback, media_type="Posts", post_limit=10):
    user_media_path = MEDIA_BASE_PATH / username
    user_thumb_path = user_media_path / THUMBNAIL_FOLDER_NAME
    user_media_path.mkdir(parents=True, exist_ok=True)
    user_thumb_path.mkdir(parents=True, exist_ok=True)

    output_callback(f"Downloading {media_type.lower()} from Instagram for @{username}...")

    if media_type == "Stories":
        url = f"https://www.instagram.com/stories/{username}/"
    else:
        url = f"https://www.instagram.com/{username}/"

    try:
        subprocess.run([
            GDL_EXE,
            url,
            "--cookies-from-browser", "firefox",
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

    # --- Define cutoff time (files created within last 30 minutes) ---
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

# === GUI SETUP ===
class InstagramDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Instagram Media Downloader Pro")
        self.root.geometry("650x650")
        self.users = []
        self.media_type = tk.StringVar(value="Posts")
        self.post_limit = tk.IntVar(value=10)

        self.create_widgets()

        if DB_FILE and validate_database(DB_FILE):
            self.db_label.config(text=str(DB_FILE))
            self.reload_users()
            self.start_button.config(state="normal")
            self.refresh_button.config(state="normal")

    def create_widgets(self):
        ttk.Button(self.root, text="Select Database", command=self.select_database).pack(pady=10)

        self.db_label = ttk.Label(self.root, text="No database selected", font=("Segoe UI", 10, "italic"))
        self.db_label.pack(pady=5)

        ttk.Label(self.root, text="Select Instagram User:", font=("Segoe UI", 12)).pack(pady=10)

        self.user_var = tk.StringVar()
        self.user_dropdown = ttk.Combobox(self.root, textvariable=self.user_var, state="readonly", font=("Segoe UI", 11))
        self.user_dropdown.pack(pady=5, fill='x', padx=50)

        media_type_frame = ttk.LabelFrame(self.root, text="Download Type")
        media_type_frame.pack(pady=10)
        for mtype in GDL_INCLUDE_OPTIONS.keys():
            ttk.Radiobutton(media_type_frame, text=mtype, variable=self.media_type, value=mtype).pack(anchor='w', padx=10)

        range_frame = ttk.Frame(self.root)
        range_frame.pack(pady=5)
        ttk.Label(range_frame, text="Number of latest posts to download, write 0 if you wanna download all:").pack(side='left', padx=5)
        ttk.Entry(range_frame, textvariable=self.post_limit, width=6).pack(side='left')

        self.start_button = ttk.Button(self.root, text="Start Download", command=self.start_download, state="disabled")
        self.start_button.pack(pady=10)

        self.refresh_button = ttk.Button(self.root, text="Reload Users", command=self.reload_users, state="disabled")
        self.refresh_button.pack(pady=5)

        ttk.Button(self.root, text="Add Media Manually to DB", command=self.add_manual_media).pack(pady=5)

        self.progress = ttk.Progressbar(self.root, mode='indeterminate')
        self.progress.pack(fill='x', padx=20, pady=5)

        self.output_box = tk.Text(self.root, height=12, wrap='word', font=("Consolas", 10))
        self.output_box.pack(fill='both', expand=True, padx=10, pady=10)

    def log_output(self, text):
        self.output_box.insert(tk.END, f"{text}\n")
        self.output_box.see(tk.END)
        self.root.update_idletasks()

    def select_database(self):
        global DB_FILE
        file_path = filedialog.askopenfilename(filetypes=[["SQLite Database", "*.sqlite"]])
        if file_path:
            if not validate_database(file_path):
                messagebox.showerror("Invalid Database", f"The selected database is missing required tables: {MEDIA_TABLE} and/or {SUBSCRIPTIONS_TABLE}.")
                return

            DB_FILE = Path(file_path)
            self.db_label.config(text=str(DB_FILE))
            self.reload_users()
            self.start_button.config(state="normal")
            self.refresh_button.config(state="normal")

    def reload_users(self):
        self.users = fetch_users()
        if not self.users:
            self.user_dropdown['values'] = []
            self.user_dropdown.set("")
            messagebox.showerror("Error", "No valid users found in the selected database.")
        else:
            self.user_dropdown['values'] = [f"{u[1]}" for u in self.users]
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
        post_limit = self.post_limit.get()

        self.start_button.config(state="disabled")
        self.progress.start()
        self.log_output(f"⏳ Starting for {username} ({media_type})...\n")

        threading.Thread(
            target=self.download_worker,
            args=(subscription_id_blob, username, media_type, post_limit),
            daemon=True
        ).start()

    def download_worker(self, subscription_id_blob, username, media_type, post_limit):
        try:
            download_media(subscription_id_blob, username, self.log_output, media_type, post_limit)
        except Exception as e:
            self.log_output(f"❌ Error: {e}")
        finally:
            self.progress.stop()
            self.start_button.config(state="normal")

    def add_manual_media(self):
        index = self.user_dropdown.current()
        if index < 0 or index >= len(self.users):
            messagebox.showerror("Error", "No user selected.")
            return

        subscription_id_blob, username = self.users[index]
        user_media_path = MEDIA_BASE_PATH / username

        if not user_media_path.exists():
            messagebox.showerror("Error", f"Path does not exist: {user_media_path}")
            return

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        created_time = int(time.time())

        cursor.execute(f"SELECT instagram_id FROM {SUBSCRIPTIONS_TABLE} WHERE query = ?", (username,))
        result = cursor.fetchone()
        owner_id = result[0] if result else None

        for filename in os.listdir(user_media_path):
            if filename.lower().endswith((".jpg", ".jpeg", ".png", ".mp4")):
                full_path = user_media_path / filename
                file_relative_path = str(full_path.relative_to(MEDIA_BASE_PATH.parent))

                cursor.execute(f"SELECT COUNT(*) FROM {MEDIA_TABLE} WHERE file = ?", (file_relative_path,))
                if cursor.fetchone()[0] > 0:
                    self.log_output(f"Skipping existing: {filename}")
                    continue

                if filename.lower().endswith('.mp4'):
                    thumb_path = full_path.with_suffix('.jpg')
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
                self.log_output(f"Manually inserted: {filename}")

        conn.commit()
        conn.close()
        self.log_output("\n✅ Manual media insertion complete.")

if __name__ == "__main__":
    root = tk.Tk()
    app = InstagramDownloaderApp(root)
    root.mainloop()
