# Instagram Media Downloader Pro

A GUI tool to download **Instagram posts and stories** with ease, generate **video thumbnails**, and insert downloaded media into a local **SQLite database**. Built with `tkinter`, powered by `gallery-dl` and `ffmpeg`.

---

## ⚙️ Features

- Download **latest posts** or **stories** from selected Instagram users.
- Automatically generate **video thumbnails** using `ffmpeg`.
- Automatically insert newly downloaded media into the SQLite `.stogram.sqlite` database.
- **Manual import** support for media files already on disk.
- Friendly GUI with progress bar and log output.

---

## 📦 Requirements

- Python 3.8+
- Needs to be the same folder as the 4kstogram database
- Firefox browser (used by `gallery-dl` for cookie extraction)
- Required executables:
  - `assets/gallery-dl.exe`
  - `assets/ffmpeg.exe`

> ⚠️ You must be logged into Instagram via Firefox for `gallery-dl` to work properly with `--cookies-from-browser firefox`.

---
