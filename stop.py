import os

import psutil

STARTUP_SCRIPT = os.path.join(
    os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs",
    "Startup", "x64dbgDiscordRPC.vbs",
)

for proc in psutil.process_iter(["cmdline"]):
    if any(arg.endswith("rpc_worker.pyw") for arg in proc.info["cmdline"] or []):
        proc.kill()

if os.path.exists(STARTUP_SCRIPT):
    os.remove(STARTUP_SCRIPT)

print("x64dbg Discord RPC stopped and removed from startup.")
