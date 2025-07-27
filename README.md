# Instagram Media Downloader Pro

A professional desktop tool for downloading Instagram **posts** and **stories**, generating video **thumbnails**, and inserting media into a local **SQLite** `.stogram.sqlite` database — all through a clean, intuitive GUI.

Built with `tkinter`, powered by `gallery-dl` and `ffmpeg`.

---

## ⚙️ Features

- 🎯 Download the latest **posts** or **stories** from selected Instagram users
- 🖼️ Automatically generate **video thumbnails** using `ffmpeg`
- 🗃️ Seamlessly insert new media into the local `.stogram.sqlite` database
- 🛠️ Supports **manual import** of media files already on disk
- 🧠 Remembers your last used:
  - Username
  - Browser (Chrome / Firefox)
  - Media type
  - Post limit

---

## 📦 Requirements

- **Python** `3.8+`
- **4K Stogram** `.stogram.sqlite` database file (must be in the same folder as the script)
- **Firefox** or **Chrome** browser (used by `gallery-dl` for cookie extraction)
- **Executables** (must be in the `assets/` folder):
  - `assets/gallery-dl.exe`
  - `assets/ffmpeg.exe`

> ⚠️ You must be logged into Instagram in your selected browser (`firefox` or `chrome`) for `gallery-dl` to successfully access private or authenticated content.

---

## 🚀 Running the App

### 🪟 On Windows:
Simply place the InstagramDownloaderPro.exe and /assets directory to the same directory as your `.stogram.sqlite` file and run the exe.
No Python installation needed.

### 🐍 From Source:

1. Place the script in the same directory as your `.stogram.sqlite` file. In windows you can use the InstagramDownloaderPro.exe
2. Ensure `gallery-dl.exe` and `ffmpeg.exe` are present in `./assets/`.
3. Run the app:
   `python instagram_gui.py`
4. You can create the exe by using this command:
  `pyinstaller --onefile --windowed instagram_gui_downloader.py --add-data "assets;assets" --name InstagramDownloaderPro`