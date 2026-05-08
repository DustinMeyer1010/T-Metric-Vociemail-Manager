import os
import sys
import ctypes
from pathlib import Path

SOURCE_DIR = Path(os.getenv('APPDATA')) / "T-Metrics, Inc" / "ACD Agent Module" / "Downloads"
ICON_PATH = "URMC.ico"

CACHE_DIR = Path(os.getenv('APPDATA')) / "T-Metrics, Inc" / "VoicemailManager"
WORKSPACE_DIR = CACHE_DIR / "Voicemail_Workspace"
SOUNDS_DIR = CACHE_DIR / "Voicemail_Sounds"

# Handle both frozen and non-frozen environments
if getattr(sys, 'frozen', False):
    BASE_PATH = Path(sys._MEIPASS)
else:
    BASE_PATH = Path(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_SOUNDS_DIR = BASE_PATH / "default_sounds"
CACHE_FILE = CACHE_DIR / "reviewed_cache.txt"
CONFIG_FILE = CACHE_DIR / "config.txt"

CACHE_DIR.mkdir(parents=True, exist_ok=True)
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
SOUNDS_DIR.mkdir(parents=True, exist_ok=True)

HWND_TOPMOST = -1
SW_RESTORE = 9
SW_SHOWNOACTIVATE = 4
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
TOPMOST_FLAGS = SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
CUSTOM_RESTORE_SOUND = BASE_PATH / "restore_sound.wav"

# DWM (Desktop Window Manager) constants for title bar theming
# Windows 10: 19, Windows 11: 20
import sys
if sys.getwindowsversion().build >= 22000:  # Windows 11
    DWMWA_USE_IMMERSIVE_DARK_MODE = 20
else:  # Windows 10
    DWMWA_USE_IMMERSIVE_DARK_MODE = 19

EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

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
        background-color: #37474F;
        border: 1px solid #546E7A;
        border-radius: 3px;
        padding: 0px;
        min-width: 32px;
        max-width: 32px;
        min-height: 55px;
        max-height: 55px;
    }
    QPushButton#play_btn:hover {
        background-color: #455A64;
        border-color: #00E5FF;
    }
    QPushButton#play_btn:pressed {
        background-color: #263238;
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

    /* Theme Button Specific Styling */
    QPushButton#theme_btn {
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
    QPushButton#theme_btn:hover {
        background-color: #009688;
        color: white;
    }

    /* Settings Button Specific Styling */
    QPushButton#settings_btn {
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
    QPushButton#settings_btn:hover {
        background-color: #009688;
        color: white;
    }

    /* Refresh Sounds Button Styling */
    QPushButton#refresh_sounds_btn {
        background-color: #37474F;
        color: #00E5FF;
        font-size: 10pt;
        font-weight: bold;
        padding: 2px;
        min-width: 24px;
        max-width: 24px;
        min-height: 20px;
        max-height: 20px;
        border: 1px solid #546E7A;
        border-radius: 3px;
    }
    QPushButton#refresh_sounds_btn:hover {
        background-color: #455A64;
        color: #00E5FF;
    }
    QPushButton#refresh_sounds_btn:pressed {
        background-color: #263238;
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

LIGHT_THEME_STYLE = """
    QMainWindow {
        background-color: #FFFFFF;
    }
    
    QLabel {
        color: #111827;
    }
    
    /* Modern Light Theme Buttons */
    QPushButton {
        background-color: #2563EB;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 8px 16px;
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
        background-color: #E5E7EB;
        border: 1px solid #9CA3AF;
        border-radius: 3px;
        padding: 0px;
        min-width: 32px;
        max-width: 32px;
        min-height: 55px;
        max-height: 55px;
    }
    QPushButton#play_btn:hover {
        background-color: #D1D5DB;
        border-color: #2563EB;
    }
    QPushButton#play_btn:pressed {
        background-color: #F9FAFB;
    }

    QPushButton:hover {
        background-color: #1D4ED8;
    }
    QPushButton:pressed {
        background-color: #1E40AF;
    }
    QPushButton:disabled {
        background-color: #E5E7EB;
        color: #9CA3AF;
    }
    
    /* Info Button Specific Styling */
    QPushButton#info_btn {
        background-color: transparent;
        color: #2563EB;
        font-size: 13pt;
        font-weight: bold;
        padding: 0px;
        min-width: 28px;
        max-width: 28px;
        min-height: 28px;
        max-height: 28px;
        border-radius: 4px;
    }
    QPushButton#info_btn:hover {
        background-color: #2563EB;
        color: white;
    }

    /* Theme Button Specific Styling */
    QPushButton#theme_btn {
        background-color: transparent;
        color: #2563EB;
        font-size: 13pt;
        font-weight: bold;
        padding: 0px;
        min-width: 28px;
        max-width: 28px;
        min-height: 28px;
        max-height: 28px;
        border-radius: 4px;
    }
    QPushButton#theme_btn:hover {
        background-color: #2563EB;
        color: white;
    }

    /* Settings Button Specific Styling */
    QPushButton#settings_btn {
        background-color: transparent;
        color: #2563EB;
        font-size: 13pt;
        font-weight: bold;
        padding: 0px;
        min-width: 28px;
        max-width: 28px;
        min-height: 28px;
        max-height: 28px;
        border-radius: 4px;
    }
    QPushButton#settings_btn:hover {
        background-color: #2563EB;
        color: white;
    }

    /* Refresh Sounds Button Styling */
    QPushButton#refresh_sounds_btn {
        background-color: #E5E7EB;
        color: #2563EB;
        font-size: 10pt;
        font-weight: bold;
        padding: 2px;
        min-width: 24px;
        max-width: 24px;
        min-height: 20px;
        max-height: 20px;
        border: 1px solid #D1D5DB;
        border-radius: 3px;
    }
    QPushButton#refresh_sounds_btn:hover {
        background-color: #D1D5DB;
        color: #1E40AF;
    }
    QPushButton#refresh_sounds_btn:pressed {
        background-color: #F9FAFB;
    }

    /* Bulk Action Button Styling */
    QPushButton#delete_all_btn {
        background-color: #6B7280;
        color: white;
    }
    QPushButton#delete_all_btn:hover {
        background-color: #4B5563;
    }
    QPushButton#delete_all_btn:pressed {
        background-color: #374151;
    }
    
    /* Light Theme Voicemail Row List Container */
    QListWidget {
        background-color: #F3F4F6;
        border: 2px solid #D1D5DB;
        border-radius: 8px;
        padding: 5px;
    }
    QListWidget::item {
        border-bottom: 1px solid #E5E7EB;
        padding: 10px;
        margin-bottom: 2px;
        border-radius: 6px;
        color: #111827;
        background-color: #FFFFFF;
        border: 1px solid #F3F4F6;
    }
    QListWidget::item:hover {
        background-color: #F9FAFB;
        color: #111827;
        border: 1px solid #D1D5DB;
    }
    QListWidget::item:selected {
        background-color: #DBEAFE;
        color: #1E40AF;
        font-weight: 500;
        border: 2px solid #2563EB;
    }
    
    /* Modernized Light Theme Checkboxes */
    QCheckBox {
        spacing: 8px;
        color: #111827;
    }
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border: 2px solid #6B7280;
        border-radius: 4px;
        background-color: #FFFFFF;
    }
    QCheckBox::indicator:hover {
        border-color: #2563EB;
    }
    QCheckBox::indicator:checked {
        background-color: #2563EB;
        border-color: #2563EB;
    }

    /* Audio Selection Dropdown Menu styling */
    QComboBox {
        border: 2px solid #D1D5DB;
        border-radius: 6px;
        padding: 6px 8px;
        background-color: #FFFFFF;
        color: #111827;
    }
    QComboBox:hover {
        border-color: #2563EB;
    }
    QComboBox::drop-down {
        border: none;
        background:  #FFFFFF;
    }
    
    /* Dropdown Internal List Engine Configurations */
    QComboBox QAbstractItemView,
    QComboBox QListView {
        background-color: #FFFFFF;
        border: 2px solid #D1D5DB;
        border-radius: 6px;
        padding: 4px;
        color: #111827;
        outline: 0px;
        selection-background-color: #2563EB;
    }
    QComboBox QAbstractItemView::item,
    QComboBox QListView::item {
        padding: 8px;
        border-radius: 4px;
        color: #111827;
        background-color: #FFFFFF;
    }
    QComboBox QAbstractItemView::item:hover,
    QComboBox QAbstractItemView::item:selected,
    QComboBox QListView::item:hover,
    QComboBox QListView::item:selected {
        background-color: #3B82F6 !important;
        color: #FFFFFF !important;
    }
    
    /* Inputs & Modals */
    QDialog {
        background-color: #FFFFFF;
        border-radius: 8px;
    }
    QInputDialog {
        background-color: #FFFFFF;
    }
    QInputDialog QLabel {
        margin-bottom: 6px;
        font-size: 11pt;
    }
    QLineEdit {
        background-color: #FFFFFF;
        border: 2px solid #D1D5DB;
        border-radius: 6px;
        padding: 8px 12px;
        color: #111827;
        font-size: 11pt;
        selection-background-color: #3B82F6;
    }
    QLineEdit:focus {
        border: 2px solid #2563EB;
        outline: none;
    }

    /* Compact Workspace Sidebar Note Field Stylesheet */
    QTextEdit {
        background-color: #FFFFFF;
        border: 1px solid #D1D5DB;
        border-radius: 6px;
        color: #111827;
        padding: 8px;
        font-family: "Segoe UI", sans-serif;
        font-size: 10pt;
    }
    QTextEdit:focus {
        border: 2px solid #2563EB;
        outline: none;
    }
    QTextEdit:disabled {
        background-color: #F9FAFB;
        color: #9CA3AF;
        border-color: #E5E7EB;
    }
"""

CARTOON_THEME_STYLE = """
    QMainWindow, QDialog {
        background-color: #FFF4C2;
    }

    QLabel {
        color: #243B53;
        font-family: "Comic Sans MS", "Segoe UI", sans-serif;
        font-weight: 700;
    }

    QPushButton {
        background-color: #FF7A59;
        color: #1F2937;
        border: 2px solid #243B53;
        border-radius: 8px;
        padding: 7px 16px;
        font-family: "Comic Sans MS", "Segoe UI", sans-serif;
        font-weight: 800;
        font-size: 12px;
        min-width: 75px;
    }
    QPushButton:hover {
        background-color: #FFB703;
    }
    QPushButton:pressed {
        background-color: #FB5607;
        color: #FFFFFF;
    }
    QPushButton:disabled {
        background-color: #F4D6A0;
        color: #8A817C;
        border-color: #B08968;
    }

    QPushButton#play_btn {
        background-color: #FFE066;
        border: 2px solid #243B53;
        border-radius: 8px;
        padding: 0px;
        min-width: 32px;
        max-width: 32px;
        min-height: 55px;
        max-height: 55px;
    }
    QPushButton#play_btn:hover {
        background-color: #FFB703;
        border-color: #3A86FF;
    }
    QPushButton#play_btn:pressed {
        background-color: #FB5607;
    }

    QPushButton#settings_btn {
        background-color: transparent;
        border: 2px solid transparent;
        border-radius: 6px;
        padding: 0px;
        min-width: 28px;
        max-width: 28px;
        min-height: 28px;
        max-height: 28px;
    }
    QPushButton#settings_btn:hover {
        background-color: #FFE066;
        border-color: #243B53;
    }

    QPushButton#refresh_sounds_btn {
        background-color: #FFE066;
        color: #243B53;
        font-weight: 800;
        padding: 2px;
        min-width: 24px;
        max-width: 24px;
        min-height: 20px;
        max-height: 20px;
        border: 2px solid #243B53;
        border-radius: 6px;
    }
    QPushButton#refresh_sounds_btn:hover {
        background-color: #FFB703;
    }
    QPushButton#refresh_sounds_btn:pressed {
        background-color: #FB5607;
    }

    QPushButton#delete_all_btn {
        background-color: #EF476F;
        color: #FFFFFF;
    }
    QPushButton#delete_all_btn:hover {
        background-color: #D90429;
    }

    QListWidget {
        background-color: #FFFFFF;
        border: 3px solid #243B53;
        border-radius: 10px;
        padding: 5px;
        color: #243B53;
        font-family: "Comic Sans MS", "Segoe UI", sans-serif;
    }
    QListWidget::item {
        border-bottom: 2px solid #FFE066;
        padding: 8px;
    }
    QListWidget::item:selected {
        background-color: #3A86FF;
        color: #FFFFFF;
        border-radius: 6px;
    }

    QLineEdit, QTextEdit, QComboBox {
        background-color: #FFFFFF;
        border: 2px solid #243B53;
        border-radius: 8px;
        color: #243B53;
        padding: 6px;
        font-family: "Comic Sans MS", "Segoe UI", sans-serif;
    }
    QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
        border-color: #3A86FF;
    }

    QCheckBox {
        color: #243B53;
        font-family: "Comic Sans MS", "Segoe UI", sans-serif;
        font-weight: 800;
        spacing: 8px;
    }
    QCheckBox::indicator {
        width: 16px;
        height: 16px;
        border: 2px solid #243B53;
        border-radius: 4px;
        background-color: #FFFFFF;
    }
    QCheckBox::indicator:checked {
        background-color: #06D6A0;
    }

    QGroupBox {
        border: 3px solid #243B53;
        border-radius: 10px;
        margin-top: 12px;
        padding: 12px 8px 8px 8px;
        font-family: "Comic Sans MS", "Segoe UI", sans-serif;
        font-weight: 800;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 12px;
        padding: 0px 6px;
        background-color: #FFF4C2;
    }
"""
