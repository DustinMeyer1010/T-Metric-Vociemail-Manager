import os
import ctypes
from pathlib import Path

SOURCE_DIR = Path(os.getenv('APPDATA')) / "T-Metrics, Inc" / "ACD Agent Module" / "Downloads"
ICON_PATH = "URMC.ico"

CACHE_DIR = Path(os.getenv('APPDATA')) / "T-Metrics, Inc" / "VoicemailManager"
WORKSPACE_DIR = CACHE_DIR / "Voicemail_Workspace"
CACHE_FILE = CACHE_DIR / "reviewed_cache.txt"
CONFIG_FILE = CACHE_DIR / "config.txt"

CACHE_DIR.mkdir(parents=True, exist_ok=True)
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

HWND_TOPMOST = -1
SW_RESTORE = 9
SW_SHOWNOACTIVATE = 4
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
TOPMOST_FLAGS = SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
CUSTOM_RESTORE_SOUND = Path(os.path.dirname(os.path.abspath(__file__))) / "restore_sound.wav"

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
