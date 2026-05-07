import os
import re
import sys
import shutil
import ctypes
import struct
from pathlib import Path
import time
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QListWidget, QListWidgetItem, QLabel, QHBoxLayout, 
                             QPushButton, QMessageBox, QInputDialog, QLineEdit,
                             QComboBox, QSlider, QCheckBox, QTextEdit, QDialog)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaDevices, QSoundEffect
from PyQt6.QtCore import Qt, QMimeData, QUrl, QSize, QFileSystemWatcher, QTimer, QRectF, QRegularExpression, pyqtSignal, QThread
from PyQt6.QtGui import QClipboard, QRegularExpressionValidator, QDrag, QFont, QIcon, QColor, QPainter, QBrush, QPen

# Win32 COM library for deep Windows Shell inspection
try:
    import win32com.client
except ImportError:
    win32com = None

try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WhisperModel = None
    WHISPER_AVAILABLE = False

# Paths
SOURCE_DIR = Path(os.getenv('APPDATA')) / "T-Metrics, Inc" / "ACD Agent Module" / "Downloads"
ICON_PATH = "URMC.ico"

# Persistent Cache, Config, and Workspace Paths Consolidated in AppData
CACHE_DIR = Path(os.getenv('APPDATA')) / "T-Metrics, Inc" / "VoicemailManager"
WORKSPACE_DIR = CACHE_DIR / "Voicemail_Workspace"
CACHE_FILE = CACHE_DIR / "reviewed_cache.txt"
CONFIG_FILE = CACHE_DIR / "config.txt"

# Ensure directories exist
CACHE_DIR.mkdir(parents=True, exist_ok=True)
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

# Windows API Configurations for pinning external windows
HWND_TOPMOST = -1
SW_RESTORE = 9
SW_SHOWNOACTIVATE = 4
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
TOPMOST_FLAGS = SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
CUSTOM_RESTORE_SOUND = Path(os.path.dirname(os.path.abspath(__file__))) / "restore_sound.wav"

# Define Win32 Callback for window iteration
EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

PHONE_REGEX_PATTERNS = [
    r"\+?1[\s\-\.]*\(?([2-9]\d{2})\)?[\s\-\.]*([2-9]\d{2})[\s\-\.]*([0-9]{4})",
    r"\b([2-9]\d{2})[\s\-\.]*([2-9]\d{2})[\s\-\.]*([0-9]{4})\b",
    r"\b([2-9]\d{2})[\s\-\.]*([0-9]{4})\b",
    r"\b(\d{10})\b",
]


def extract_phone_from_transcript(transcript):
    if not transcript:
        return ""
    for pattern in PHONE_REGEX_PATTERNS:
        match = re.search(pattern, transcript)
        if match:
            return "".join(match.groups())
    digits = ''.join(ch for ch in transcript if ch.isdigit())
    if len(digits) >= 10:
        return digits[:10]
    if len(digits) >= 7:
        return digits[:7]
    return ""


class TranscriptionWorker(QThread):
    result_ready = pyqtSignal(str, str, str)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    def run(self):
        if not WHISPER_AVAILABLE:
            self.result_ready.emit("", "", "Install faster-whisper to enable transcription.")
            return

        try:
            model = WhisperModel("small", device="cpu", compute_type="int8")
            segments, _ = model.transcribe(str(self.file_path), beam_size=5, language="en")
            transcript = " ".join(segment.text.strip() for segment in segments if segment.text.strip())
            phone = extract_phone_from_transcript(transcript)
            self.result_ready.emit(transcript, phone, "")
        except Exception as exc:
            self.result_ready.emit("", "", f"Transcription failed: {exc}")

# --- FULL DARK THEME DESIGN STYLESHEET (QSS) ---
DARK_THEME_STYLE = """
    QMainWindow {
        background-color: #1E272C;
    }
    
    QLabel {
        color: #FFFFFF;
    }
    
    /* Premium Modern Electric Teal Buttons */
    QPushButton {
        background-color: #009688;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 6px 16px;
        font-family: "Segoe UI", sans-serif;
        font-weight: 600;
        font-size: 12px;
        min-width: 75px;
    }

    QPushButton#copy_btn {
        width: 125px;
        height: 13px;
    }

    QPushButton#play_btn {
        padding: 0px 0px;
        width: 25px;
        height: 42px;
        min-width: 25px;
    }

    QPushButton:hover {
        background-color: #00BFA5;
    }
    QPushButton:pressed {
        background-color: #00796B;
    }
    QPushButton:disabled {
        background-color: #37474F;
        color: #78909C;
    }
    
    /* Info Button Specific Styling */
    QPushButton#info_btn {
        background-color: transparent;
        color: #00E5FF;
        font-size: 13pt;
        font-weight: bold;
        padding: 0px;
        min-width: 28px;
        max-width: 28px;
        min-height: 28px;
        max-height: 28px;
    }
    QPushButton#info_btn:hover {
        background-color: #009688;
        color: white;
    }

    /* Bulk Action Button Styling */
    QPushButton#delete_all_btn {
        background-color: #455A64;
    }
    QPushButton#delete_all_btn:hover {
        background-color: #546E7A;
    }
    QPushButton#delete_all_btn:pressed {
        background-color: #37474F;
    }
    
    /* Dark Theme Voicemail Row List Container */
    QListWidget {
        background-color: #263238;
        border: 1px solid #37474F;
        border-radius: 6px;
        padding: 5px;
    }
    QListWidget::item {
        border-bottom: 1px solid #37474F;
        padding: 8px;
        margin-bottom: 2px;
        border-radius: 4px;
        color: #ECEFF1;
    }
    QListWidget::item:hover {
        background-color: #37474F;
        color: #00E5FF;
    }
    QListWidget::item:selected {
        background-color: #004D40;
        color: #00E5FF;
        font-weight: 500;
        border: 1px solid #00796B;
    }
    
    /* Modernized Dark Theme Checkboxes */
    QCheckBox {
        spacing: 8px;
        color: #ECEFF1;
    }
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border: 2px solid #546E7A;
        border-radius: 3px;
        background-color: #263238;
    }
    QCheckBox::indicator:hover {
        border-color: #009688;
    }
    QCheckBox::indicator:checked {
        background-color: #009688;
        border-color: #009688;
    }

    /* Audio Selection Dropdown Menu styling */
    QComboBox {
        border: 1px solid #37474F;
        border-radius: 4px;
        padding: 4px 8px;
        background-color: #263238;
        color: #FFFFFF;
    }
    QComboBox:hover {
        border-color: #009688;
    }
    QComboBox::drop-down {
        border: none;
    }
    
    /* Dropdown Internal List Engine Configurations */
    QComboBox QAbstractItemView {
        background-color: #263238;
        border: 1px solid #455A64;
        border-radius: 4px;
        padding: 4px;
        color: #FFFFFF;
        outline: 0px;
        selection-background-color: #009688;
    }
    QComboBox QAbstractItemView::item {
        padding: 6px;
        border-radius: 3px;
        color: #FFFFFF;
        background-color: transparent;
    }
    QComboBox QAbstractItemView::item:hover,
    QComboBox QAbstractItemView::item:selected {
        background-color: #009688 !important;
        color: #FFFFFF !important;
    }
    
    /* Inputs & Modals */
    QDialog {
        background-color: #1E272C;
    }
    QInputDialog {
        background-color: #1E272C;
    }
    QInputDialog QLabel {
        margin-bottom: 6px;
        font-size: 11pt;
    }
    QLineEdit {
        background-color: #263238;
        border: 1px solid #37474F;
        border-radius: 6px;
        padding: 8px 10px;
        color: #FFFFFF;
        font-size: 11pt;
        selection-background-color: #009688;
    }
    QLineEdit:focus {
        border: 1px solid #00E5FF;
    }

    /* Compact Workspace Sidebar Note Field Stylesheet */
    QTextEdit {
        background-color: #263238;
        border: 1px solid #37474F;
        border-radius: 6px;
        color: #FFFFFF;
        padding: 6px;
        font-family: "Segoe UI", sans-serif;
        font-size: 10pt;
    }
    QTextEdit:focus {
        border: 1px solid #009688;
    }
    QTextEdit:disabled {
        background-color: #1A2226;
        color: #546E7A;
        border-color: #263238;
    }
"""

class InfoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Feature Settings Guide")
        self.resize(440, 310)
        self.setStyleSheet(DARK_THEME_STYLE)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)
        
        # Always on top explanation
        top_title = QLabel("Always on Top")
        top_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        top_title.setStyleSheet("color: #00E5FF;")
        top_desc = QLabel("Keeps this manager window on top of all your other running programs so it stays visible. It also monitors and forces the T-Metrics 'Customer Message Information' popup to the front whenever it appears.")
        top_desc.setWordWrap(True)
        top_desc.setFont(QFont("Segoe UI", 10))
        top_desc.setStyleSheet("color: #ECEFF1;")
        
        # Hide Reviewed explanation
        hide_title = QLabel("Hide Reviewed")
        hide_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        hide_title.setStyleSheet("color: #00E5FF;")
        hide_desc = QLabel("Instantly hides any voicemail from your main list as soon as you listen to it or mark it as reviewed. Turning this setting off will show them in the list again.")
        hide_desc.setWordWrap(True)
        hide_desc.setFont(QFont("Segoe UI", 10))
        hide_desc.setStyleSheet("color: #ECEFF1;")
        
        # Auto-Close Folder explanation
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
                drag = QDrag(self); mime_data = QMimeData()
                mime_data.setUrls([QUrl.fromLocalFile(file_path)])
                drag.setMimeData(mime_data); drag.exec(Qt.DropAction.CopyAction)


class VoicemailManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("T-Metric Voicemail Manager")
        self.resize(820, 580) 
        
        if os.path.exists(ICON_PATH):
            self.setWindowIcon(QIcon(ICON_PATH))

        initial_topmost = self.peek_always_on_top_config()
        if initial_topmost:
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.restore_sound = QSoundEffect()
        if CUSTOM_RESTORE_SOUND.exists():
            self.restore_sound.setSource(QUrl.fromLocalFile(str(CUSTOM_RESTORE_SOUND)))
            self.restore_sound.setVolume(0.8)
        else:
            self.restore_sound = None
        self.reviewed_files = set()
        self.current_file_duration_ms = 0
        self.known_workspace_signatures = set()

        central_widget = QWidget(); self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)
        
        # --- TOP HEADER ROW ---
        header_layout = QHBoxLayout()
        self.status_label = QLabel("Initializing application...")
        self.status_label.setFont(QFont("Segoe UI Semibold", 10))
        header_layout.addWidget(self.status_label)
        
        header_layout.addStretch()
        
        # Info button pinned directly into the header layout row
        self.info_btn = QPushButton("ⓘ")
        self.info_btn.setObjectName("info_btn")
        self.info_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.info_btn.clicked.connect(self.show_feature_info)
        header_layout.addWidget(self.info_btn)
        
        main_layout.addLayout(header_layout)

        # --- MIDDLE ROW (MAIN SPLIT) ---
        middle_layout = QHBoxLayout()
        middle_layout.setSpacing(12)

        # Left Side: Voicemail Rows List View
        self.list_widget = DraggableListWidget()
        self.list_widget.itemDoubleClicked.connect(self.prompt_rename)
        self.list_widget.itemSelectionChanged.connect(self.on_item_selected)
        middle_layout.addWidget(self.list_widget, stretch=7)

        # Right Side: Sidebar Configuration Layout
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setSpacing(8)
        
        self.always_on_top_cb = QCheckBox("Always on Top")
        self.always_on_top_cb.setFont(QFont("Segoe UI", 10))
        self.always_on_top_cb.stateChanged.connect(self.on_always_on_top_changed)
        sidebar_layout.addWidget(self.always_on_top_cb)
        
        self.hide_reviewed_cb = QCheckBox("Hide Reviewed")
        self.hide_reviewed_cb.setFont(QFont("Segoe UI", 10))
        self.hide_reviewed_cb.stateChanged.connect(self.on_hide_reviewed_changed)
        sidebar_layout.addWidget(self.hide_reviewed_cb)
        
        self.auto_close_folder_cb = QCheckBox("Auto-Close Folder")
        self.auto_close_folder_cb.setFont(QFont("Segoe UI", 10))
        self.auto_close_folder_cb.stateChanged.connect(self.on_auto_close_changed)
        sidebar_layout.addWidget(self.auto_close_folder_cb)
        
        # Compact Notes Widget tucked perfectly inside the sidebar framework
        sidebar_layout.addSpacing(6)
        phone_label = QLabel("Customer Phone:")
        phone_label.setFont(QFont("Segoe UI Semibold", 9))
        sidebar_layout.addWidget(phone_label)

        self.phone_number_input = QLineEdit()
        self.phone_number_input.setFixedWidth(160)
        self.phone_number_input.setFont(QFont("Segoe UI", 9))
        self.phone_number_input.setPlaceholderText("Enter phone number")
        self.phone_number_input.setMaxLength(20)
        self.phone_number_input.setValidator(QRegularExpressionValidator(QRegularExpression(r'[0-9\s\-]*')))
        self.phone_number_input.textChanged.connect(self.auto_save_current_notes)
        sidebar_layout.addWidget(self.phone_number_input)

        self.phone_copy_btn = QPushButton("Copy Phone Number")
        self.phone_copy_btn.setObjectName("copy_btn")
        self.phone_copy_btn.setFixedWidth(100)
        self.phone_copy_btn.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        self.phone_copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.phone_copy_btn.clicked.connect(self.copy_phone_number)
        sidebar_layout.addWidget(self.phone_copy_btn)

        sidebar_layout.addSpacing(6)
        notes_label = QLabel("Quick Notes:")
        notes_label.setFont(QFont("Segoe UI Semibold", 9))
        sidebar_layout.addWidget(notes_label)
        
        self.notes_box = QTextEdit()
        self.notes_box.setFixedWidth(160)
        self.notes_box.setPlaceholderText("Type message details...")
        self.notes_box.textChanged.connect(self.auto_save_current_notes)
        self.notes_box.setEnabled(False)
        sidebar_layout.addWidget(self.notes_box)
        
        # Audio Selection Dropdown Menu now aligned below the notes framework
        sidebar_layout.addSpacing(6)
        device_label = QLabel("Audio Output:")
        device_label.setFont(QFont("Segoe UI Semibold", 9))
        sidebar_layout.addWidget(device_label)
        
        self.device_combo = QComboBox()
        self.device_combo.setFixedWidth(160)
        self.device_combo.setFont(QFont("Segoe UI", 9))
        self.device_combo.currentIndexChanged.connect(self.change_audio_device)
        sidebar_layout.addWidget(self.device_combo)
        
        sidebar_layout.addStretch() 
        middle_layout.addLayout(sidebar_layout, stretch=3)
        main_layout.addLayout(middle_layout, stretch=10)

        # --- FULL-WIDTH WAVEFORM ROW + MEDIA CONTROLLER SUB-LAYOUT ---
        playback_container_layout = QVBoxLayout()
        playback_container_layout.setSpacing(6)

        time_layout = QHBoxLayout()
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setFont(QFont("Segoe UI Semibold", 10))
        self.time_label.setStyleSheet("color: #00E5FF;") 
        time_layout.addWidget(self.time_label)
        time_layout.addStretch()
        playback_container_layout.addLayout(time_layout)

        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(8)
        
        self.play_btn = QPushButton("▶")
        self.play_btn.setFixedSize(40, 50)
        self.play_btn.setFont(QFont("Segoe UI", 12))
        self.play_btn.setMinimumWidth(40)
        self.play_btn.setObjectName("play_btn")
        controls_layout.addWidget(self.play_btn)

        self.timeline_slider = WaveformProgressBar()
        self.timeline_slider.on_seek_requested = self.seek_audio_position
        controls_layout.addWidget(self.timeline_slider)
        
        playback_container_layout.addLayout(controls_layout)
        main_layout.addLayout(playback_container_layout)

        # --- BOTTOM ROW: FOOTER ACTIONS ---
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(10)

        self.rename_btn = QPushButton("Rename")
        self.unreview_btn = QPushButton("Mark Unreviewed") 
        self.open_btn = QPushButton("Open Folder")
        self.delete_btn = QPushButton("Delete")
        self.delete_all_btn = QPushButton("Delete All")
        self.delete_all_btn.setObjectName("delete_all_btn")
        
        for btn in [self.rename_btn, self.unreview_btn, self.open_btn, self.delete_btn, self.delete_all_btn]:
            btn.setFixedHeight(30)
            bottom_layout.addWidget(btn)

        main_layout.addLayout(bottom_layout)

        # Wire up connections
        self.play_btn.clicked.connect(self.play_audio)
        self.rename_btn.clicked.connect(self.prompt_rename)
        self.unreview_btn.clicked.connect(self.mark_as_unreviewed)
        self.open_btn.clicked.connect(self.open_tmetrics_folder)
        self.delete_btn.clicked.connect(self.delete_file)
        self.delete_all_btn.clicked.connect(self.delete_all_files)

        self.media_player.positionChanged.connect(self.update_slider_position)
        self.media_player.durationChanged.connect(self.update_slider_duration)
        self.media_player.playbackStateChanged.connect(self.handle_playback_state_change)

        self.explorer_check_timer = QTimer(self)
        self.explorer_check_timer.timeout.connect(self.close_explorer_at_location)

        QTimer.singleShot(50, self.bootstrap_application)

    def show_feature_info(self):
        dialog = InfoDialog(self)
        dialog.exec()

    def peek_always_on_top_config(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    lines = f.read().splitlines()
                    if len(lines) > 1:
                        return lines[1].strip() == "True"
            except: pass
        return False

    def bootstrap_application(self):
        self.reviewed_files = self.load_reviewed_cache()
        self.load_config()
        
        self.watcher = QFileSystemWatcher()
        if SOURCE_DIR.exists():
            self.watcher.addPath(str(SOURCE_DIR))
        self.watcher.directoryChanged.connect(self.handle_directory_changed_with_delay)

        self.devices_manager = QMediaDevices()
        self.populate_audio_devices()
        self.devices_manager.audioOutputsChanged.connect(self.populate_audio_devices)

        if WORKSPACE_DIR.exists():
            self.known_workspace_signatures = {str(f.absolute()) for f in WORKSPACE_DIR.glob("*.wav")}

        self.sync_from_source()

        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)
            self.on_item_selected()

        self.window_pin_timer = QTimer(self)
        self.window_pin_timer.timeout.connect(self.ensure_tmetrics_popup_on_top)
        self.window_pin_timer.start(1000)

    def handle_directory_changed_with_delay(self):
        QTimer.singleShot(300, self.sync_from_source)

    def get_wav_duration(self, file_path):
        try:
            with open(file_path, 'rb') as f:
                riff_header = f.read(44)
                if len(riff_header) < 44:
                    return 0
                byte_rate = struct.unpack('<I', riff_header[28:32])[0]
                data_size = struct.unpack('<I', riff_header[40:44])[0]
                if byte_rate > 0 and data_size > 0:
                    return int(data_size / byte_rate)
        except Exception as e:
            print(f"Error parsing metadata header: {e}")
        return 0

    def on_item_selected(self):
        item = self.list_widget.currentItem()
        if not item:

            self.notes_box.blockSignals(True)
            self.notes_box.clear()
            self.notes_box.setEnabled(False)
            self.notes_box.blockSignals(False)
            
            self.phone_number_input.blockSignals(True)
            self.phone_number_input.clear()
            self.phone_number_input.blockSignals(False)
            
            self.time_label.setText("00:00 / 00:00")
            self.timeline_slider.set_waveform(None)
            self.timeline_slider.set_range(0)
            self.unreview_btn.setEnabled(False)
            self.current_file_duration_ms = 0
            return

        if self.media_player.playbackState() != QMediaPlayer.PlaybackState.StoppedState:
            self.media_player.stop()
        self.media_player.setSource(QUrl())

        file_path_str = item.data(Qt.ItemDataRole.UserRole)
        
        self.notes_box.blockSignals(True)
        self.notes_box.clear()
        self.phone_number_input.blockSignals(True)
        self.phone_number_input.clear()
        
        if file_path_str:
            self.notes_box.setEnabled(True)
            note_file_path = Path(file_path_str).with_suffix(".txt")
            if note_file_path.exists():
                try:
                    with open(note_file_path, "r", encoding="utf-8") as nf:
                        file_content = nf.read()
                    lines = file_content.split('\n', 1)
                    if lines[0].startswith("PHONE:"):
                        phone = lines[0].replace("PHONE:", "").strip()
                        self.phone_number_input.setText(phone)
                        notes_content = lines[1] if len(lines) > 1 else ""
                        self.notes_box.setPlainText(notes_content)
                    else:
                        self.notes_box.setPlainText(file_content)
                except Exception as e:
                    print(f"Error loading text notes: {e}")
        else:
            self.notes_box.setEnabled(False)
        self.notes_box.blockSignals(False)
        self.phone_number_input.blockSignals(False)

        if file_path_str:
            filename = Path(file_path_str).name
            self.unreview_btn.setEnabled(filename in self.reviewed_files)

        if file_path_str and os.path.exists(file_path_str):
            duration_seconds = self.get_wav_duration(file_path_str)
            self.current_file_duration_ms = duration_seconds * 1000
            tot_min = duration_seconds // 60
            tot_sec = duration_seconds % 60
            
            self.time_label.setText(f"00:00 / {tot_min:02d}:{tot_sec:02d}")
            self.timeline_slider.set_range(self.current_file_duration_ms)
            self.timeline_slider.set_value(0)
            self.timeline_slider.set_waveform(file_path_str)

    def auto_save_current_notes(self):
        item = self.list_widget.currentItem()
        if not item: return
        
        file_path_str = item.data(Qt.ItemDataRole.UserRole)
        if file_path_str:
            note_file_path = Path(file_path_str).with_suffix(".txt")
            text_content = self.notes_box.toPlainText()
            phone_content = self.phone_number_input.text().strip()
            try:
                combined_content = ""
                if phone_content:
                    combined_content = f"PHONE:{phone_content}\n"
                combined_content += text_content
                
                if not combined_content.strip() or (not phone_content and not text_content.strip()):
                    if note_file_path.exists():
                        os.remove(note_file_path)
                else:
                    with open(note_file_path, "w", encoding="utf-8") as nf:
                        nf.write(combined_content)
            except Exception as e:
                print(f"Error auto-saving workspace note: {e}")


    def copy_phone_number(self):
        if not hasattr(self, 'phone_number_input'):
            return
        raw_number = self.phone_number_input.text().strip()
        digits = ''.join(ch for ch in raw_number if ch.isdigit())
        digit_count = len(digits)

        original_text = self.status_label.text()

        if digit_count == 10:
            copy_value = "91" + digits
        elif digit_count == 7:
            copy_value = "91585" + digits
        else:
            copy_value = digits

        if copy_value:
            QApplication.clipboard().setText(copy_value, QClipboard.Mode.Clipboard)
            self.status_label.setText(f"Copied phone number: {copy_value}")
            QTimer.singleShot(1500, lambda: self.status_label.setText(original_text))
        else:
            self.status_label.setText("Enter a valid phone number to copy.")
            QTimer.singleShot(1500, lambda: self.status_label.setText(original_text))

    def ensure_tmetrics_popup_on_top(self):
        """Monitors windows to bring both windows forward cleanly without stealing focus."""
        if not self.always_on_top_cb.isChecked():
            return

        # 1. Evaluate Manager Window alignment safely
        manager_hwnd = int(self.winId())
        if manager_hwnd:
            if ctypes.windll.user32.GetForegroundWindow() != manager_hwnd:
                ctypes.windll.user32.SetWindowPos(manager_hwnd, HWND_TOPMOST, 0, 0, 0, 0, TOPMOST_FLAGS)

        # 2. Evaluate T-Metrics context independently with multi-match criteria
        target_phrases = ["Customer Message Information", "Message Information", "Customer Message"]
        
        def scan_windows_callback(hwnd, extra):
            if not ctypes.windll.user32.IsWindowVisible(hwnd):
                return True

            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            window_title = ""
            if length > 0:
                buffer = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buffer, length + 1)
                window_title = buffer.value

            # Match criteria against fuzzy targets
            is_target_window = any(phrase.lower() in window_title.lower() for phrase in target_phrases)
            
            if is_target_window:
                if ctypes.windll.user32.IsIconic(hwnd):
                    ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)
                    if self.restore_sound:
                        try:
                            self.restore_sound.play()
                        except Exception:
                            pass
                    else:
                        try:
                            ctypes.windll.user32.MessageBeep(0x00000030)
                        except Exception:
                            pass
                
                # Push visual depth layer if it isn't currently assigned as the active layout pane
                foreground_hwnd = ctypes.windll.user32.GetForegroundWindow()
                if foreground_hwnd != hwnd:
                    ctypes.windll.user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, TOPMOST_FLAGS)
                return False  
            return True  
            
        ctypes.windll.user32.EnumWindows(EnumWindowsProc(scan_windows_callback), 0)

    def load_reviewed_cache(self):
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    return {line.strip() for line in f if line.strip()}
            except Exception as e:
                print(f"Error loading cache: {e}")
        return set()

    def save_reviewed_cache(self):
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                for filename in sorted(self.reviewed_files):
                    f.write(f"{filename}\n")
        except Exception as e:
            print(f"Error saving cache: {e}")

    def load_config(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    lines = f.read().splitlines()
                    hide_state = lines[0].strip() if len(lines) > 0 else "False"
                    self.hide_reviewed_cb.setChecked(hide_state == "True")
                    
                    top_state = lines[1].strip() if len(lines) > 1 else "False"
                    self.always_on_top_cb.blockSignals(True)
                    self.always_on_top_cb.setChecked(top_state == "True")
                    self.always_on_top_cb.blockSignals(False)

                    close_state = lines[2].strip() if len(lines) > 2 else "True"
                    self.auto_close_folder_cb.setChecked(close_state == "True")
            except Exception as e:
                print(f"Error loading config: {e}")

    def save_config(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                f.write(f"{self.hide_reviewed_cb.isChecked()}\n")
                f.write(f"{self.always_on_top_cb.isChecked()}\n")
                f.write(f"{self.auto_close_folder_cb.isChecked()}\n")
        except Exception as e:
            print(f"Error saving config: {e}")

    def on_hide_reviewed_changed(self):
        self.save_config()
        self.refresh_list()

    def on_always_on_top_changed(self):
        self.save_config()
        flags = self.windowFlags()
        if self.always_on_top_cb.isChecked():
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()

    def on_auto_close_changed(self):
        self.save_config()
        if self.auto_close_folder_cb.isChecked():
            self.explorer_check_timer.start(500)
        else:
            self.explorer_check_timer.stop()

    def close_explorer_at_location(self):
        if not win32com or not self.auto_close_folder_cb.isChecked():
            return
            
        try:
            shell = win32com.client.Dispatch("Shell.Application")
            target_path = os.path.normpath(str(SOURCE_DIR)).lower()
            
            for window in shell.Windows():
                if window.Name == "File Explorer" or "explorer.exe" in window.FullName.lower():
                    raw_url = str(window.LocationURL)
                    if raw_url.startswith("file:///"):
                        local_path = raw_url.replace("file:///", "").replace("/", "\\")
                        from urllib.parse import unquote
                        unquoted_path = os.path.normpath(unquote(local_path)).lower()
                        
                        if unquoted_path == target_path:
                            window.Quit() 
        except Exception as e:
            print(f"Real-time folder tracking layer error: {e}")

    def play_audio(self):
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
            return
        elif self.media_player.playbackState() == QMediaPlayer.PlaybackState.PausedState:
            self.media_player.play()
            return
            
        item = self.list_widget.currentItem()
        if item:
            file_path_str = item.data(Qt.ItemDataRole.UserRole)
            file_path = Path(file_path_str)
            filename = file_path.name

            if filename not in self.reviewed_files:
                self.reviewed_files.add(filename)
                self.save_reviewed_cache()
                self.refresh_list()
                self.unreview_btn.setEnabled(True)

            if self.media_player.source().isEmpty() or self.media_player.playbackState() == QMediaPlayer.PlaybackState.StoppedState:
                self.media_player.setSource(QUrl.fromLocalFile(file_path_str))
            
            self.media_player.play()

    def handle_playback_state_change(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_btn.setText("‖") 
        else:
            self.play_btn.setText("▶")

    def mark_as_unreviewed(self):
        item = self.list_widget.currentItem()
        if not item: return

        file_path_str = item.data(Qt.ItemDataRole.UserRole)
        if file_path_str:
            filename = Path(file_path_str).name
            if filename in self.reviewed_files:
                self.media_player.stop()
                self.media_player.setSource(QUrl())
                
                self.reviewed_files.discard(filename)
                self.save_reviewed_cache()
                self.refresh_list()
                self.unreview_btn.setEnabled(False)

    def update_slider_duration(self, duration_ms):
        if duration_ms > 0:
            self.current_file_duration_ms = duration_ms
        self.timeline_slider.set_range(self.current_file_duration_ms)
        self.update_time_label(self.media_player.position(), self.current_file_duration_ms)

    def update_slider_position(self, position_ms):
        self.timeline_slider.set_value(position_ms)
        self.update_time_label(position_ms, self.current_file_duration_ms)

    def seek_audio_position(self, position_ms):
        self.media_player.setPosition(position_ms)
        self.update_time_label(position_ms, self.current_file_duration_ms)

    def update_time_label(self, current_ms, total_ms):
        if total_ms > 0 and current_ms > total_ms:
            current_ms = total_ms
            
        cur_sec = current_ms // 1000
        cur_min = cur_sec // 60
        cur_sec = cur_sec % 60
        
        tot_sec = total_ms // 1000
        tot_min = tot_sec // 60
        tot_sec = tot_sec % 60
        self.time_label.setText(f"{cur_min:02d}:{cur_sec:02d} / {tot_min:02d}:{tot_sec:02d}")

    def populate_audio_devices(self):
        current_selection = self.device_combo.currentText()
        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        self.device_combo.addItem("System Default")
        self.available_devices = self.devices_manager.audioOutputs()
        for device in self.available_devices:
            self.device_combo.addItem(device.description())
        index = self.device_combo.findText(current_selection)
        if index >= 0:
            self.device_combo.setCurrentIndex(index)
        else:
            self.device_combo.setCurrentIndex(0)
        self.device_combo.blockSignals(False)
        self.change_audio_device(self.device_combo.currentIndex())

    def change_audio_device(self, index):
        if index == 0:
            from PyQt6.QtMultimedia import QAudioDevice
            self.audio_output.setDevice(QAudioDevice())
        elif hasattr(self, 'available_devices') and 0 < index <= len(self.available_devices):
            selected_device = self.available_devices[index - 1]
            self.audio_output.setDevice(selected_device)

    def open_tmetrics_folder(self):
        if SOURCE_DIR.exists(): 
            self.auto_close_folder_cb.setChecked(False)
            os.startfile(SOURCE_DIR)

    def sync_from_source(self):
        if not SOURCE_DIR.exists(): return
        valid_ext = ('.wav')
        existing_in_workspace = {f.name for f in WORKSPACE_DIR.iterdir()}

        for f in SOURCE_DIR.iterdir():
            if f.suffix.lower() in valid_ext and f.name not in existing_in_workspace:
                try:
                    shutil.copy2(f, WORKSPACE_DIR / f.name)
                except: pass
        self.refresh_list()

    def refresh_list(self):
        selected_path = None
        current_item = self.list_widget.currentItem()
        if current_item:
            selected_path = current_item.data(Qt.ItemDataRole.UserRole)
        
        was_empty = (self.list_widget.count() == 0)

        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        files = [f for f in WORKSPACE_DIR.glob("*") if f.suffix.lower() in ('.wav')]
        files.sort(key=lambda x: getattr(x.stat(), 'st_birthtime', x.stat().st_mtime), reverse=True)

        visible_count = 0
        target_row_to_select = -1
        
        newly_arrived_absolute_path = ""
        for f in files:
            f_abs_str = str(f.absolute())
            if f_abs_str not in self.known_workspace_signatures:
                newly_arrived_absolute_path = f_abs_str
                break

        self.known_workspace_signatures = {str(f.absolute()) for f in files}

        for f in files:
            is_reviewed = f.name in self.reviewed_files
            if is_reviewed and self.hide_reviewed_cb.isChecked():
                continue

            c_time = getattr(f.stat(), 'st_birthtime', f.stat().st_mtime) 
            date_str = time.strftime("%m/%d/%y %I:%M %p", time.localtime(c_time))
            display_text = f"[Reviewed] {f.name}   |   {date_str}" if is_reviewed else f"{f.name}   |   {date_str}"
                
            item = QListWidgetItem(display_text)
            item.setSizeHint(QSize(0,38))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable) 
            item.setData(Qt.ItemDataRole.UserRole, str(f.absolute()))
            if is_reviewed:
                item.setForeground(QColor("#546E7A")) 
                
            self.list_widget.addItem(item)
            
            if selected_path and str(f.absolute()) == selected_path:
                target_row_to_select = visible_count
            elif newly_arrived_absolute_path and str(f.absolute()) == newly_arrived_absolute_path:
                if not selected_path:
                    target_row_to_select = visible_count
                    
            visible_count += 1
            
        self.status_label.setText(f"Report issue to Dustin  |  Voicemails Displayed: {visible_count}/{len(files)}")
        self.list_widget.blockSignals(False)

        if was_empty and visible_count > 0:
            self.list_widget.setCurrentRow(0)
            self.on_item_selected()
        elif newly_arrived_absolute_path:
            found_row = -1
            for row in range(self.list_widget.count()):
                row_item = self.list_widget.item(row)
                if row_item and row_item.data(Qt.ItemDataRole.UserRole) == newly_arrived_absolute_path:
                    found_row = row
                    break
            if found_row >= 0:
                self.list_widget.setCurrentRow(found_row)
                self.on_item_selected()
        elif target_row_to_select >= 0:
            self.list_widget.setCurrentRow(target_row_to_select)
        else:
            if visible_count == 0:
                self.unreview_btn.setEnabled(False)

    def prompt_rename(self):
        item = self.list_widget.currentItem()
        if not item: return

        self.media_player.stop()
        self.media_player.setSource(QUrl())
        ws_path = Path(item.data(Qt.ItemDataRole.UserRole))
        current_filename = ws_path.stem

        dialog = QInputDialog(self)
        dialog.setWindowTitle("Rename Voicemail")
        dialog.setLabelText("Enter new name for voicemail:")
        dialog.setTextValue(current_filename)
        dialog.setTextEchoMode(QLineEdit.EchoMode.Normal)
        
        dialog.resize(450, 180)
        dialog.setStyleSheet(DARK_THEME_STYLE)
        
        if dialog.layout():
            dialog.layout().setContentsMargins(20, 20, 20, 20)
            dialog.layout().setSpacing(12)
        
        QTimer.singleShot(0, dialog.findChild(QLineEdit).selectAll)

        if dialog.exec() == QInputDialog.DialogCode.Accepted:
            user_input = dialog.textValue().strip()
            if not user_input: return
            
            suffix = " VOICEMAIL" if not user_input.endswith(" VOICEMAIL") else ""
            new_name = f"{user_input}{suffix}{ws_path.suffix}"
            new_ws_path = ws_path.parent / new_name

            if ws_path != new_ws_path:
                if ws_path.name in self.reviewed_files:
                    self.reviewed_files.remove(ws_path.name)
                    self.reviewed_files.add(new_name)
                    self.save_reviewed_cache()

                old_note_path = ws_path.with_suffix(".txt")
                if old_note_path.exists():
                    try: os.rename(old_note_path, new_ws_path.with_suffix(".txt"))
                    except OSError: pass

                original_file_path = SOURCE_DIR / ws_path.name
                if original_file_path.exists():
                    try: os.rename(original_file_path, SOURCE_DIR / new_name)
                    except OSError: pass
                try:
                    os.rename(ws_path, new_ws_path)
                    self.refresh_list()
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Rename failed: {e}")
                    self.refresh_list()

    def delete_file(self):
        self.media_player.stop()
        self.media_player.setSource(QUrl())
        item = self.list_widget.currentItem()
        if not item: return
        ws_path = Path(item.data(Qt.ItemDataRole.UserRole))
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Delete")
        msg_box.setText(f"Delete {ws_path.name}?")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setStyleSheet(DARK_THEME_STYLE)
        if msg_box.layout():
            msg_box.layout().setContentsMargins(20, 20, 20, 20)
        
        if msg_box.exec() == QMessageBox.StandardButton.Yes:
            if ws_path.name in self.reviewed_files:
                self.reviewed_files.discard(ws_path.name)
                self.save_reviewed_cache()

            note_path = ws_path.with_suffix(".txt")
            if note_path.exists():
                try: os.remove(note_path)
                except OSError: pass

            original_file_path = SOURCE_DIR / ws_path.name
            if original_file_path.exists():
                try: os.remove(original_file_path)
                except OSError: pass
            try:
                os.remove(ws_path)
                self.refresh_list()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Delete failed: {e}")

    def delete_all_files(self):
        self.media_player.stop()
        self.media_player.setSource(QUrl())
        file_count = self.list_widget.count()
        if file_count == 0:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Delete All")
            msg_box.setText("No voicemails found to delete.")
            msg_box.setStyleSheet(DARK_THEME_STYLE)
            if msg_box.layout():
                msg_box.layout().setContentsMargins(20, 20, 20, 20)
            msg_box.exec()
            return

        confirm_box = QMessageBox(self)
        confirm_box.setWindowTitle("Confirm Delete All")
        confirm_box.setText(f"Are you absolutely sure you want to permanently delete ALL {file_count} voicemails?\n\nThis will wipe them from your Workspace (including text notes) and T-Metrics folders.")
        confirm_box.setIcon(QMessageBox.Icon.Warning)
        confirm_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        confirm_box.setDefaultButton(QMessageBox.StandardButton.No)
        confirm_box.setStyleSheet(DARK_THEME_STYLE)
        if confirm_box.layout():
            confirm_box.layout().setContentsMargins(20, 20, 20, 20)
        
        if confirm_box.exec() == QMessageBox.StandardButton.Yes:
            self.reviewed_files.clear()
            self.save_reviewed_cache()
            if WORKSPACE_DIR.exists():
                for f in WORKSPACE_DIR.glob("*.wav"):
                    try: os.remove(f)
                    except: pass
                for f in WORKSPACE_DIR.glob("*.txt"):
                    try: os.remove(f)
                    except: pass
            if SOURCE_DIR.exists():
                for f in SOURCE_DIR.glob("*.wav"):
                    try: os.remove(f)
                    except: pass
            self.refresh_list()
            
            success_box = QMessageBox(self)
            success_box.setWindowTitle("Success")
            success_box.setText("All voicemails and associated notes have been successfully deleted.")
            success_box.setStyleSheet(DARK_THEME_STYLE)
            if success_box.layout():
                success_box.layout().setContentsMargins(20, 20, 20, 20)
            success_box.exec()


if __name__ == "__main__":
    try:
        myappid = 'DustinMeyer.tmetrics.workspace.v2'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception as e:
        print(f"Could not set AppUserModelID: {e}")

    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_THEME_STYLE)
    app.setStyle("Fusion")
    
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
        
    resolved_icon_path = os.path.join(base_path, ICON_PATH)

    if os.path.exists(resolved_icon_path):
        app.setWindowIcon(QIcon(resolved_icon_path))
    else:
        if getattr(sys, 'frozen', False):
            app.setWindowIcon(QIcon(os.path.abspath(sys.executable)))

    window = VoicemailManager()
    
    if os.path.exists(resolved_icon_path):
        window.setWindowIcon(QIcon(resolved_icon_path))
    elif getattr(sys, 'frozen', False):
        window.setWindowIcon(QIcon(os.path.abspath(sys.executable)))

    window.show()
    sys.exit(app.exec())