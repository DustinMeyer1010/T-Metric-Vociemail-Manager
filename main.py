import os
import sys
import ctypes
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from constants import DARK_THEME_STYLE, ICON_PATH
from manager import VoicemailManager

SINGLE_INSTANCE_MUTEX_NAME = "TMetricVoicemailManagerSingleInstance"
WINDOW_TITLE = "T-Metric Voicemail Manager"
ERROR_ALREADY_EXISTS = 183
SW_RESTORE = 9


def focus_existing_window():
    matching_hwnd = {"value": None}

    def enum_windows_callback(hwnd, lparam):
        if not ctypes.windll.user32.IsWindowVisible(hwnd):
            return True

        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True

        buffer = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buffer, length + 1)
        if buffer.value.strip() == WINDOW_TITLE:
            matching_hwnd["value"] = hwnd
            return False

        return True

    enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(enum_windows_callback)
    ctypes.windll.user32.EnumWindows(enum_proc, 0)

    hwnd = matching_hwnd["value"]
    if hwnd:
        ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)
        ctypes.windll.user32.BringWindowToTop(hwnd)
        ctypes.windll.user32.SetForegroundWindow(hwnd)
        return True

    return False


def main():
    try:
        myappid = 'DustinMeyer.tmetrics.workspace.v2'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception as e:
        print(f"Could not set AppUserModelID: {e}")

    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, SINGLE_INSTANCE_MUTEX_NAME)
    if not mutex:
        print("Could not create single-instance mutex.")
    elif ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        focus_existing_window()
        return

    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_THEME_STYLE)
    app.setStyle('Fusion')

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

    window = VoicemailManager(app)

    if os.path.exists(resolved_icon_path):
        window.setWindowIcon(QIcon(resolved_icon_path))
    elif getattr(sys, 'frozen', False):
        window.setWindowIcon(QIcon(os.path.abspath(sys.executable)))

    window.show()
    exit_code = app.exec()

    if mutex:
        ctypes.windll.kernel32.CloseHandle(mutex)

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
