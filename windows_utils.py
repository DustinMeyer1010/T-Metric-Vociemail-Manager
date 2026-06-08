import ctypes

from constants import SW_RESTORE


def focus_existing_window(window_title: str) -> bool:
    matching_hwnd = {"value": None}

    def enum_windows_callback(hwnd, lparam):
        if not ctypes.windll.user32.IsWindowVisible(hwnd):
            return True

        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True

        buffer = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buffer, length + 1)
        if buffer.value.strip() == window_title:
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
