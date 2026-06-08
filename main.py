import os
import sys
import ctypes
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from app_logger import setup_logging, get_logger
from constants import DARK_THEME_STYLE, ICON_PATH, SINGLE_INSTANCE_MUTEX_NAME, WINDOW_TITLE, ERROR_ALREADY_EXISTS
from windows_utils import focus_existing_window
from manager import VoicemailManager
logger = get_logger("main")


# Focus helper extracted to `windows_utils.py`


def main():
    setup_logging()
    logger.info("Application startup initiated")
    try:
        myappid = 'DustinMeyer.tmetrics.workspace.v2'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception as e:
        logger.exception("Could not set AppUserModelID: %s", e)

    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, SINGLE_INSTANCE_MUTEX_NAME)
    if not mutex:
        logger.error("Could not create single-instance mutex")
    elif ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        logger.info("Second instance launch detected; focusing existing window")
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
    logger.info("Main window shown")
    exit_code = app.exec()
    logger.info("Application exiting with code %s", exit_code)

    if mutex:
        ctypes.windll.kernel32.CloseHandle(mutex)

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
