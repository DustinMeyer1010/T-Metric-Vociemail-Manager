import os
import shutil
import struct
from pathlib import Path
import logging

from constants import SOUNDS_DIR, DEFAULT_SOUNDS_DIR

logger = logging.getLogger("manager_utils")


def get_wav_duration(file_path: str) -> int:
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
        logger.exception("Error parsing metadata header: %s", e)
    return 0


def copy_default_sounds():
    """Copy default sounds from the bundled `default_sounds` folder into the user's sounds folder."""
    try:
        default_dir = DEFAULT_SOUNDS_DIR
        target_dir = SOUNDS_DIR

        if not default_dir.exists():
            return

        for sound_file in default_dir.iterdir():
            if sound_file.suffix.lower() in ('.wav', '.mp3', '.flac', '.ogg'):
                target_file = target_dir / sound_file.name
                if not target_file.exists():
                    try:
                        shutil.copy2(str(sound_file), str(target_file))
                    except Exception as e:
                        logger.exception("Error copying default sound %s: %s", sound_file, e)
    except Exception as e:
        logger.exception("Error in copy_default_sounds: %s", e)