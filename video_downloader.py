import os
import sys
import subprocess
import yt_dlp

from PySide6.QtCore import QObject, QThread, Signal, Qt
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QRadioButton, QButtonGroup, QPushButton, QProgressBar, QFileDialog,
    QMessageBox, QFrame, QComboBox,
)
from qt_material import apply_stylesheet


class DownloadWorker(QObject):
    progress = Signal(float, str)
    status = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, url, save_path, quality, ffmpeg_path):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self.quality = quality
        self.ffmpeg_path = ffmpeg_path

    def run(self):
        try:
            ydl_opts = {
                'outtmpl': os.path.join(self.save_path, '%(title)s.%(ext)s'),
                'progress_hooks': [self.progress_hook],
            }

            if self.ffmpeg_path:
                ydl_opts['ffmpeg_location'] = self.ffmpeg_path

            if self.quality == "audio":
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                })
            elif self.quality == "best":
                ydl_opts.update({
                    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                    'merge_output_format': 'mp4',
                })
            elif self.quality == "720":
                ydl_opts.update({
                    'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]',
                    'merge_output_format': 'mp4',
                })
            elif self.quality == "480":
                ydl_opts.update({
                    'format': 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best[height<=480]',
                    'merge_output_format': 'mp4',
                })

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])

            self.finished.emit(True, "Download completed successfully!")

        except Exception as e:
            self.finished.emit(False, str(e))

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            try:
                percent = float(d.get('_percent_str', '0%').replace('%', ''))
                info = f"{d.get('_speed_str', '')} - ETA {d.get('_eta_str', '')}"
                self.progress.emit(percent, info)
            except (ValueError, TypeError):
                pass
        elif d['status'] == 'finished':
            self.status.emit("Processing...")


class VideoDownloader(QWidget):
    THEMES = {
        "Light": "light_blue.xml",
        "Dark": "dark_teal.xml",
        "Pink": "light_pink_500.xml",
        "Purple": "light_purple_500.xml",
        "Green": "light_green_500.xml",
        "Orange": "light_orange_500.xml",
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Downloader")
        self.setFixedSize(620, 540)
        self.ffmpeg_path = self.get_ffmpeg_path()
        self.thread = None
        self.worker = None

        self.build_ui()

    def get_ffmpeg_path(self):
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))

        for candidate in (
            os.path.join(base_path, "ffmpeg", "bin", "ffmpeg.exe"),
            os.path.join(os.getcwd(), "ffmpeg", "bin", "ffmpeg.exe"),
        ):
            if os.path.exists(candidate):
                return candidate

        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            return "ffmpeg"
        except Exception:
            return None

    def build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(14)

        title = QLabel("Video Downloader")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        root.addWidget(title)

        subtitle = QLabel("Download videos from any site with yt-dlp")
        subtitle.setStyleSheet("color: gray;")
        subtitle.setAlignment(Qt.AlignCenter)
        root.addWidget(subtitle)

        url_row = QHBoxLayout()
        self.url_entry = QLineEdit()
        self.url_entry.setPlaceholderText("Paste video URL here...")
        url_row.addWidget(self.url_entry, stretch=1)
        root.addLayout(url_row)

        quality_group = QFrame()
        quality_group.setFrameShape(QFrame.StyledPanel)
        q_layout = QVBoxLayout(quality_group)
        q_layout.setContentsMargins(14, 10, 14, 12)
        q_layout.setSpacing(6)

        q_label = QLabel("Quality / Format")
        q_label.setStyleSheet("font-weight: bold;")
        q_layout.addWidget(q_label)

        self.quality_group = QButtonGroup(self)
        qualities = [
            ("MP4 - Best Quality (1080p+)", "best"),
            ("MP4 - Medium Quality (720p)", "720"),
            ("MP4 - Low Quality (480p)", "480"),
            ("MP3 - Audio Only", "audio"),
        ]
        for i, (text, value) in enumerate(qualities):
            rb = QRadioButton(text)
            rb.setProperty("quality", value)
            if i == 0:
                rb.setChecked(True)
            self.quality_group.addButton(rb)
            q_layout.addWidget(rb)

        root.addWidget(quality_group)

        loc_row = QHBoxLayout()
        self.location_entry = QLineEdit()
        self.location_entry.setText(os.path.join(os.path.expanduser("~"), "Downloads"))
        browse_btn = QPushButton("Browse")
        browse_btn.setFixedWidth(90)
        browse_btn.clicked.connect(self.browse_location)
        loc_row.addWidget(QLabel("Save to:"))
        loc_row.addWidget(self.location_entry, stretch=1)
        loc_row.addWidget(browse_btn)
        root.addLayout(loc_row)

        theme_row = QHBoxLayout()
        theme_row.addWidget(QLabel("Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(self.THEMES.keys()))
        self.theme_combo.currentTextChanged.connect(self.change_theme)
        theme_row.addWidget(self.theme_combo)
        theme_row.addStretch(1)
        root.addLayout(theme_row)

        self.download_btn = QPushButton("Download")
        self.download_btn.setFixedHeight(44)
        self.download_btn.setStyleSheet(
            "font-size: 15px; font-weight: bold; background-color: #43A047; color: white;"
        )
        self.download_btn.clicked.connect(self.start_download)
        root.addWidget(self.download_btn)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        root.addWidget(self.progress)

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: gray;")
        self.status_label.setAlignment(Qt.AlignCenter)
        root.addWidget(self.status_label)

        if not self.ffmpeg_path:
            self.status_label.setText("Warning: FFmpeg not found!")
            self.status_label.setStyleSheet("color: #C62828;")

        root.addStretch(1)

    def browse_location(self):
        folder = QFileDialog.getExistingDirectory(self, "Select save location")
        if folder:
            self.location_entry.setText(folder)

    def change_theme(self, name):
        apply_stylesheet(QApplication.instance(), theme=self.THEMES[name])

    def start_download(self):
        url = self.url_entry.text().strip()
        if not url:
            QMessageBox.warning(self, "Error", "Please enter a URL")
            return

        save_path = self.location_entry.text().strip()
        if not os.path.exists(save_path):
            QMessageBox.warning(self, "Error", "Invalid save location")
            return

        quality = self.quality_group.checkedButton().property("quality")

        self.download_btn.setEnabled(False)
        self.download_btn.setText("Downloading...")
        self.status_label.setText("Starting download...")
        self.status_label.setStyleSheet("color: #1565C0;")

        self.thread = QThread(self)
        self.worker = DownloadWorker(url, save_path, quality, self.ffmpeg_path)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.on_progress)
        self.worker.status.connect(self.on_status)
        self.worker.finished.connect(self.on_finished)
        self.worker.finished.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def on_progress(self, percent, info):
        self.progress.setValue(int(percent))
        self.status_label.setText(f"Downloading: {info}")
        self.status_label.setStyleSheet("color: #1565C0;")

    def on_status(self, text):
        self.status_label.setText(text)
        self.status_label.setStyleSheet("color: #EF6C00;")

    def on_finished(self, success, message):
        self.download_btn.setEnabled(True)
        self.download_btn.setText("Download")
        self.progress.setValue(0 if not success else 100)

        if success:
            self.status_label.setText(message)
            self.status_label.setStyleSheet("color: #2E7D32;")
            QMessageBox.information(self, "Success", message)
        else:
            self.status_label.setText(f"Error: {message}")
            self.status_label.setStyleSheet("color: #C62828;")
            QMessageBox.critical(self, "Error", message)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    apply_stylesheet(app, theme="light_blue.xml")
    window = VideoDownloader()
    window.show()
    sys.exit(app.exec())
