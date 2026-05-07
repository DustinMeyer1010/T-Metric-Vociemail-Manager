import os
import struct
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton,
                             QWidget, QListWidget, QApplication)
from PyQt6.QtCore import Qt, QUrl, QRectF, QMimeData
from PyQt6.QtGui import QDrag, QFont, QColor, QPainter, QBrush, QPen
from constants import DARK_THEME_STYLE


class InfoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Feature Settings Guide")
        self.resize(440, 310)
        self.setStyleSheet(DARK_THEME_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        top_title = QLabel("Always on Top")
        top_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        top_title.setStyleSheet("color: #00E5FF;")
        top_desc = QLabel("Keeps this manager window on top of all your other running programs so it stays visible. It also monitors and forces the T-Metrics 'Customer Message Information' popup to the front whenever it appears.")
        top_desc.setWordWrap(True)
        top_desc.setFont(QFont("Segoe UI", 10))
        top_desc.setStyleSheet("color: #ECEFF1;")

        hide_title = QLabel("Hide Reviewed")
        hide_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        hide_title.setStyleSheet("color: #00E5FF;")
        hide_desc = QLabel("Instantly hides any voicemail from your main list as soon as you listen to it or mark it as reviewed. Turning this setting off will show them in the list again.")
        hide_desc.setWordWrap(True)
        hide_desc.setFont(QFont("Segoe UI", 10))
        hide_desc.setStyleSheet("color: #ECEFF1;")

        close_title = QLabel("Auto-Close Folder")
        close_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        close_title.setStyleSheet("color: #00E5FF;")
        close_desc = QLabel("When T-Metrics downloads a new voicemail, Windows forces the local file explorer folder to pop up on your screen. This setting detects that specific folder and closes it automatically so it doesn't clutter your desktop.")
        close_desc.setWordWrap(True)
        close_desc.setFont(QFont("Segoe UI", 10))
        close_desc.setStyleSheet("color: #ECEFF1;")

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_btn.setFixedWidth(100)

        layout.addWidget(top_title)
        layout.addWidget(top_desc)
        layout.addWidget(hide_title)
        layout.addWidget(hide_desc)
        layout.addWidget(close_title)
        layout.addWidget(close_desc)
        layout.addSpacing(4)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)


class WaveformProgressBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(55)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.peaks = []
        self.duration_ms = 0
        self.position_ms = 0
        self._is_dragging = False
        self.on_seek_requested = None

    def set_waveform(self, file_path):
        self.peaks = []
        self.position_ms = 0
        if not file_path or not os.path.exists(file_path):
            self.update()
            return

        try:
            with open(file_path, 'rb') as f:
                f.seek(22)
                num_channels = struct.unpack('<H', f.read(2))[0]
                f.seek(34)
                bits_per_sample = struct.unpack('<H', f.read(2))[0]

                f.seek(44)
                raw_data = f.read(256000)

                sample_step = 2 if bits_per_sample == 16 else 1
                fmt = '<h' if bits_per_sample == 16 else '<b'

                temp_samples = []
                for i in range(0, len(raw_data) - sample_step, sample_step * 32):
                    val = struct.unpack(fmt, raw_data[i:i+sample_step])[0]
                    temp_samples.append(abs(val))

                if not temp_samples:
                    self.update()
                    return

                target_bars = 150
                chunk_size = max(1, len(temp_samples) // target_bars)
                max_possible = max(temp_samples) if max(temp_samples) > 0 else 1

                for i in range(0, len(temp_samples), chunk_size):
                    chunk = temp_samples[i:i+chunk_size]
                    avg_peak = sum(chunk) / len(chunk) if chunk else 0
                    self.peaks.append(avg_peak / max_possible)
                    if len(self.peaks) >= target_bars:
                        break
        except Exception as e:
            print(f"Error parsing waveform peaks: {e}")
            self.peaks = []

        self.update()

    def set_range(self, max_ms):
        self.duration_ms = max_ms
        self.update()

    def set_value(self, current_ms):
        if not self._is_dragging:
            self.position_ms = current_ms
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        painter.fillRect(0, 0, w, h, QBrush(QColor("#263238")))

        if not self.peaks:
            painter.setPen(QPen(QColor("#546E7A"), 1, Qt.PenStyle.DotLine))
            painter.drawLine(20, h // 2, w - 20, h // 2)
            return

        progress_ratio = self.position_ms / self.duration_ms if self.duration_ms > 0 else 0
        progress_x = int(progress_ratio * w)

        num_bars = len(self.peaks)
        bar_gap = 1
        total_gaps_w = (num_bars - 1) * bar_gap
        bar_w = max(1.0, (w - total_gaps_w) / num_bars)

        for i, peak in enumerate(self.peaks):
            x = i * (bar_w + bar_gap)
            bar_h = max(2.0, peak * (h - 15))
            y = (h - bar_h) / 2

            if x <= progress_x:
                painter.fillRect(QRectF(x, y, bar_w, bar_h), QBrush(QColor("#00E676")))
            else:
                painter.fillRect(QRectF(x, y, bar_w, bar_h), QBrush(QColor("#78909C")))

        painter.setPen(QPen(QColor("#00E5FF"), 1))
        painter.drawLine(progress_x, 0, progress_x, h)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self.handle_click_or_drag(event.pos().x())

    def mouseMoveEvent(self, event):
        if self._is_dragging:
            self.handle_click_or_drag(event.pos().x())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False

    def handle_click_or_drag(self, local_x):
        w = self.width()
        if w <= 0 or self.duration_ms <= 0:
            return
        ratio = max(0.0, min(1.0, local_x / w))
        self.position_ms = int(ratio * self.duration_ms)
        self.update()
        if self.on_seek_requested:
            self.on_seek_requested(self.position_ms)


class DraggableListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setEditTriggers(QListWidget.EditTrigger.NoEditTriggers)
        self.setFont(QFont("Segoe UI", 11))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton) or \
           (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return
        item = self.currentItem()
        if item:
            file_path = item.data(Qt.ItemDataRole.UserRole)
            if file_path and os.path.exists(file_path):
                drag = QDrag(self)
                mime_data = QMimeData()
                mime_data.setUrls([QUrl.fromLocalFile(file_path)])
                drag.setMimeData(mime_data)
                drag.exec(Qt.DropAction.CopyAction)
