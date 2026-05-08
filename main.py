import os
import sys
import ctypes
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from constants import DARK_THEME_STYLE, ICON_PATH
from manager import VoicemailManager


def main():
    try:
        myappid = 'DustinMeyer.tmetrics.workspace.v2'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception as e:
        print(f"Could not set AppUserModelID: {e}")

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
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
