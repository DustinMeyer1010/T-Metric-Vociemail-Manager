import os
import shutil
import sys
import ctypes
import struct
import time
import json
import webbrowser
from pathlib import Path
from urllib.parse import unquote

from PyQt6.QtWidgets import (QDialog, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QCheckBox, QLineEdit, QComboBox, QTextEdit, QPushButton,
                             QMessageBox, QInputDialog, QApplication, QListWidgetItem, QListWidget, QStackedWidget)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaDevices, QAudioDevice
from PyQt6.QtCore import Qt, QUrl, QFileSystemWatcher, QTimer, QSize, QRegularExpression, QRectF
from PyQt6.QtGui import (QIcon, QColor, QFont, QClipboard, QRegularExpressionValidator,
                         QPixmap, QPainter, QPen)

from constants import (BASE_PATH, SOURCE_DIR, ICON_PATH, WORKSPACE_DIR,
                       CACHE_FILE, CONFIG_FILE, CUSTOM_RESTORE_SOUND,
                       SOUNDS_DIR, DEFAULT_SOUNDS_DIR, TRASH_DIR, TMETRIC_RINGTONES_DIR, HWND_TOPMOST, TOPMOST_FLAGS, EnumWindowsProc,
                       CARTOON_THEME_STYLE, DARK_THEME_STYLE, LIGHT_THEME_STYLE, SW_RESTORE,
                       DWMWA_USE_IMMERSIVE_DARK_MODE)
from ui_components import InfoDialog, WaveformProgressBar, DraggableListWidget, SettingsDialog, play_icon, pause_icon

try:
    import win32com.client
except ImportError:
    win32com = None


DEFAULT_SOUND_LABEL = "Default Sound"
TRASH_RETENTION_DAYS = 30


class VoicemailManager(QMainWindow):
    def __init__(self, app):
        super().__init__()
        
        self.app = app
        self.current_theme = 'dark'
        self.current_style = DARK_THEME_STYLE
        self.setWindowTitle("T-Metric Voicemail Manager")
        self.resize(500, 500)

        if os.path.exists(ICON_PATH):
            self.setWindowIcon(QIcon(ICON_PATH))

        initial_topmost = self.peek_always_on_top_config()
        if initial_topmost:
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.notification_player = QMediaPlayer()
        self.notification_audio_output = QAudioOutput()
        self.notification_audio_output.setVolume(0.8)
        self.notification_player.setAudioOutput(self.notification_audio_output)
        self.selected_sound_file = None
        self.available_sounds = []
        self.audio_device_name = "System Default"
        self.devices_manager = QMediaDevices()
        self.devices_manager.audioOutputsChanged.connect(self.apply_saved_audio_device)
        self.settings_view = None
        self.loading_config = False
        self.tmetrics_popup_detected = False

        self.reviewed_files = set()
        self.current_file_duration_ms = 0
        self.known_workspace_signatures = set()
        self.include_notes_in_drag_drop = False
        self.ask_before_delete = True

        self.view_stack = QStackedWidget()
        self.setCentralWidget(self.view_stack)

        self.main_view = QWidget()
        self.settings_view = SettingsDialog(self.current_theme, self)
        self.settings_view.close_requested.connect(self.show_main_view)

        self.view_stack.addWidget(self.main_view)
        self.view_stack.addWidget(self.settings_view)
        self.initialize_settings_view()

        main_layout = QVBoxLayout(self.main_view)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        header_layout = QHBoxLayout()
        self.status_label = QLabel("Initializing application...")
        self.status_label.setFont(QFont("Segoe UI Semibold", 10))
        header_layout.addWidget(self.status_label)
        header_layout.addStretch()

        self.settings_btn = QPushButton()
        self.settings_btn.setObjectName("settings_btn")
        self.settings_btn.setIconSize(QSize(18, 18))
        self.update_settings_icon()
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.clicked.connect(self.show_settings)
        header_layout.addWidget(self.settings_btn)

        main_layout.addLayout(header_layout)

        middle_layout = QHBoxLayout()
        middle_layout.setSpacing(12)

        self.list_widget = DraggableListWidget()
        self.list_widget.include_note_in_drag = self.include_notes_in_drag_drop
        self.list_widget.itemDoubleClicked.connect(self.prompt_rename)
        self.list_widget.itemSelectionChanged.connect(self.on_item_selected)
        middle_layout.addWidget(self.list_widget, stretch=7)

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

        sidebar_layout.addStretch()
        middle_layout.addLayout(sidebar_layout, stretch=3)
        main_layout.addLayout(middle_layout, stretch=10)

        playback_container_layout = QVBoxLayout()
        playback_container_layout.setSpacing(6)

        time_layout = QHBoxLayout()
        self.time_label = QLabel("0:00 / 0:00")
        self.time_label.setFont(QFont("Segoe UI Semibold", 10))
        self.time_label.setStyleSheet("color: #00E5FF;")
        time_layout.addWidget(self.time_label)
        time_layout.addStretch()
        playback_container_layout.addLayout(time_layout)

        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(8)

        self.play_btn = QPushButton()
        self.play_btn.setFixedSize(32, 55)
        self.play_btn.setIconSize(QSize(16, 16))
        self.play_btn.setObjectName("play_btn")
        self.update_playback_button_icon()
        controls_layout.addWidget(self.play_btn)

        self.timeline_slider = WaveformProgressBar(self.current_theme)
        self.timeline_slider.on_seek_requested = self.seek_audio_position
        controls_layout.addWidget(self.timeline_slider)

        playback_container_layout.addLayout(controls_layout)
        main_layout.addLayout(playback_container_layout)

        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(10)

        self.rename_btn = QPushButton("Rename")
        self.unreview_btn = QPushButton("Mark Unreviewed")
        self.delete_btn = QPushButton("Delete")
        self.delete_all_btn = QPushButton("Delete All")
        self.delete_all_btn.setObjectName("delete_all_btn")

        for btn in [self.rename_btn, self.unreview_btn, self.delete_btn, self.delete_all_btn]:
            btn.setFixedHeight(30)
            bottom_layout.addWidget(btn)

        main_layout.addLayout(bottom_layout)

        self.play_btn.clicked.connect(self.play_audio)
        self.rename_btn.clicked.connect(self.prompt_rename)
        self.unreview_btn.clicked.connect(self.mark_as_unreviewed)
        self.delete_btn.clicked.connect(self.delete_file)
        self.delete_all_btn.clicked.connect(self.delete_all_files)

        self.media_player.positionChanged.connect(self.update_slider_position)
        self.media_player.durationChanged.connect(self.update_slider_duration)
        self.media_player.playbackStateChanged.connect(self.handle_playback_state_change)

        self.explorer_check_timer = QTimer(self)
        self.explorer_check_timer.timeout.connect(self.close_explorer_at_location)

        QTimer.singleShot(50, self.bootstrap_application)

    def build_settings_icon(self):
        if self.current_theme in ('dark', 'light'):
            icon_name = "dark-settings.png" if self.current_theme == 'dark' else "light-settings.png"
            icon_path = Path(BASE_PATH) / "assets" / icon_name
            if icon_path.exists():
                return QIcon(str(icon_path))

        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.current_theme == 'cartoon':
            color = QColor("#3A86FF")
        else:
            color = QColor("#00E5FF" if self.current_theme == 'dark' else "#2563EB")
        painter.setPen(QPen(color, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))

        painter.drawEllipse(QRectF(8, 8, 8, 8))
        for x1, y1, x2, y2 in [
            (12, 2.5, 12, 5.5),
            (12, 18.5, 12, 21.5),
            (2.5, 12, 5.5, 12),
            (18.5, 12, 21.5, 12),
            (5.2, 5.2, 7.3, 7.3),
            (16.7, 16.7, 18.8, 18.8),
            (18.8, 5.2, 16.7, 7.3),
            (7.3, 16.7, 5.2, 18.8),
        ]:
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        painter.end()
        return QIcon(pixmap)

    def update_settings_icon(self):
        self.settings_btn.setIcon(self.build_settings_icon())

    def apply_theme(self, theme, save=True):
        if theme not in ('dark', 'light', 'cartoon'):
            theme = 'dark'

        if theme == self.current_theme:
            return

        if theme == 'light':
            self.app.setStyleSheet(LIGHT_THEME_STYLE)
            self.current_style = LIGHT_THEME_STYLE
            self.current_theme = 'light'
            self.timeline_slider.set_theme('light')
            self.update_settings_icon()
            self.update_playback_button_icon()
            self.set_title_bar_theme(dark_mode=False)
        elif theme == 'cartoon':
            self.app.setStyleSheet(CARTOON_THEME_STYLE)
            self.current_style = CARTOON_THEME_STYLE
            self.current_theme = 'cartoon'
            self.timeline_slider.set_theme('cartoon')
            self.update_settings_icon()
            self.update_playback_button_icon()
            self.set_title_bar_theme(dark_mode=False)
        else:
            self.app.setStyleSheet(DARK_THEME_STYLE)
            self.current_style = DARK_THEME_STYLE
            self.current_theme = 'dark'
            self.timeline_slider.set_theme('dark')
            self.update_settings_icon()
            self.update_playback_button_icon()
            self.set_title_bar_theme(dark_mode=True)

        if save:
            self.save_config()

        if self.settings_view is not None:
            self.settings_view.apply_theme(self.current_theme)

    def toggle_theme(self):
        next_theme = 'light' if self.current_theme == 'dark' else 'cartoon' if self.current_theme == 'light' else 'dark'
        self.apply_theme(next_theme)

    def show_feature_info(self):
        dialog = InfoDialog(self.current_theme, self)
        dialog.exec()

    def initialize_settings_view(self):
        self.settings_view.open_sounds_folder_btn.clicked.connect(self.open_sounds_folder)
        self.settings_view.recover_deleted_btn.clicked.connect(self.recover_deleted_voicemail)
        self.settings_view.open_tmetrics_folder_btn.clicked.connect(self.open_tmetrics_folder)
        self.settings_view.open_tmetrics_ringtones_btn.clicked.connect(self.open_tmetrics_ringtones_folder)
        self.settings_view.github_btn.clicked.connect(self.open_project_link)
        self.settings_view.test_sound_btn.clicked.connect(self.play_notification_sound)
        self.settings_view.info_btn.clicked.connect(self.show_feature_info)
        self.settings_view.sound_combo.currentTextChanged.connect(self.on_settings_sound_changed)
        self.settings_view.include_notes_drag_cb.stateChanged.connect(self.on_include_notes_drag_changed)
        self.settings_view.ask_before_delete_cb.stateChanged.connect(self.on_ask_before_delete_changed)

    def populate_settings_view(self):
        # Populate audio devices
        dialog = self.settings_view
        available_devices = self.devices_manager.audioOutputs()

        try:
            dialog.device_combo.currentIndexChanged.disconnect()
        except Exception:
            pass
        try:
            dialog.theme_combo.currentTextChanged.disconnect()
        except Exception:
            pass

        dialog.device_combo.blockSignals(True)
        dialog.theme_combo.blockSignals(True)
        dialog.include_notes_drag_cb.blockSignals(True)
        dialog.ask_before_delete_cb.blockSignals(True)

        dialog.apply_theme(self.current_theme)
        dialog.device_combo.clear()
        dialog.device_combo.addItem("System Default")
        for device in available_devices:
            dialog.device_combo.addItem(device.description())

        current_device_index = dialog.device_combo.findText(self.audio_device_name)
        if current_device_index < 0:
            current_device_index = 0
        dialog.device_combo.setCurrentIndex(current_device_index)
        dialog.theme_combo.setCurrentText(self.current_theme.title())
        dialog.include_notes_drag_cb.setChecked(self.include_notes_in_drag_drop)
        dialog.ask_before_delete_cb.setChecked(self.ask_before_delete)

        self.refresh_sounds_in_dialog(dialog, getattr(self, 'sound_combo_current_text', DEFAULT_SOUND_LABEL))

        dialog.device_combo.blockSignals(False)
        dialog.theme_combo.blockSignals(False)
        dialog.include_notes_drag_cb.blockSignals(False)
        dialog.ask_before_delete_cb.blockSignals(False)

        dialog.device_combo.currentIndexChanged.connect(
            lambda index, devices=available_devices: self.on_settings_audio_device_changed(index, devices)
        )
        dialog.theme_combo.currentTextChanged.connect(
            lambda theme, dialog=dialog: self.on_settings_theme_changed(theme, dialog)
        )

    def show_settings(self):
        self.populate_settings_view()
        self.view_stack.setCurrentWidget(self.settings_view)

    def show_main_view(self):
        self.view_stack.setCurrentWidget(self.main_view)

    def peek_always_on_top_config(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    lines = f.read().splitlines()
                    if len(lines) > 1:
                        return lines[1].strip() == "True"
            except Exception:
                pass
        return False

    def set_title_bar_theme(self, dark_mode=True):
        """Set the Windows title bar theme (dark/light)"""
        try:
            # Get the window handle
            hwnd = int(self.winId())
            print(f"Setting title bar theme - hwnd: {hwnd}, dark_mode: {dark_mode}, DWMWA_USE_IMMERSIVE_DARK_MODE: {DWMWA_USE_IMMERSIVE_DARK_MODE}")
            
            # Set the DWM attribute for immersive dark mode
            # 0 = light title bar, 1 = dark title bar
            value = ctypes.c_int(1 if dark_mode else 0)
            result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_USE_IMMERSIVE_DARK_MODE,
                ctypes.byref(value),
                ctypes.sizeof(value)
            )
            print(f"DwmSetWindowAttribute result: {result}")
        except Exception as e:
            print(f"Error setting title bar theme: {e}")
            # Silently fail if DWM is not available or other error
            pass

    def bootstrap_application(self):
        self.reviewed_files = self.load_reviewed_cache()
        self.load_config()
        self.on_auto_close_changed()
        self.copy_default_sounds()
        self.purge_expired_deleted_voicemails()

        self.watcher = QFileSystemWatcher()
        if SOURCE_DIR.exists():
            self.watcher.addPath(str(SOURCE_DIR))
        self.watcher.directoryChanged.connect(self.handle_directory_changed_with_delay)

        self.sounds_watcher = QFileSystemWatcher()
        if SOUNDS_DIR.exists():
            self.sounds_watcher.addPath(str(SOUNDS_DIR))
        self.sounds_watcher.directoryChanged.connect(self.handle_sounds_directory_changed)

        if WORKSPACE_DIR.exists():
            self.known_workspace_signatures = {str(f.absolute()) for f in WORKSPACE_DIR.glob("*.wav")}

        self.sync_from_source()

        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)
            self.on_item_selected()

        self.window_pin_timer = QTimer(self)
        self.window_pin_timer.timeout.connect(self.ensure_tmetrics_popup_on_top)
        self.window_pin_timer.start(500)

        # Set title bar theme based on loaded config
        self.set_title_bar_theme(dark_mode=(self.current_theme == 'dark'))

    def copy_default_sounds(self):
        """Copy default sounds to the AppData sounds directory if they don't already exist"""
        # Determine the source directory for default sounds
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            base_path = sys._MEIPASS
        else:
            # Running as script
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        default_sounds_path = os.path.join(base_path, 'default_sounds')
        
        if not os.path.exists(default_sounds_path):
            return
        
        for sound_file in os.listdir(default_sounds_path):
            if sound_file.endswith(('.wav', '.mp3', '.flac', '.ogg')):
                source_file = os.path.join(default_sounds_path, sound_file)
                target_file = SOUNDS_DIR / sound_file
                if not target_file.exists():
                    try:
                        shutil.copy2(source_file, target_file)
                    except Exception as e:
                        print(f"Error copying default sound {sound_file}: {e}")

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

            self.reset_playback_panel()
            self.unreview_btn.setEnabled(False)
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
                    phone, notes_content = self.parse_note_file_content(file_content)
                    self.phone_number_input.setText(phone)
                    self.notes_box.setPlainText(notes_content)
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

            self.time_label.setText(f"0:00 / {tot_min}:{tot_sec:02d}")
            self.timeline_slider.set_range(self.current_file_duration_ms)
            self.timeline_slider.set_value(0)
            self.timeline_slider.set_waveform(file_path_str)

    def auto_save_current_notes(self):
        item = self.list_widget.currentItem()
        if not item:
            return

        file_path_str = item.data(Qt.ItemDataRole.UserRole)
        if file_path_str:
            note_file_path = Path(file_path_str).with_suffix(".txt")
            text_content = self.notes_box.toPlainText()
            phone_content = self.phone_number_input.text().strip()
            try:
                combined_content = self.build_note_file_content(phone_content, text_content)

                if not combined_content:
                    if note_file_path.exists():
                        os.remove(note_file_path)
                else:
                    with open(note_file_path, "w", encoding="utf-8") as nf:
                        nf.write(combined_content)
            except Exception as e:
                print(f"Error auto-saving workspace note: {e}")

    def copy_phone_number(self):
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
        else:
            self.status_label.setText("Enter a valid phone number to copy.")

        QTimer.singleShot(1500, lambda: self.status_label.setText(original_text))

    def enforce_popup_window_state(self, hwnd):
        if ctypes.windll.user32.IsIconic(hwnd):
            ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)

        ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)
        ctypes.windll.user32.BringWindowToTop(hwnd)
        ctypes.windll.user32.SetForegroundWindow(hwnd)
        ctypes.windll.user32.SetWindowPos(
            hwnd,
            HWND_TOPMOST,
            0,
            0,
            0,
            0,
            TOPMOST_FLAGS
        )

    def ensure_tmetrics_popup_on_top(self):
        """
        Detect the T-Metrics Customer Message Information popup.

        Behavior:
        - Keeps the Customer Message Information window always on top.
        - Restores it if minimized.
        - Restores/unminimizes this Voicemail Manager app on first detection.
        - Plays the selected notification sound once when the popup is first found.
        - Does not repeat the sound while the same popup remains open.
        - Resets after the popup closes so the sound plays again next time.
        """
        try:
            manager_hwnd = int(self.winId())

            # Keep this Voicemail Manager window topmost as well.
            # This matches your existing behavior of keeping the manager visible.
            if manager_hwnd:
                ctypes.windll.user32.SetWindowPos(
                    manager_hwnd,
                    HWND_TOPMOST,
                    0,
                    0,
                    0,
                    0,
                    TOPMOST_FLAGS
                )

            target_phrases = [
                "Customer Message Information",
                "Message Information",
                "Customer Message"
            ]

            popup_found = {"value": False}

            def scan_windows_callback(hwnd, extra):
                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                window_title = ""

                if length > 0:
                    buffer = ctypes.create_unicode_buffer(length + 1)
                    ctypes.windll.user32.GetWindowTextW(hwnd, buffer, length + 1)
                    window_title = buffer.value

                is_target_window = any(
                    phrase.lower() in window_title.lower()
                    for phrase in target_phrases
                )

                if is_target_window:
                    popup_found["value"] = True
                    self.enforce_popup_window_state(hwnd)

                    # Stop scanning once we find the target popup
                    return False

                return True

            ctypes.windll.user32.EnumWindows(
                EnumWindowsProc(scan_windows_callback),
                0
            )

            # First time the popup is detected
            if popup_found["value"] and not self.tmetrics_popup_detected:
                self.tmetrics_popup_detected = True

                # Restore/unminimize the Voicemail Manager app
                self.restore_manager_window()

                # Play selected notification sound once
                self.play_notification_sound()

            # Reset after the popup is closed/no longer found
            elif not popup_found["value"] and self.tmetrics_popup_detected:
                self.tmetrics_popup_detected = False

        except Exception as e:
            print(f"Error ensuring T-Metrics popup on top: {e}")

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
                self.loading_config = True
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    lines = f.read().splitlines()
                    hide_state = lines[0].strip() if len(lines) > 0 else "False"
                    self.hide_reviewed_cb.blockSignals(True)
                    self.hide_reviewed_cb.setChecked(hide_state == "True")
                    self.hide_reviewed_cb.blockSignals(False)

                    top_state = lines[1].strip() if len(lines) > 1 else "False"
                    self.always_on_top_cb.blockSignals(True)
                    self.always_on_top_cb.setChecked(top_state == "True")
                    self.always_on_top_cb.blockSignals(False)

                    close_state = lines[2].strip() if len(lines) > 2 else "True"
                    self.auto_close_folder_cb.blockSignals(True)
                    self.auto_close_folder_cb.setChecked(close_state == "True")
                    self.auto_close_folder_cb.blockSignals(False)

                    theme_state = (lines[3].strip() if len(lines) > 3 else "dark").lower()
                    self.apply_theme(theme_state, save=False)

                    selected_sound = lines[4].strip() if len(lines) > 4 else DEFAULT_SOUND_LABEL
                    if selected_sound == "None":
                        selected_sound = DEFAULT_SOUND_LABEL
                    self.sound_combo_current_text = selected_sound
                    self.load_selected_sound()

                    self.audio_device_name = lines[5].strip() if len(lines) > 5 else "System Default"
                    self.apply_saved_audio_device()

                    self.include_notes_in_drag_drop = lines[6].strip() == "True" if len(lines) > 6 else False
                    self.list_widget.include_note_in_drag = self.include_notes_in_drag_drop
                    self.ask_before_delete = lines[7].strip() != "False" if len(lines) > 7 else True
            except Exception as e:
                print(f"Error loading config: {e}")
            finally:
                self.loading_config = False

    def save_config(self):
        if self.loading_config:
            return

        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                f.write(f"{self.hide_reviewed_cb.isChecked()}\n")
                f.write(f"{self.always_on_top_cb.isChecked()}\n")
                f.write(f"{self.auto_close_folder_cb.isChecked()}\n")
                f.write(f"{self.current_theme}\n")
                f.write(f"{getattr(self, 'sound_combo_current_text', DEFAULT_SOUND_LABEL)}\n")
                f.write(f"{getattr(self, 'audio_device_name', 'System Default')}\n")
                f.write(f"{getattr(self, 'include_notes_in_drag_drop', False)}\n")
                f.write(f"{getattr(self, 'ask_before_delete', True)}\n")
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

    def on_include_notes_drag_changed(self, state):
        self.include_notes_in_drag_drop = bool(state)
        self.list_widget.include_note_in_drag = self.include_notes_in_drag_drop
        self.save_config()

    def on_ask_before_delete_changed(self, state):
        self.ask_before_delete = bool(state)
        self.save_config()

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

    def update_playback_button_icon(self):
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.play_btn.setIcon(pause_icon(self.current_theme))
        else:
            self.play_btn.setIcon(play_icon(self.current_theme))

    def handle_playback_state_change(self, state):
        self.update_playback_button_icon()

    def mark_as_unreviewed(self):
        item = self.list_widget.currentItem()
        if not item:
            return

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
        self.time_label.setText(f"{cur_min}:{cur_sec:02d} / {tot_min}:{tot_sec:02d}")

    def reset_playback_panel(self):
        self.media_player.stop()
        self.media_player.setSource(QUrl())
        self.time_label.setText("0:00 / 0:00")
        self.timeline_slider.set_waveform(None)
        self.timeline_slider.set_range(0)
        self.timeline_slider.set_value(0)
        self.current_file_duration_ms = 0

    def parse_note_file_content(self, file_content):
        normalized = file_content.replace("\r\n", "\n").strip()
        if not normalized:
            return "", ""

        if normalized.startswith("PHONE:"):
            lines = normalized.split("\n", 1)
            phone = lines[0].replace("PHONE:", "", 1).strip()
            notes = lines[1].strip() if len(lines) > 1 else ""
            return phone, notes

        phone = ""
        notes = normalized

        lines = normalized.split("\n")
        if lines and lines[0].startswith("Phone Number:"):
            phone = lines[0].replace("Phone Number:", "", 1).strip()
            remaining_lines = lines[1:]
            if remaining_lines and not remaining_lines[0].strip():
                remaining_lines = remaining_lines[1:]
            if remaining_lines and remaining_lines[0].strip() == "Notes:":
                remaining_lines = remaining_lines[1:]
                if remaining_lines and not remaining_lines[0].strip():
                    remaining_lines = remaining_lines[1:]
            notes = "\n".join(remaining_lines).strip()

        return phone, notes

    def build_note_file_content(self, phone_content, text_content):
        phone = phone_content.strip()
        notes = text_content.strip()
        sections = []

        if phone:
            sections.append(f"Phone Number: {phone}")
        if notes:
            if phone:
                sections.append(f"Notes:\n{notes}")
            else:
                sections.append(notes)

        return "\n\n".join(sections).strip()

    def change_audio_device(self, index):
        if index == 0:
            self.audio_output.setDevice(QAudioDevice())
            self.notification_audio_output.setDevice(QAudioDevice())
        elif hasattr(self, 'available_devices') and 0 < index <= len(self.available_devices):
            selected_device = self.available_devices[index - 1]
            self.audio_output.setDevice(selected_device)
            self.notification_audio_output.setDevice(selected_device)

    def apply_audio_device(self, device_name, available_devices=None):
        self.audio_device_name = device_name or "System Default"
        devices = available_devices if available_devices is not None else self.devices_manager.audioOutputs()

        if self.audio_device_name == "System Default":
            self.audio_output.setDevice(QAudioDevice())
            self.notification_audio_output.setDevice(QAudioDevice())
            return

        for device in devices:
            if device.description() == self.audio_device_name:
                self.audio_output.setDevice(device)
                self.notification_audio_output.setDevice(device)
                return

        self.audio_output.setDevice(QAudioDevice())
        self.notification_audio_output.setDevice(QAudioDevice())

    def apply_saved_audio_device(self):
        self.apply_audio_device(getattr(self, 'audio_device_name', "System Default"))

    def on_settings_audio_device_changed(self, index, available_devices):
        if index == 0:
            self.apply_audio_device("System Default", available_devices)
        elif index <= len(available_devices):
            self.apply_audio_device(available_devices[index - 1].description(), available_devices)
        self.save_config()

    def on_settings_sound_changed(self, selected_sound):
        self.sound_combo_current_text = selected_sound or DEFAULT_SOUND_LABEL
        self.load_selected_sound()
        self.save_config()

    def on_settings_theme_changed(self, theme, dialog):
        selected_theme = theme.lower()
        self.apply_theme(selected_theme)
        dialog.apply_theme(selected_theme)

    def get_available_sound_files(self):
        sound_files = []
        if SOUNDS_DIR.exists():
            for ext in ['*.wav', '*.mp3', '*.flac', '*.ogg']:
                sound_files.extend(SOUNDS_DIR.glob(ext))
        return sorted([f for f in sound_files if f.is_file()], key=lambda f: f.stem.lower())

    def refresh_sounds_in_dialog(self, dialog, preferred_sound=None):
        """Refresh sounds list in the settings dialog."""
        current_sound = preferred_sound or dialog.sound_combo.currentText() or DEFAULT_SOUND_LABEL
        if current_sound == "None":
            current_sound = DEFAULT_SOUND_LABEL
        dialog.sound_combo.blockSignals(True)
        dialog.sound_combo.clear()
        dialog.sound_combo.addItem(DEFAULT_SOUND_LABEL)

        for sound_file in self.get_available_sound_files():
            dialog.sound_combo.addItem(sound_file.stem)

        index = dialog.sound_combo.findText(current_sound)
        dialog.sound_combo.setCurrentIndex(index if index >= 0 else 0)

        dialog.sound_combo.blockSignals(False)

    def handle_sounds_directory_changed(self):
        if SOUNDS_DIR.exists() and str(SOUNDS_DIR) not in self.sounds_watcher.directories():
            self.sounds_watcher.addPath(str(SOUNDS_DIR))

        if self.settings_view and self.view_stack.currentWidget() == self.settings_view:
            dialog = self.settings_view
            QTimer.singleShot(
                200,
                lambda dialog=dialog: self.refresh_sounds_in_dialog(dialog) if dialog is self.settings_view else None
            )

        self.load_selected_sound()

    def open_sounds_folder(self):
        SOUNDS_DIR.mkdir(parents=True, exist_ok=True)
        os.startfile(SOUNDS_DIR)

    def load_selected_sound(self):
        """Load the selected sound file"""
        selected_sound = getattr(self, 'sound_combo_current_text', DEFAULT_SOUND_LABEL)
        if selected_sound == "None":
            selected_sound = DEFAULT_SOUND_LABEL
            self.sound_combo_current_text = selected_sound
        
        # Try to load the selected sound file
        if selected_sound and selected_sound != DEFAULT_SOUND_LABEL:
            for sound_file in self.get_available_sound_files():
                if sound_file.stem == selected_sound:
                    self.selected_sound_file = sound_file
                    return
        
        # Default Sound plays the bundled restore_sound.wav.
        if CUSTOM_RESTORE_SOUND.exists():
            self.selected_sound_file = CUSTOM_RESTORE_SOUND
        else:
            self.selected_sound_file = None


    def play_notification_sound(self):
        """Play the selected notification sound"""
        if self.selected_sound_file and self.selected_sound_file.exists():
            try:
                self.notification_player.stop()
                self.notification_player.setSource(QUrl.fromLocalFile(str(self.selected_sound_file)))
                self.notification_player.play()
            except Exception as e:
                print(f"Error playing notification sound: {e}")
                try:
                    ctypes.windll.user32.MessageBeep(0x00000030)
                except Exception:
                    pass
        else:
            # Fall back to system beep if no sound selected
            try:
                ctypes.windll.user32.MessageBeep(0x00000030)
            except Exception:
                pass

    def open_tmetrics_folder(self):
        if SOURCE_DIR.exists():
            self.auto_close_folder_cb.setChecked(False)
            os.startfile(SOURCE_DIR)

    def open_tmetrics_ringtones_folder(self):
        TMETRIC_RINGTONES_DIR.mkdir(parents=True, exist_ok=True)
        os.startfile(TMETRIC_RINGTONES_DIR)


    def restore_manager_window(self):
        """Restore and show the Voicemail Manager window when a T-Metrics popup is detected."""
        try:
            if self.isMinimized():
                self.showNormal()

            self.show()
            self.raise_()
            self.activateWindow()

            manager_hwnd = int(self.winId())
            if manager_hwnd:
                ctypes.windll.user32.ShowWindow(manager_hwnd, SW_RESTORE)
                ctypes.windll.user32.SetWindowPos(
                    manager_hwnd,
                    HWND_TOPMOST,
                    0,
                    0,
                    0,
                    0,
                    TOPMOST_FLAGS
                )

        except Exception as e:
            print(f"Error restoring manager window: {e}")


    def open_project_link(self):
        webbrowser.open('https://github.com/DustinMeyer1010/T-Metric-Vociemail-Manager')

    def sync_from_source(self):
        if not SOURCE_DIR.exists():
            return
        existing_in_workspace = {f.name for f in WORKSPACE_DIR.iterdir()}
        for f in SOURCE_DIR.iterdir():
            if f.suffix.lower() == '.wav' and f.name not in existing_in_workspace:
                try:
                    shutil.copy2(f, WORKSPACE_DIR / f.name)
                except Exception:
                    pass
        self.refresh_list()

    def get_trash_item_paths(self, trash_item_dir):
        metadata_path = trash_item_dir / "metadata.json"
        voicemail_path = trash_item_dir / "workspace.wav"
        note_path = trash_item_dir / "workspace.txt"
        source_path = trash_item_dir / "source.wav"
        return metadata_path, voicemail_path, note_path, source_path

    def get_deleted_voicemail_entries(self):
        entries = []
        if not TRASH_DIR.exists():
            return entries

        for trash_item_dir in TRASH_DIR.iterdir():
            if not trash_item_dir.is_dir():
                continue

            metadata_path, voicemail_path, note_path, source_path = self.get_trash_item_paths(trash_item_dir)
            if not metadata_path.exists() or not voicemail_path.exists():
                continue

            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                deleted_at = float(metadata.get("deleted_at", 0))
            except Exception:
                continue

            entries.append({
                "trash_dir": trash_item_dir,
                "metadata_path": metadata_path,
                "voicemail_path": voicemail_path,
                "note_path": note_path,
                "source_path": source_path,
                "filename": metadata.get("filename", voicemail_path.name),
                "deleted_at": deleted_at,
                "has_note": note_path.exists(),
                "has_source": source_path.exists(),
            })

        entries.sort(key=lambda entry: entry["deleted_at"], reverse=True)
        return entries

    def purge_expired_deleted_voicemails(self):
        now = time.time()
        retention_seconds = TRASH_RETENTION_DAYS * 24 * 60 * 60

        for entry in self.get_deleted_voicemail_entries():
            deleted_at = entry.get("deleted_at", 0)
            if deleted_at <= 0 or now - deleted_at < retention_seconds:
                continue

            try:
                shutil.rmtree(entry["trash_dir"])
            except Exception as e:
                print(f"Error purging deleted voicemail {entry['trash_dir']}: {e}")

    def move_voicemail_to_trash(self, ws_path):
        deleted_at = time.time()
        trash_item_dir = TRASH_DIR / f"{int(deleted_at * 1000)}_{ws_path.stem}"
        trash_item_dir.mkdir(parents=True, exist_ok=True)

        metadata_path, voicemail_path, note_path, source_path = self.get_trash_item_paths(trash_item_dir)
        metadata = {
            "filename": ws_path.name,
            "deleted_at": deleted_at,
            "was_reviewed": ws_path.name in self.reviewed_files,
        }

        shutil.move(str(ws_path), str(voicemail_path))

        ws_note_path = ws_path.with_suffix(".txt")
        if ws_note_path.exists():
            shutil.move(str(ws_note_path), str(note_path))

        original_file_path = SOURCE_DIR / ws_path.name
        if original_file_path.exists():
            shutil.move(str(original_file_path), str(source_path))

        metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    def format_trash_time_remaining(self, deleted_at):
        retention_seconds = TRASH_RETENTION_DAYS * 24 * 60 * 60
        remaining_seconds = max(0, int((deleted_at + retention_seconds) - time.time()))

        days, remainder = divmod(remaining_seconds, 24 * 60 * 60)
        hours, remainder = divmod(remainder, 60 * 60)
        minutes, _ = divmod(remainder, 60)

        if days > 0:
            return f"{days}d {hours}h left"
        if hours > 0:
            return f"{hours}h {minutes}m left"
        return f"{minutes}m left"

    def confirm_delete_action(self, title, text, icon=QMessageBox.Icon.NoIcon, default_button=QMessageBox.StandardButton.No):
        if not self.ask_before_delete:
            return True

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(text)
        msg_box.setIcon(icon)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(default_button)
        msg_box.setStyleSheet(self.current_style)
        if msg_box.layout():
            msg_box.layout().setContentsMargins(20, 20, 20, 20)

        ask_checkbox = QCheckBox("Ask before deleting voicemails")
        ask_checkbox.setChecked(True)
        msg_box.setCheckBox(ask_checkbox)

        confirmed = msg_box.exec() == QMessageBox.StandardButton.Yes
        self.ask_before_delete = ask_checkbox.isChecked()
        self.save_config()
        return confirmed

    def recover_deleted_voicemail(self):
        self.purge_expired_deleted_voicemails()
        deleted_entries = self.get_deleted_voicemail_entries()
        if not deleted_entries:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Recover Deleted")
            msg_box.setText("There are no deleted voicemails available to recover.")
            msg_box.setStyleSheet(self.current_style)
            if msg_box.layout():
                msg_box.layout().setContentsMargins(20, 20, 20, 20)
            msg_box.exec()
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Recover Deleted Voicemail")
        dialog.resize(560, 420)
        dialog.setStyleSheet(self.current_style)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        title_label = QLabel("Recover Deleted Voicemail")
        title_label.setFont(QFont("Segoe UI Semibold", 12))
        layout.addWidget(title_label)

        info_label = QLabel(
            f"Deleted voicemails stay available for recovery for {TRASH_RETENTION_DAYS} days. "
            "Choose one below to restore it to the main list."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        deleted_list = QListWidget()
        deleted_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        layout.addWidget(deleted_list)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        close_btn = QPushButton("Close")
        restore_btn = QPushButton("Restore")
        button_layout.addWidget(close_btn)
        button_layout.addWidget(restore_btn)
        layout.addLayout(button_layout)

        def refresh_deleted_list():
            self.purge_expired_deleted_voicemails()
            current_entries = self.get_deleted_voicemail_entries()
            deleted_list.clear()

            for entry in current_entries:
                time_remaining = self.format_trash_time_remaining(entry["deleted_at"])
                item = QListWidgetItem(f"{entry['filename']}   |   {time_remaining}")
                item.setData(Qt.ItemDataRole.UserRole, str(entry["trash_dir"]))
                item.setSizeHint(QSize(0, 38))
                deleted_list.addItem(item)

            has_entries = bool(current_entries)
            restore_btn.setEnabled(has_entries)
            if has_entries:
                deleted_list.setCurrentRow(0)
                info_label.setText(
                    f"Deleted voicemails stay available for recovery for {TRASH_RETENTION_DAYS} days. "
                    "Choose one below to restore it to the main list."
                )
            else:
                info_label.setText("There are no deleted voicemails available to recover.")

            return current_entries

        current_entries = refresh_deleted_list()

        close_btn.clicked.connect(dialog.reject)

        def restore_selected_entry():
            current_entries = refresh_deleted_list()
            selected_item = deleted_list.currentItem()
            if not selected_item:
                return

            selected_dir = Path(selected_item.data(Qt.ItemDataRole.UserRole))
            selected_entry = next((entry for entry in current_entries if entry["trash_dir"] == selected_dir), None)
            if not selected_entry:
                return

            restore_target = WORKSPACE_DIR / selected_entry["filename"]
            if restore_target.exists():
                QMessageBox.warning(self, "Recover Deleted", f"{selected_entry['filename']} already exists in the workspace.")
                refresh_deleted_list()
                return

            try:
                shutil.move(str(selected_entry["voicemail_path"]), str(restore_target))

                if selected_entry["has_note"]:
                    shutil.move(str(selected_entry["note_path"]), str(restore_target.with_suffix(".txt")))

                if selected_entry["has_source"] and SOURCE_DIR.exists():
                    source_restore_target = SOURCE_DIR / selected_entry["filename"]
                    if not source_restore_target.exists():
                        shutil.move(str(selected_entry["source_path"]), str(source_restore_target))

                metadata = json.loads(selected_entry["metadata_path"].read_text(encoding="utf-8"))
                if metadata.get("was_reviewed"):
                    self.reviewed_files.add(selected_entry["filename"])
                    self.save_reviewed_cache()

                shutil.rmtree(selected_entry["trash_dir"], ignore_errors=True)
                self.refresh_list()
                remaining_entries = refresh_deleted_list()

                for row in range(self.list_widget.count()):
                    row_item = self.list_widget.item(row)
                    if row_item and row_item.data(Qt.ItemDataRole.UserRole) == str(restore_target.absolute()):
                        self.list_widget.setCurrentRow(row)
                        self.on_item_selected()
                        break

                if remaining_entries:
                    deleted_list.setCurrentRow(0)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Recovery failed: {e}")

        restore_btn.clicked.connect(restore_selected_entry)
        dialog.exec()

    def refresh_list(self):
        self.purge_expired_deleted_voicemails()
        selected_path = None
        current_item = self.list_widget.currentItem()
        if current_item:
            selected_path = current_item.data(Qt.ItemDataRole.UserRole)

        was_empty = self.list_widget.count() == 0
        self.list_widget.blockSignals(True)
        self.list_widget.clear()

        files = [f for f in WORKSPACE_DIR.glob("*") if f.suffix.lower() == '.wav']
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
            item.setSizeHint(QSize(0, 38))
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

        self.status_label.setText(f"Voicemails Displayed: {visible_count}/{len(files)}")
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
                self.list_widget.clearSelection()
                self.on_item_selected()
                self.unreview_btn.setEnabled(False)

    def prompt_rename(self):
        item = self.list_widget.currentItem()
        if not item:
            return

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
        dialog.setStyleSheet(self.current_style)

        if dialog.layout():
            dialog.layout().setContentsMargins(20, 20, 20, 20)
            dialog.layout().setSpacing(12)

        QTimer.singleShot(0, dialog.findChild(QLineEdit).selectAll)

        if dialog.exec() == QInputDialog.DialogCode.Accepted:
            user_input = dialog.textValue().strip()
            if not user_input:
                return

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
                    try:
                        os.rename(old_note_path, new_ws_path.with_suffix(".txt"))
                    except OSError:
                        pass

                original_file_path = SOURCE_DIR / ws_path.name
                if original_file_path.exists():
                    try:
                        os.rename(original_file_path, SOURCE_DIR / new_name)
                    except OSError:
                        pass
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
        if not item:
            return

        ws_path = Path(item.data(Qt.ItemDataRole.UserRole))
        confirmed = self.confirm_delete_action(
            "Delete",
            f"Delete {ws_path.name}?\n\nYou can recover it for up to {TRASH_RETENTION_DAYS} days."
        )

        if confirmed:
            if ws_path.name in self.reviewed_files:
                self.reviewed_files.discard(ws_path.name)
                self.save_reviewed_cache()

            try:
                self.move_voicemail_to_trash(ws_path)
                self.refresh_list()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Delete failed: {e}")

    def delete_all_files(self):
        self.media_player.stop()
        self.media_player.setSource(QUrl())
        file_count = len(list(WORKSPACE_DIR.glob("*.wav"))) if WORKSPACE_DIR.exists() else 0
        if file_count == 0:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Delete All")
            msg_box.setText("No voicemails found to delete.")
            msg_box.setStyleSheet(self.current_style)
            if msg_box.layout():
                msg_box.layout().setContentsMargins(20, 20, 20, 20)
            msg_box.exec()
            return

        confirmed = self.confirm_delete_action(
            "Confirm Delete All",
            f"Delete ALL {file_count} voicemails?\n\n"
            f"They will be recoverable for {TRASH_RETENTION_DAYS} days before permanent deletion.",
            icon=QMessageBox.Icon.Warning,
            default_button=QMessageBox.StandardButton.No
        )

        if confirmed:
            self.reviewed_files.clear()
            self.save_reviewed_cache()
            if WORKSPACE_DIR.exists():
                for f in WORKSPACE_DIR.glob("*.wav"):
                    try:
                        self.move_voicemail_to_trash(f)
                    except Exception:
                        pass
            self.refresh_list()

            success_box = QMessageBox(self)
            success_box.setWindowTitle("Success")
            success_box.setText(
                f"All voicemails were moved to Deleted Voicemails.\n\n"
                f"They can be recovered for {TRASH_RETENTION_DAYS} days."
            )
            success_box.setStyleSheet(self.current_style)
            if success_box.layout():
                success_box.layout().setContentsMargins(20, 20, 20, 20)
            success_box.exec()
