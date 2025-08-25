# Changelog
---
### Release

## [1.1.3] - 2025-08-25

### Fixed
- "Add Media Manually to DB" button fixed and improved

## [1.1.2] - 2025-07-28

### Release
- Small improvments to the UI

## [1.1.1] - 2025-07-27

### Added
- 🧠 **Persistent Preferences**:
  - Last selected Instagram username
  - Browser choice (Firefox or Chrome)
  - Media type (Posts or Stories)
  - Post limit
- 🔢 **Post Limit Validation**: Post limit field now only accepts numeric input.
- 💄 **UI Enhancements**:
  - Improved layout with Segoe UI font
  - Better padding and spacing
  - Grouped sections (e.g. user options, status)
  - Styled buttons and widgets

### Changed
- GUI layout restructured for improved usability and visual clarity.

### Fixed
- Prevented non-numeric values in the post limit input.
- Improved fail-safety for corrupted or missing `settings.json`.

---

## [1.0.0] - 2025-07-25

### Initial release
- Basic GUI to select Instagram user from local .stogram.sqlite database.
- Downloads media via `gallery-dl` using browser cookies.
- Auto-generates thumbnails with `ffmpeg`.
- Inserts new media records into SQLite database.

