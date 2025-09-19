"""Utilities for sending chat messages to native Windows chat windows.

This module provides a small helper that finds child controls whose class
name is ``RICHEDIT50W`` and replaces their text with a given message. The
helper can optionally simulate pressing the Enter key so that the host
application treats the message as if a user typed it.

The implementation is intentionally self-contained and relies only on the
standard library, using :mod:`ctypes` to call the Win32 API directly. This
keeps the dependency surface small while still providing the level of control
required to interact with native chat windows.
"""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from typing import Callable, Iterator, List, Optional, Sequence


try:  # pragma: no cover - platform dependent branch
    USER32 = ctypes.windll.user32  # type: ignore[attr-defined]
    KERNEL32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
except (AttributeError, OSError):
    USER32 = None
    KERNEL32 = None


def _ensure_windows() -> None:
    """Ensure the current interpreter runs on a Windows platform.

    The helpers in this module use functions that are only available on
    Windows. Importing the module on a different operating system is fine, but
    calling any of the exported functions will raise :class:`OSError`.
    """

    if USER32 is None or KERNEL32 is None:
        raise OSError("chat_sender utilities are only available on Windows.")


# Constants used when sending keyboard input to windows.
WM_SETTEXT = 0x000C
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_CHAR = 0x0102
VK_RETURN = 0x0D


if USER32 is not None:
    # Register prototypes for Win32 APIs that will be called from Python.
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    USER32.EnumWindows.argtypes = (WNDENUMPROC, wintypes.LPARAM)
    USER32.EnumWindows.restype = wintypes.BOOL

    USER32.EnumChildWindows.argtypes = (wintypes.HWND, WNDENUMPROC, wintypes.LPARAM)
    USER32.EnumChildWindows.restype = wintypes.BOOL

    USER32.IsWindowVisible.argtypes = (wintypes.HWND,)
    USER32.IsWindowVisible.restype = wintypes.BOOL

    USER32.GetWindowTextLengthW.argtypes = (wintypes.HWND,)
    USER32.GetWindowTextLengthW.restype = ctypes.c_int

    USER32.GetWindowTextW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
    USER32.GetWindowTextW.restype = ctypes.c_int

    USER32.GetClassNameW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
    USER32.GetClassNameW.restype = ctypes.c_int

    USER32.SendMessageW.argtypes = (wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
    USER32.SendMessageW.restype = wintypes.LRESULT

    USER32.MapVirtualKeyW.argtypes = (wintypes.UINT, wintypes.UINT)
    USER32.MapVirtualKeyW.restype = wintypes.UINT


else:  # pragma: no cover - executed on non-Windows platforms

    def WNDENUMPROC(func):  # type: ignore[override]
        return func


@dataclass
class ChatTarget:
    """Description of a chat text input control.

    Attributes
    ----------
    window_handle:
        Handle of the top-level window that owns the chat input.
    edit_handle:
        Handle of the ``RICHEDIT50W`` child control where text is written.
    window_title:
        Current title of the top-level window. This is useful for logging or
        for generating per-window messages via :func:`send_message_to_chatrooms`.
    """

    window_handle: int
    edit_handle: int
    window_title: str


def _get_window_text(hwnd: int) -> str:
    _ensure_windows()
    length = USER32.GetWindowTextLengthW(hwnd)
    if length == 0:
        # Either no title or the call failed. We still attempt to fetch the
        # text so that we return an empty string when appropriate.
        buffer = ctypes.create_unicode_buffer(1)
    else:
        buffer = ctypes.create_unicode_buffer(length + 1)
    USER32.GetWindowTextW(hwnd, buffer, len(buffer))
    return buffer.value


def _get_class_name(hwnd: int) -> str:
    _ensure_windows()
    buffer = ctypes.create_unicode_buffer(256)
    USER32.GetClassNameW(hwnd, buffer, len(buffer))
    return buffer.value


def _iter_top_level_windows() -> Iterator[int]:
    _ensure_windows()
    windows: List[int] = []

    @WNDENUMPROC
    def _enum_proc(hwnd: int, _lparam: int) -> bool:
        if USER32.IsWindowVisible(hwnd):
            windows.append(hwnd)
        return True

    if not USER32.EnumWindows(_enum_proc, 0):
        raise ctypes.WinError(ctypes.get_last_error())
    return iter(windows)


def _iter_child_windows(parent: int) -> Iterator[int]:
    _ensure_windows()
    children: List[int] = []

    @WNDENUMPROC
    def _enum_proc(hwnd: int, _lparam: int) -> bool:
        children.append(hwnd)
        return True

    if not USER32.EnumChildWindows(parent, _enum_proc, 0):
        raise ctypes.WinError(ctypes.get_last_error())
    return iter(children)


def _make_title_filter(
    window_title_filter: Optional[Sequence[str] | Callable[[str], bool]]
) -> Callable[[str], bool]:
    if window_title_filter is None:
        return lambda _title: True
    if callable(window_title_filter):
        return window_title_filter

    lowered = [fragment.lower() for fragment in window_title_filter if fragment]

    if not lowered:
        return lambda _title: True

    def _checker(title: str) -> bool:
        title_lower = (title or "").lower()
        return any(fragment in title_lower for fragment in lowered)

    return _checker


def find_chat_targets(
    *,
    window_title_filter: Optional[Sequence[str] | Callable[[str], bool]] = None,
) -> List[ChatTarget]:
    """Return a list of :class:`ChatTarget` objects for visible chat windows.

    Parameters
    ----------
    window_title_filter:
        Optional sequence of substrings (case-insensitive) or a callable used
        to filter the top-level windows that are inspected. When provided, only
        windows whose title matches the filter will be considered.
    """

    _ensure_windows()
    matches: List[ChatTarget] = []
    checker = _make_title_filter(window_title_filter)

    for window in _iter_top_level_windows():
        title = _get_window_text(window)
        if not checker(title):
            continue
        for child in _iter_child_windows(window):
            if _get_class_name(child) == "RICHEDIT50W":
                matches.append(ChatTarget(window, child, title))

    return matches


def _build_key_lparam(virtual_key: int, *, key_down: bool) -> int:
    scan_code = USER32.MapVirtualKeyW(virtual_key, 0)
    lparam = 1 | (scan_code << 16)
    if not key_down:
        lparam |= 0xC0000000  # Transition state and previous key-state bits.
    return lparam


def _set_edit_text(edit_hwnd: int, text: str) -> None:
    buffer = ctypes.c_wchar_p(text)
    USER32.SendMessageW(edit_hwnd, WM_SETTEXT, 0, buffer)


def _send_enter(edit_hwnd: int) -> None:
    down_lparam = _build_key_lparam(VK_RETURN, key_down=True)
    up_lparam = _build_key_lparam(VK_RETURN, key_down=False)

    USER32.SendMessageW(edit_hwnd, WM_KEYDOWN, VK_RETURN, down_lparam)
    USER32.SendMessageW(edit_hwnd, WM_CHAR, VK_RETURN, down_lparam)
    USER32.SendMessageW(edit_hwnd, WM_KEYUP, VK_RETURN, up_lparam)


def send_message_to_chatrooms(
    *,
    message: Optional[str] = None,
    message_factory: Optional[Callable[[ChatTarget], str]] = None,
    window_title_filter: Optional[Sequence[str] | Callable[[str], bool]] = None,
    auto_enter: bool = True,
) -> List[ChatTarget]:
    """Write a message to every visible ``RICHEDIT50W`` control found.

    Parameters
    ----------
    message:
        Message that should be written to each chat input. Either ``message``
        or ``message_factory`` must be provided.
    message_factory:
        Callable that receives a :class:`ChatTarget` and returns the message
        that should be sent to that specific chat window.
    window_title_filter:
        Optional filter applied to the top-level window titles. This can be a
        sequence of substrings or a callable that receives the title and
        returns ``True`` when the window should be targeted.
    auto_enter:
        When ``True`` (the default) the function simulates pressing the Enter
        key after the text is updated so that the chat application sends the
        message immediately.

    Returns
    -------
    list[ChatTarget]
        A list describing every chat input that was updated. This is useful
        for logging or for post-processing by the caller.
    """

    _ensure_windows()

    if message is None and message_factory is None:
        raise ValueError("Either 'message' or 'message_factory' must be provided.")

    targets = find_chat_targets(window_title_filter=window_title_filter)

    for target in targets:
        text = message_factory(target) if message_factory else message
        if text is None:
            text = ""
        text = str(text)
        _set_edit_text(target.edit_handle, text)
        if auto_enter:
            _send_enter(target.edit_handle)

    return targets


def _run_cli(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Send text to chat windows using the RICHEDIT50W control.")
    parser.add_argument("message", help="Message to send to each discovered chat window.")
    parser.add_argument(
        "--title-contains",
        action="append",
        dest="title_filters",
        help="Only target top-level windows whose title contains the given substring. Can be used multiple times.",
    )
    parser.add_argument(
        "--no-enter",
        dest="auto_enter",
        action="store_false",
        help="Do not press Enter after updating the text.",
    )
    args = parser.parse_args(argv)

    try:
        targets = send_message_to_chatrooms(
            message=args.message,
            window_title_filter=args.title_filters,
            auto_enter=args.auto_enter,
        )
    except OSError as exc:  # pragma: no cover - executed only on non-Windows
        parser.error(str(exc))
        return 2

    print(f"Updated {len(targets)} chat input control(s).")
    return 0


if __name__ == "__main__":  # pragma: no cover - manual usage helper
    raise SystemExit(_run_cli())
