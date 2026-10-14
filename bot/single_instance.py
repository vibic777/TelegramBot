import hashlib
import os
import sys
from pathlib import Path

ALREADY_RUNNING_EXIT_CODE = 3


class AlreadyRunning(RuntimeError):
    pass


class SingleInstance:
    """Holds a system-wide lock so only one bot per project folder runs at a time.

    On Windows this is a named mutex, on other systems an flock'ed file. Both are
    released by the OS when the process exits, even after a crash or a kill.
    """

    def __init__(self, project_root: Path) -> None:
        root = str(project_root.resolve()).lower()
        self._key = hashlib.sha256(root.encode("utf-8")).hexdigest()[:16]
        self._lock_path = project_root / "data" / "bot.lock"
        self._handle = None

    def acquire(self) -> None:
        if sys.platform == "win32":
            self._acquire_windows()
        else:
            self._acquire_posix()

    def release(self) -> None:
        if self._handle is None:
            return
        if sys.platform == "win32":
            import ctypes

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.ReleaseMutex(self._handle)
            kernel32.CloseHandle(self._handle)
        else:
            self._handle.close()
        self._handle = None

    def __enter__(self) -> "SingleInstance":
        self.acquire()
        return self

    def __exit__(self, *exc_info) -> None:
        self.release()

    def _acquire_windows(self) -> None:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.WaitForSingleObject.restype = wintypes.DWORD
        kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel32.ReleaseMutex.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

        handle = kernel32.CreateMutexW(None, False, f"Local\\TelegramBot-{self._key}")
        if not handle:
            raise OSError(ctypes.get_last_error(), "CreateMutexW failed")
        wait_object_0, wait_abandoned = 0x0, 0x80
        result = kernel32.WaitForSingleObject(handle, 0)
        if result not in (wait_object_0, wait_abandoned):
            kernel32.CloseHandle(handle)
            raise AlreadyRunning
        self._handle = handle

    def _acquire_posix(self) -> None:
        import fcntl

        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = open(self._lock_path, "a+")
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            handle.close()
            raise AlreadyRunning from None
        handle.seek(0)
        handle.truncate()
        handle.write(str(os.getpid()))
        handle.flush()
        self._handle = handle
