# Release Notes – Image Editor Pro v1.0.0

**Release date:** *(fill in when you tag)*  
**Full Changelog:** https://github.com/thomas-sabu-cs/image-editor-pro/compare/v0.9.0...v1.0.0 *(adjust base tag if needed)*

---

## 🎉 v1.0.0 – First stable release

This release marks Image Editor Pro as a **production-ready** desktop image editor with a modern dark UI, robust undo/redo, and a professional development and distribution setup.

---

### 🚀 Build system & distribution

- **Single-executable builds**  
  - New **`build_exe.py`** script uses **PyInstaller** to bundle the app into a single executable (no Python install required on the target machine).  
  - Supports an optional app icon via **`assets/icon.ico`** (or **`assets/icon.png`**).  
  - Bundles the **`src/`** module and optional **`assets/`** folder so the app runs standalone.

- **Run from source**  
  - **`python main.py`** (or your existing **`run.bat`** on Windows) with dependencies from **`requirements.txt`**.

---

### 🔄 CI/CD and quality

- **GitHub Actions workflow** (**.github/workflows/python-app.yml**)  
  - Runs on every **push** and **pull_request** to **`main`**.  
  - Uses **Python 3.10** and installs dependencies from **`requirements.txt`**.  
  - **Tests:** runs the full **pytest** suite in **`tests/`** (filter tests + command/undo-redo tests). The build **fails** if any test fails.  
  - **Linting:** runs **flake8** on **`src/`**, **`main.py`**, and **`build_exe.py`** so the codebase stays PEP 8–compliant and consistent.

- **Developer experience**  
  - **`.flake8`** config (e.g. max line length 127, ignore W293) keeps lint checks consistent locally and in CI.  
  - **`docs/DEVELOPMENT.md`** explains architecture (MVC, Command pattern), data flow, and how to add filters/tools and run tests.

---

### 🖥️ User-facing and polish

- **Modern dark theme**  
  - **`src/styles.qss`** provides a cohesive dark-mode look (charcoal grays, blue accents) for the main window, menus, toolbar, dockable panels, and dialogs.

- **Background filter processing**  
  - Heavy filter work runs in a **QThread** (**`FilterWorker`** in **`worker.py`**), so the UI stays responsive during blur, sharpen, and other filters. A progress dialog is shown while the worker runs.

- **Logging**  
  - **`main.py`** configures logging to **`app.log`** (next to the entry point) and to stderr, so support and debugging are easier when users report issues.

- **Error handling**  
  - File I/O (open/save image and project) uses try/except with user-friendly **QMessageBox** messages for permission errors, corrupted files, and invalid formats.

---

### 📦 What’s included

- Layer-based editing (add, remove, reorder, opacity, visibility)  
- Drawing tools (brush, eraser, shapes, paint bucket, eyedropper)  
- Rich filter set (blur, sharpen, brightness, contrast, hue/saturation, grayscale, invert, sepia, posterize, edge detect, emboss, smooth, detail)  
- Image transforms (flip, rotate, resize, canvas size, crop)  
- Full undo/redo (Command pattern)  
- Save/load **`.iep`** project format  
- Dockable panels (Layers, Tools, History)  
- Status bar (zoom, dimensions, cursor position)  
- Unit tests for filters and commands  
- CI/CD with pytest and flake8  
- Build script for a single executable  

---

### 📄 Documentation

- **README:** badges (build status, license), feature list, installation, usage, testing, roadmap.  
- **docs/DEVELOPMENT.md:** architecture (MVC, Command pattern), project layout, data flow, how to add filters/tools, code style, CI, logging, packaging.  
- **docs/ARCHITECTURE.md:** design patterns and component details.  
- **docs/PHOTOSHOP_FEATURES.md:** feature comparison with Photoshop-style workflows.

---

### How to use this for GitHub Releases

1. Open your repo → **Releases** → **Draft a new release**.  
2. Choose tag **v1.0.0** (create the tag if needed).  
3. Title: **Image Editor Pro v1.0.0**.  
4. Copy the contents of this file (from the first heading through the last line) into the release description.  
5. Attach build artifacts (e.g. **Image Editor Pro.exe** from **dist/**) if you want to ship binaries.  
6. Publish the release.

---

Thank you to everyone who contributed or gave feedback to reach this milestone.
