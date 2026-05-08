import os
import struct
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton,
                             QWidget, QListWidget, QApplication, QHBoxLayout,
                             QComboBox, QGroupBox)
from PyQt6.QtCore import Qt, QUrl, QRectF, QMimeData, QSize, QPointF
from PyQt6.QtGui import QDrag, QFont, QColor, QPainter, QBrush, QPen, QIcon, QPixmap, QPolygonF
from constants import BASE_PATH, CARTOON_THEME_STYLE, DARK_THEME_STYLE, LIGHT_THEME_STYLE


def theme_accent_color(theme):
    if theme == 'cartoon':
        return QColor("#3A86FF")
    return QColor("#00E5FF" if theme == 'dark' else "#2563EB")


def theme_stylesheet(theme):
    if theme == 'cartoon':
        return CARTOON_THEME_STYLE
    return DARK_THEME_STYLE if theme == 'dark' else LIGHT_THEME_STYLE


def theme_text_colors(theme):
    if theme == 'cartoon':
        return "#243B53", "#243B53"
    return ("#00E5FF", "#ECEFF1") if theme == 'dark' else ("#2563EB", "#1F2937")


def folder_icon(theme):
    if theme in ('dark', 'light'):
        icon_name = "dark-folder.png" if theme == 'dark' else "light-folder.png"
        icon_path = BASE_PATH / "assets" / icon_name
        if icon_path.exists():
            return QIcon(str(icon_path))

    pixmap = QPixmap(24, 24)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    color = theme_accent_color(theme)
    painter.setPen(QPen(color, 1.8))
    painter.setBrush(QBrush(color.lighter(115)))
    painter.drawRoundedRect(QRectF(3, 8, 18, 11), 2, 2)
    painter.drawRoundedRect(QRectF(4, 5, 8, 5), 1.5, 1.5)
    painter.end()

    return QIcon(pixmap)


def play_icon(theme):
    pixmap = QPixmap(24, 24)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    color = theme_accent_color(theme)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(color))
    painter.drawPolygon(QPolygonF([
        QPointF(8, 5),
        QPointF(8, 19),
        QPointF(18, 12),
    ]))
    painter.end()

    return QIcon(pixmap)


def pause_icon(theme):
    pixmap = QPixmap(24, 24)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    color = theme_accent_color(theme)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(color))
    painter.drawRoundedRect(QRectF(7, 5, 3.5, 14), 1, 1)
    painter.drawRoundedRect(QRectF(13.5, 5, 3.5, 14), 1, 1)
    painter.end()

    return QIcon(pixmap)


class InfoDialog(QDialog):
    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setWindowTitle("Feature Settings Guide")
        self.resize(480, 550)
        self.setStyleSheet(theme_stylesheet(theme))

        title_color, desc_color = theme_text_colors(theme)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        top_title = QLabel("Always on Top")
        top_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        top_title.setStyleSheet(f"color: {title_color};")
        top_desc = QLabel("Keeps this manager window on top of all your other running programs so it stays visible. It also monitors and forces the T-Metrics 'Customer Message Information' popup to the front whenever it appears.")
        top_desc.setWordWrap(True)
        top_desc.setFont(QFont("Segoe UI", 10))
        top_desc.setStyleSheet(f"color: {desc_color};")

        hide_title = QLabel("Hide Reviewed")
        hide_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        hide_title.setStyleSheet(f"color: {title_color};")
        hide_desc = QLabel("Instantly hides any voicemail from your main list as soon as you listen to it or mark it as reviewed. Turning this setting off will show them in the list again.")
        hide_desc.setWordWrap(True)
        hide_desc.setFont(QFont("Segoe UI", 10))
        hide_desc.setStyleSheet(f"color: {desc_color};")

        close_title = QLabel("Auto-Close Folder")
        close_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        close_title.setStyleSheet(f"color: {title_color};")
        close_desc = QLabel("When T-Metrics downloads a new voicemail, Windows forces the local file explorer folder to pop up on your screen. This setting detects that specific folder and closes it automatically so it doesn't clutter your desktop.")
        close_desc.setWordWrap(True)
        close_desc.setFont(QFont("Segoe UI", 10))
        close_desc.setStyleSheet(f"color: {desc_color};")

        sound_title = QLabel("Notification Sound")
        sound_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        sound_title.setStyleSheet(f"color: {title_color};")
        sound_desc = QLabel("Configure notification sounds in the Settings menu. Add custom sounds by placing .wav, .mp3, .flac, or .ogg files in the Voicemail_Sounds folder located in your AppData directory. Selected sounds will play when the application detects and restores the T-Metrics popup window.")
        sound_desc.setWordWrap(True)
        sound_desc.setFont(QFont("Segoe UI", 10))
        sound_desc.setStyleSheet(f"color: {desc_color};")

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_btn.setFixedWidth(100)

        layout.addWidget(top_title)
        layout.addWidget(top_desc)
        layout.addWidget(hide_title)
        layout.addWidget(hide_desc)
        layout.addWidget(close_title)
        layout.addWidget(close_desc)
        layout.addWidget(sound_title)
        layout.addWidget(sound_desc)
        layout.addSpacing(4)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)


class SettingsDialog(QDialog):
    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setWindowTitle("Settings")
        self.resize(420, 380)
        title_color, desc_color = self.apply_theme(theme)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Audio Settings Group
        audio_group = QGroupBox("Audio Settings")
        audio_group.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        audio_group.setStyleSheet(f"color: {title_color};")
        audio_layout = QVBoxLayout(audio_group)
        audio_layout.setSpacing(10)

        # Audio Output
        device_label = QLabel("Audio Output:")
        device_label.setFont(QFont("Segoe UI", 9))
        device_label.setStyleSheet(f"color: {desc_color};")
        audio_layout.addWidget(device_label)

        self.device_combo = QComboBox()
        self.device_combo.setFont(QFont("Segoe UI", 9))
        audio_layout.addWidget(self.device_combo)

        # Notification Sound
        sound_label = QLabel("Notification Sound:")
        sound_label.setFont(QFont("Segoe UI", 9))
        sound_label.setStyleSheet(f"color: {desc_color};")
        audio_layout.addWidget(sound_label)

        sound_combo_layout = QHBoxLayout()
        sound_combo_layout.setSpacing(4)

        self.test_sound_btn = QPushButton()
        self.test_sound_btn.setIcon(play_icon(theme))
        self.test_sound_btn.setIconSize(QSize(16, 16))
        self.test_sound_btn.setFixedWidth(32)
        self.test_sound_btn.setFixedHeight(24)
        self.test_sound_btn.setToolTip("Play selected notification sound")
        self.test_sound_btn.setObjectName("refresh_sounds_btn")
        self.test_sound_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        sound_combo_layout.addWidget(self.test_sound_btn)

        self.sound_combo = QComboBox()
        self.sound_combo.setFont(QFont("Segoe UI", 9))
        sound_combo_layout.addWidget(self.sound_combo)

        self.open_sounds_folder_btn = QPushButton()
        self.open_sounds_folder_btn.setIcon(folder_icon(theme))
        self.open_sounds_folder_btn.setIconSize(QSize(18, 18))
        self.open_sounds_folder_btn.setFixedWidth(32)
        self.open_sounds_folder_btn.setFixedHeight(24)
        self.open_sounds_folder_btn.setToolTip("Open notification sounds folder")
        self.open_sounds_folder_btn.setFont(QFont("Segoe UI", 9))
        self.open_sounds_folder_btn.setObjectName("refresh_sounds_btn")
        self.open_sounds_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        sound_combo_layout.addWidget(self.open_sounds_folder_btn)
        audio_layout.addLayout(sound_combo_layout)

        layout.addWidget(audio_group)

        app_group = QGroupBox("Application")
        app_group.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        app_group.setStyleSheet(f"color: {title_color};")
        app_layout = QVBoxLayout(app_group)
        app_layout.setSpacing(10)

        theme_label = QLabel("Theme:")
        theme_label.setFont(QFont("Segoe UI", 9))
        theme_label.setStyleSheet(f"color: {desc_color};")
        app_layout.addWidget(theme_label)

        self.theme_combo = QComboBox()
        self.theme_combo.setFont(QFont("Segoe UI", 9))
        self.theme_combo.addItems(["Dark", "Light"]) # Cartoon add to get cartoon theme
        app_layout.addWidget(self.theme_combo)

        self.info_btn = QPushButton("Feature Information")
        self.info_btn.setFont(QFont("Segoe UI", 9))
        self.info_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        app_layout.addWidget(self.info_btn)

        self.open_tmetrics_folder_btn = QPushButton("Open T-Metric Voicemail Folder")
        self.open_tmetrics_folder_btn.setFont(QFont("Segoe UI", 9))
        self.open_tmetrics_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        app_layout.addWidget(self.open_tmetrics_folder_btn)

        layout.addWidget(app_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.save_btn = QPushButton("Close")
        self.save_btn.setFixedWidth(80)
        self.save_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.save_btn)
        layout.addLayout(button_layout)
        self.apply_theme(theme)

    def apply_theme(self, theme):
        self.theme = theme
        self.setStyleSheet(theme_stylesheet(theme))

        title_color, desc_color = theme_text_colors(theme)

        for group_box in self.findChildren(QGroupBox):
            group_box.setStyleSheet(f"color: {title_color};")

        for label in self.findChildren(QLabel):
            label.setStyleSheet(f"color: {desc_color};")

        if hasattr(self, 'open_sounds_folder_btn'):
            self.open_sounds_folder_btn.setIcon(folder_icon(theme))
        if hasattr(self, 'test_sound_btn'):
            self.test_sound_btn.setIcon(play_icon(theme))
        action_buttons = []
        if hasattr(self, 'info_btn'):
            action_buttons.append(self.info_btn)
        if hasattr(self, 'open_tmetrics_folder_btn'):
            action_buttons.append(self.open_tmetrics_folder_btn)

        for button in action_buttons:
            if theme == 'dark':
                button.setStyleSheet(
                    "QPushButton { background-color: #009688; color: #FFFFFF; border: none; "
                    "border-radius: 4px; padding: 6px 12px; font-weight: 700; }"
                    "QPushButton:hover { background-color: #00BFA5; }"
                    "QPushButton:pressed { background-color: #00796B; }"
                )
            
            elif theme == 'cartoon':
                button.setStyleSheet(
                    "QPushButton { background-color: #FF7A59; color: #1F2937; border: 2px solid #243B53; "
                    "border-radius: 8px; padding: 7px 12px; font-weight: 800; }"
                    "QPushButton:hover { background-color: #FFB703; }"
                   "QPushButton:pressed { background-color: #FB5607; color: #FFFFFF; }"
                )
        
            else:
                button.setStyleSheet(
                    "QPushButton { background-color: #2563EB; color: #FFFFFF; border: none; "
                    "border-radius: 6px; padding: 8px 12px; font-weight: 700; }"
                    "QPushButton:hover { background-color: #1E40AF; }"
                    "QPushButton:pressed { background-color: #1E40AF; }"
                )

        return title_color, desc_color


class WaveformProgressBar(QWidget):
    def __init__(self, theme='dark', parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setMinimumHeight(55)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.peaks = []
        self.duration_ms = 0
        self.position_ms = 0
        self._is_dragging = False
        self.on_seek_requested = None

    def set_theme(self, theme):
        self.theme = theme
        self.update()

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

        # Theme-based colors
        if self.theme == 'dark':
            bg_color = QColor("#263238")
            no_waveform_color = QColor("#546E7A")
            played_color = QColor("#00E676")
            unplayed_color = QColor("#78909C")
            progress_color = QColor("#00E5FF")
        elif self.theme == 'cartoon':
            bg_color = QColor("#FFFFFF")
            no_waveform_color = QColor("#243B53")
            played_color = QColor("#3A86FF")
            unplayed_color = QColor("#FFB703")
            progress_color = QColor("#FB5607")
        else:  # light theme
            bg_color = QColor("#F9FAFB")
            no_waveform_color = QColor("#6B7280")
            played_color = QColor("#2563EB")
            unplayed_color = QColor("#9CA3AF")
            progress_color = QColor("#2563EB")

        painter.fillRect(0, 0, w, h, QBrush(bg_color))

        if not self.peaks:
            painter.setPen(QPen(no_waveform_color, 1, Qt.PenStyle.DotLine))
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
                painter.fillRect(QRectF(x, y, bar_w, bar_h), QBrush(played_color))
            else:
                painter.fillRect(QRectF(x, y, bar_w, bar_h), QBrush(unplayed_color))

        painter.setPen(QPen(progress_color, 1))
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
