import json
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKER = os.path.join(BASE_DIR, "rpc_worker.pyw")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
STARTUP_DIR = os.path.join(
    os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs", "Startup"
)
STARTUP_SCRIPT = os.path.join(STARTUP_DIR, "x64dbgDiscordRPC.vbs")


def ensure_dependencies():
    try:
        import psutil
        import pypresence
    except ImportError:
        print("Installing dependencies...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", "pypresence", "psutil"]
        )


def ensure_client_id():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, encoding="utf-8") as f:
            if json.load(f).get("client_id"):
                return
    print("First-time setup: paste your Discord Application ID")
    print("(see README.md - create an app named 'x64dbg' at discord.com/developers)")
    client_id = ""
    while not client_id.isdigit():
        client_id = input("Application ID: ").strip()
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump({"client_id": client_id}, f, indent=2)


def pythonw_path():
    candidate = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return candidate if os.path.exists(candidate) else sys.executable


def stop_old_workers():
    import psutil

    for proc in psutil.process_iter(["pid", "cmdline"]):
        cmdline = proc.info["cmdline"] or []
        if proc.info["pid"] != os.getpid() and any(
            arg.endswith("rpc_worker.pyw") for arg in cmdline
        ):
            try:
                proc.kill()
                proc.wait(3)
            except Exception:
                pass


def install_startup():
    with open(STARTUP_SCRIPT, "w", encoding="utf-8") as f:
        f.write(
            'CreateObject("WScript.Shell").Run """{}"" ""{}""", 0, False\n'.format(
                pythonw_path(), WORKER
            )
        )


def start_worker():
    flags = (
        subprocess.DETACHED_PROCESS
        | subprocess.CREATE_NEW_PROCESS_GROUP
        | subprocess.CREATE_NO_WINDOW
    )
    args = [pythonw_path(), WORKER]
    try:
        subprocess.Popen(args, cwd=BASE_DIR, creationflags=flags | subprocess.CREATE_BREAKAWAY_FROM_JOB,
                         close_fds=True)
    except OSError:
        subprocess.Popen(args, cwd=BASE_DIR, creationflags=flags, close_fds=True)


def main():
    ensure_dependencies()
    ensure_client_id()
    stop_old_workers()
    install_startup()
    start_worker()
    print()
    print("Done, your Discord RPC is now x64dbg. Open x64dbg for it to start!")
    print()
    print("You can close this window - the RPC keeps running in the background.")
    input("Press Enter to close...")


if __name__ == "__main__":
    main()
