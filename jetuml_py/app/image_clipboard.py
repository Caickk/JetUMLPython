"""Copiar uma imagem para a área de transferência do sistema (RF05).

Windows: formato CF_DIB via ctypes (cola em Word, PowerPoint, Paint...). Linux: wl-copy ou xclip. macOS: osascript.
"""
from __future__ import annotations

import io
import os
import shutil
import subprocess
import sys
import tempfile
import time


class ClipboardUnavailable(Exception):
    pass


def image_to_dib(image) -> bytes:
    """Bitmap sem o cabeçalho de arquivo (14 bytes): é o que o formato CF_DIB espera."""
    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="BMP")
    return buf.getvalue()[14:]


def image_to_png(image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def _copy_windows(dib: bytes) -> None:
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GlobalAlloc.argtypes, kernel32.GlobalAlloc.restype = [wintypes.UINT, ctypes.c_size_t], wintypes.HGLOBAL
    kernel32.GlobalLock.argtypes, kernel32.GlobalLock.restype = [wintypes.HGLOBAL], wintypes.LPVOID
    kernel32.GlobalUnlock.argtypes, kernel32.GlobalUnlock.restype = [wintypes.HGLOBAL], wintypes.BOOL
    kernel32.GlobalFree.argtypes, kernel32.GlobalFree.restype = [wintypes.HGLOBAL], wintypes.HGLOBAL
    user32.OpenClipboard.argtypes, user32.OpenClipboard.restype = [wintypes.HWND], wintypes.BOOL
    user32.EmptyClipboard.restype = wintypes.BOOL
    user32.SetClipboardData.argtypes, user32.SetClipboardData.restype = [wintypes.UINT, wintypes.HANDLE], wintypes.HANDLE
    user32.CloseClipboard.restype = wintypes.BOOL
    GMEM_MOVEABLE, CF_DIB = 0x0002, 8
    handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(dib))
    if not handle:
        raise ClipboardUnavailable("Out of memory while copying the image")
    ptr = kernel32.GlobalLock(handle)
    ctypes.memmove(ptr, dib, len(dib))
    kernel32.GlobalUnlock(handle)
    for _ in range(10):                      # a área de transferência pode estar ocupada por outro programa
        if user32.OpenClipboard(None):
            break
        time.sleep(0.05)
    else:
        kernel32.GlobalFree(handle)
        raise ClipboardUnavailable("The clipboard is busy; try again")
    try:
        user32.EmptyClipboard()
        if not user32.SetClipboardData(CF_DIB, handle):
            kernel32.GlobalFree(handle)
            raise ClipboardUnavailable("Could not place the image on the clipboard")
        # após SetClipboardData o sistema é o dono da memória
    finally:
        user32.CloseClipboard()


def _copy_with_command(png: bytes) -> None:
    for command in (["wl-copy", "--type", "image/png"], ["xclip", "-selection", "clipboard", "-t", "image/png", "-i"]):
        if shutil.which(command[0]):
            proc = subprocess.run(command, input=png, capture_output=True, timeout=10)
            if proc.returncode != 0:
                raise ClipboardUnavailable(f"{command[0]} failed: {proc.stderr.decode(errors='replace').strip()}")
            return
    raise ClipboardUnavailable("No clipboard tool found (install xclip or wl-clipboard)")


def _copy_macos(png: bytes) -> None:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(png)
        name = f.name
    try:
        script = f'set the clipboard to (read (POSIX file "{name}") as «class PNGf»)'
        proc = subprocess.run(["osascript", "-e", script], capture_output=True, timeout=10)
        if proc.returncode != 0:
            raise ClipboardUnavailable("osascript could not copy the image")
    finally:
        os.unlink(name)


def copy_image(image) -> None:
    if sys.platform == "win32":
        _copy_windows(image_to_dib(image))
    elif sys.platform == "darwin":
        _copy_macos(image_to_png(image))
    else:
        _copy_with_command(image_to_png(image))
