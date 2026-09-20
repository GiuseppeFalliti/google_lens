from __future__ import annotations

import ctypes
from ctypes import wintypes
import sys

from PySide6.QtCore import QAbstractNativeEventFilter, QObject, Signal

from src.exceptions import ScreenTranslatorError


WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000


class HotkeyError(ScreenTranslatorError):
    pass


class _NativeHotkeyFilter(QAbstractNativeEventFilter):
    def __init__(self, owner: "HotkeyManager") -> None:
        super().__init__()
        self._owner = owner

    def nativeEventFilter(self, event_type, message):  # noqa: N802
        del event_type
        if sys.platform != "win32":
            return False, 0

        try:
            msg = wintypes.MSG.from_address(int(message))
        except (TypeError, ValueError):
            return False, 0

        if msg.message == WM_HOTKEY and int(msg.wParam) == self._owner.hotkey_id:
            self._owner.hotkey_pressed.emit()
            return True, 0
        return False, 0


class HotkeyManager(QObject):
    hotkey_pressed = Signal()

    def __init__(self, application, hotkey_id: int = 0x51A7) -> None:
        super().__init__()
        self._application = application
        self.hotkey_id = hotkey_id
        self._registered = False
        self._filter = _NativeHotkeyFilter(self)
        application.installNativeEventFilter(self._filter)

    @staticmethod
    def _parse(hotkey: str) -> tuple[int, int]:
        parts = [part.strip().upper() for part in hotkey.replace(" ", "").split("+")]
        parts = [part for part in parts if part]
        if not parts:
            raise HotkeyError("Hotkey cannot be empty.")

        key_name = parts[-1]
        modifiers = MOD_NOREPEAT
        for modifier in parts[:-1]:
            if modifier in {"CTRL", "CONTROL"}:
                modifiers |= MOD_CONTROL
            elif modifier == "SHIFT":
                modifiers |= MOD_SHIFT
            elif modifier == "ALT":
                modifiers |= MOD_ALT
            elif modifier in {"WIN", "WINDOWS", "META"}:
                modifiers |= MOD_WIN
            else:
                raise HotkeyError(f"Unsupported hotkey modifier: {modifier}")

        if len(key_name) == 1 and key_name.isalnum():
            virtual_key = ord(key_name)
        elif key_name.startswith("F") and key_name[1:].isdigit():
            number = int(key_name[1:])
            if not 1 <= number <= 24:
                raise HotkeyError("Function key must be between F1 and F24.")
            virtual_key = 0x70 + number - 1
        else:
            raise HotkeyError(
                "The hotkey key must be A-Z, 0-9, or F1-F24 in this MVP."
            )

        return modifiers, virtual_key

    def register(self, hotkey: str) -> None:
        if sys.platform != "win32":
            raise HotkeyError("Global hotkeys are supported only on Windows.")

        self.unregister()
        modifiers, virtual_key = self._parse(hotkey)

        user32 = ctypes.windll.user32
        if not user32.RegisterHotKey(None, self.hotkey_id, modifiers, virtual_key):
            raise HotkeyError(
                f"Unable to register '{hotkey}'. It may already be used by another app."
            )
        self._registered = True

    def unregister(self) -> None:
        if self._registered and sys.platform == "win32":
            ctypes.windll.user32.UnregisterHotKey(None, self.hotkey_id)
        self._registered = False

    def close(self) -> None:
        self.unregister()
        try:
            self._application.removeNativeEventFilter(self._filter)
        except RuntimeError:
            pass
