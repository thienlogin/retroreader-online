"""TiemSach.org Scraper v2 — Scrape + Download ngay lập tức

Mỗi truyện tìm thấy → vào trang chi tiết → tìm link → download luôn epub + cover.
"""

import sys
import os
import re
import time
import urllib.request
import urllib.parse
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QProgressBar, QTableWidget, QTableWidgetItem,
    QHeaderView, QComboBox, QGroupBox, QFileDialog, QLineEdit, QTextEdit
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor

from DrissionPage import ChromiumPage, ChromiumOptions


DEFAULT_OUTPUT = r"C:\chum\trimui\retroreader-online\novels"


class ScraperWorker(QThread):
    """Scrape → Extract → Download ngay cho từng cuốn."""

    log = pyqtSignal(str)
    add_row = pyqtSignal(str, str, str, str)  # title, author, category, status
    update_status = pyqtSignal(int, str, str)  # row, status, color
    progress = pyqtSignal(int, int)
    done = pyqtSignal()

    def __init__(self, pages, fmt, output_dir, parent=None):
        super().__init__(parent)
        self.pages = pages
        self.fmt = fmt
        self.output_dir = Path(output_dir)
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            self._do_scrape()
        except Exception as e:
            self.log.emit(f"[FATAL] {e}")
        self.done.emit()

    def _download_file(self, url, dest, referer=""):
        """Download file with retry."""
        # Fix URLs with spaces or special chars
        if url.startswith("/"):
            url = "https://tiemsach.org" + url
        # Encode spaces and special chars in the path
        parsed = urllib.parse.urlparse(url)
        encoded_path = urllib.parse.quote(parsed.path, safe="/")
        url = urllib.parse.urlunparse(parsed._replace(path=encoded_path))

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        if referer:
            headers["Referer"] = referer
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data = resp.read()
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(data)
                    return len(data)
            except Exception as e:
                if attempt == 2:
                    raise
                time.sleep(2)
        return 0

    def _do_scrape(self):
        self.log.emit("Starting Chrome browser...")
        co = ChromiumOptions()
        co.set_argument("--disable-gpu")
        co.set_argument("--no-sandbox")
        page = ChromiumPage(co)

        # Collect book URLs from homepage
        book_list = []
        for pg in range(1, self.pages + 1):
            if self._stop:
                break
            url = f"https://tiemsach.org/page/{pg}" if pg > 1 else "https://tiemsach.org"
            self.log.emit(f"📄 Loading page {pg}...")
            page.get(url)
            time.sleep(2)

            items = page.eles("css:.book-item")
            self.log.emit(f"   Found {len(items)} books on page {pg}")

            for el in items:
                try:
                    link = el.attr("href") or ""
                    if not link or link in [b["url"] for b in book_list]:
                        continue

                    h3 = el.ele("css:h3", timeout=1)
                    title = h3.text.strip() if h3 else "Unknown"
                    auth_el = el.ele("css:.has-small-font-size", timeout=1)
                    author = auth_el.text.strip() if auth_el else ""

                    img = el.ele("css:img", timeout=1)
                    cover = ""
                    if img:
                        cover = img.attr("data-src") or img.attr("src") or ""
                        if "svg+xml" in cover:
                            cover = img.attr("data-src") or ""

                    book_list.append({
                        "title": title, "author": author,
                        "url": link, "cover": cover,
                    })
                except Exception:
                    pass

        # De-duplicate
        seen = set()
        unique = []
        for b in book_list:
            if b["url"] not in seen:
                seen.add(b["url"])
                unique.append(b)
        book_list = unique

        self.log.emit(f"\n✅ Total unique books: {len(book_list)}")

        # Add all to table
        for b in book_list:
            self.add_row.emit(b["title"], b["author"], "", "⏳ Queued")

        # Visit each book → find links → download immediately
        total = len(book_list)
        downloaded = 0
        failed = 0

        for i, book in enumerate(book_list):
            if self._stop:
                break

            self.progress.emit(i + 1, total)
            title = book["title"]
            self.log.emit(f"\n📖 [{i+1}/{total}] {title}")

            # Safe filename
            safe_title = re.sub(r'[<>:"/\\|?*]', '_', title).strip()[:80]

            try:
                # Visit book detail page
                self.update_status.emit(i, "🔍 Loading...", "#2196F3")
                page.get(book["url"])
                time.sleep(2)

                # Get category from breadcrumb
                category = ""
                try:
                    crumbs = page.eles("css:#breadcrumb a")
                    if len(crumbs) >= 2:
                        category = crumbs[-1].text.strip()
                except Exception:
                    pass

                # Find download links in #files section
                dl_url = None
                dl_fmt = self.fmt

                # Wait for JS to render download section
                files_el = page.ele("css:#files", timeout=5)
                if files_el:
                    links = files_el.eles("css:a")
                    found_links = {}
                    for lnk in links:
                        href = lnk.attr("href") or ""
                        text = (lnk.text or "").strip().lower()
                        for f in ["epub", "pdf", "mobi", "azw3"]:
                            if f".{f}" in href.lower() or f == text:
                                found_links[f] = href

                    # Also check anchor IDs
                    for f in ["epub", "pdf", "mobi", "azw3"]:
                        el = page.ele(f"css:#download-{f}", timeout=0.5)
                        if el:
                            h = el.attr("href")
                            if h:
                                found_links[f] = h

                    # Also scan all links on page for direct file URLs
                    if not found_links:
                        all_links = page.eles("css:a")
                        for lnk in all_links:
                            href = lnk.attr("href") or ""
                            for f in ["epub", "pdf", "mobi", "azw3"]:
                                if f".{f}" in href.lower():
                                    found_links[f] = href

                    if found_links:
                        self.log.emit(f"   Links found: {', '.join(found_links.keys())}")
                        # Pick preferred format
                        dl_url = found_links.get(self.fmt)
                        if not dl_url:
                            for alt in ["epub", "pdf", "mobi", "azw3"]:
                                if alt in found_links:
                                    dl_url = found_links[alt]
                                    dl_fmt = alt
                                    break

                if not dl_url:
                    self.log.emit(f"   ❌ No download link found")
                    self.update_status.emit(i, "❌ No link", "#f44336")
                    failed += 1
                    continue

                # Create output folder by category
                safe_cat = re.sub(r'[<>:"/\\|?*]', '_', category) if category else "Khác"
                out_dir = self.output_dir / safe_cat
                out_dir.mkdir(parents=True, exist_ok=True)

                # Download ebook
                book_path = out_dir / f"{safe_title}.{dl_fmt}"
                if book_path.exists():
                    self.log.emit(f"   ⏩ Already exists, skip")
                    self.update_status.emit(i, "⏩ Exists", "#FF9800")
                    continue

                self.update_status.emit(i, f"⬇️ Downloading .{dl_fmt}...", "#2196F3")
                size = self._download_file(dl_url, book_path, referer=book["url"])
                size_kb = size / 1024
                self.log.emit(f"   ✅ Saved {safe_title}.{dl_fmt} ({size_kb:.0f} KB)")

                # Download cover
                if book["cover"]:
                    cover_path = out_dir / f"{safe_title}.jpg"
                    if not cover_path.exists():
                        try:
                            self._download_file(book["cover"], cover_path)
                            self.log.emit(f"   🖼️ Cover saved")
                        except Exception:
                            self.log.emit(f"   ⚠️ Cover failed")

                self.update_status.emit(i, f"✅ {size_kb:.0f}KB", "#4CAF50")
                downloaded += 1

            except Exception as e:
                self.log.emit(f"   ❌ Error: {e}")
                self.update_status.emit(i, f"❌ Error", "#f44336")
                failed += 1

            time.sleep(1)  # Be nice to server

        try:
            page.quit()
        except Exception:
            pass

        self.log.emit(f"\n{'='*50}")
        self.log.emit(f"🏁 Done! Downloaded: {downloaded}, Failed: {failed}, Total: {total}")
        self.log.emit(f"📂 Output: {self.output_dir}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📚 TiemSach.org Scraper — RetroReader Online")
        self.setMinimumSize(950, 700)
        self.worker = None
        self._setup_ui()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)

        # Title
        title = QLabel("📚 TiemSach.org Scraper")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Output folder
        folder_group = QGroupBox("📂 Output Folder")
        folder_layout = QHBoxLayout(folder_group)
        self.folder_input = QLineEdit(DEFAULT_OUTPUT)
        self.folder_input.setFont(QFont("Consolas", 10))
        folder_layout.addWidget(self.folder_input)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_folder)
        folder_layout.addWidget(browse_btn)
        layout.addWidget(folder_group)

        # Controls
        ctrl_group = QGroupBox("⚙️ Settings")
        ctrl_layout = QHBoxLayout(ctrl_group)

        ctrl_layout.addWidget(QLabel("Pages:"))
        self.pages_combo = QComboBox()
        self.pages_combo.addItems(["1", "2", "3", "5", "10"])
        ctrl_layout.addWidget(self.pages_combo)

        ctrl_layout.addWidget(QLabel("Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["epub", "pdf", "mobi", "azw3"])
        ctrl_layout.addWidget(self.format_combo)

        ctrl_layout.addStretch()

        self.start_btn = QPushButton("🚀 Start")
        self.start_btn.setFixedSize(120, 40)
        self.start_btn.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.start_btn.setStyleSheet(
            "QPushButton{background:#2196F3;color:white;border-radius:6px}"
            "QPushButton:hover{background:#1976D2}"
            "QPushButton:disabled{background:#999}")
        self.start_btn.clicked.connect(self._start)
        ctrl_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setFixedSize(100, 40)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet(
            "QPushButton{background:#f44336;color:white;border-radius:6px}"
            "QPushButton:hover{background:#d32f2f}"
            "QPushButton:disabled{background:#999}")
        self.stop_btn.clicked.connect(self._stop)
        ctrl_layout.addWidget(self.stop_btn)

        layout.addWidget(ctrl_group)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(22)
        self.progress_bar.setStyleSheet(
            "QProgressBar{border:1px solid #ccc;border-radius:4px;text-align:center}"
            "QProgressBar::chunk{background:#4CAF50;border-radius:3px}")
        layout.addWidget(self.progress_bar)

        self.status_lbl = QLabel("Ready")
        layout.addWidget(self.status_lbl)

        # Table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Title", "Author", "Category", "Status"])
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("QTableWidget{font-size:13px}")
        layout.addWidget(self.table, stretch=3)

        # Log
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumHeight(160)
        self.log_box.setFont(QFont("Consolas", 9))
        self.log_box.setStyleSheet("background:#1e1e1e;color:#d4d4d4;border-radius:4px")
        layout.addWidget(self.log_box, stretch=1)

    def _browse_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Select Output Folder", self.folder_input.text())
        if d:
            self.folder_input.setText(d)

    def _start(self):
        self.table.setRowCount(0)
        self.log_box.clear()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        self.worker = ScraperWorker(
            pages=int(self.pages_combo.currentText()),
            fmt=self.format_combo.currentText(),
            output_dir=self.folder_input.text(),
        )
        self.worker.log.connect(self._on_log)
        self.worker.add_row.connect(self._on_add_row)
        self.worker.update_status.connect(self._on_update_status)
        self.worker.progress.connect(self._on_progress)
        self.worker.done.connect(self._on_done)
        self.worker.start()

    def _stop(self):
        if self.worker:
            self.worker.stop()

    def _on_log(self, msg):
        self.log_box.append(msg)
        sb = self.log_box.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_add_row(self, title, author, cat, status):
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, QTableWidgetItem(title))
        self.table.setItem(r, 1, QTableWidgetItem(author))
        self.table.setItem(r, 2, QTableWidgetItem(cat))
        self.table.setItem(r, 3, QTableWidgetItem(status))

    def _on_update_status(self, row, status, color):
        if row < self.table.rowCount():
            item = QTableWidgetItem(status)
            item.setForeground(QColor(color))
            self.table.setItem(row, 3, item)
            self.table.scrollToItem(item)
            self.status_lbl.setText(f"{status} — {self.table.item(row, 0).text()}")

    def _on_progress(self, cur, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(cur)

    def _on_done(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_lbl.setText("🏁 Done!")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())
