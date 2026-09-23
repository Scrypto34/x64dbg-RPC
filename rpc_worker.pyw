import ctypes
import ctypes.wintypes as wt
import json
import logging
import os
import re
import sys
import time

import psutil
from pypresence import Presence

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
LOG_PATH = os.path.join(BASE_DIR, "rpc_worker.log")

POLL_SECONDS = 5
UPDATE_SECONDS = 5

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


def acquire_single_instance():
    handle = kernel32.CreateMutexW(None, False, "Local\\x64dbgDiscordRPC")
    if kernel32.GetLastError() == 183:
        sys.exit(0)
    return handle


def find_debugger():
    for proc in psutil.process_iter(["name", "pid", "create_time"]):
        name = (proc.info["name"] or "").lower()
        if name in ("x64dbg.exe", "x32dbg.exe"):
            return proc
    return None


def window_titles(pid):
    titles = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def callback(hwnd, _):
        owner = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                titles.append(buf.value)
        return True

    user32.EnumWindows(callback, 0)
    return titles


def debug_target(pid):
    for title in window_titles(pid):
        match = re.search(r"File:\s*(.+?)\s+-\s+PID", title)
        if match:
            return match.group(1)
        if " - PID:" in title:
            return title.split(" - PID:")[0].strip()
    return None


def format_elapsed(seconds):
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m {seconds}s"


def load_client_id():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return str(json.load(f)["client_id"])


def main():
    _mutex = acquire_single_instance()
    client_id = load_client_id()
    rpc = None
    last_update = 0.0
    last_target = object()

    logging.info("Worker started")
    while True:
        try:
            proc = find_debugger()
            if proc is None:
                if rpc is not None:
                    rpc.close()
                    rpc = None
                    logging.info("x64dbg closed, presence cleared")
                time.sleep(POLL_SECONDS)
                continue

            if rpc is None:
                rpc = Presence(client_id)
                rpc.connect()
                last_update = 0.0
                logging.info("Connected to Discord")

            target = debug_target(proc.info["pid"])
            now = time.time()
            if target != last_target or now - last_update >= UPDATE_SECONDS:
                started = proc.info["create_time"]
                rpc.update(
                    details=f"Debugging {target}" if target else "Debugging nothing yet",
                    state=f"Time Spent: {format_elapsed(now - started)}",
                    large_image="x64dbg",
                    large_text=proc.info["name"],
                    start=int(started),
                )
                last_target = target
                last_update = now
        except Exception as exc:
            logging.warning("Loop error: %r", exc)
            try:
                if rpc is not None:
                    rpc.close()
            except Exception:
                pass
            rpc = None
            time.sleep(POLL_SECONDS * 2)
            continue

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
