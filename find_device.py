import tinytuya
import sys

sys.stdout.reconfigure(encoding="utf-8")

print("Scanning network (60s, 50 retries)...")
print("Target Device ID: a340147c1b6fd42df3wzzn")
print()

devices = tinytuya.deviceScan(maxretry=50)

print(f"Found {len(devices)} device(s):\n")
for ip, info in devices.items():
    gw = info.get("gwId", "?")
    match = " <--- THIS IS YOUR EV CHARGER!" if gw == "a340147c1b6fd42df3wzzn" else ""
    print(f"  IP: {ip}   Device ID: {gw}{match}")

target = "a340147c1b6fd42df3wzzn"
found = [ip for ip, info in devices.items() if info.get("gwId") == target]
if found:
    print(f"\n>>> EV charger found at: {found[0]}")
else:
    print("\n>>> EV charger (a340147c1b6fd42df3wzzn) NOT found on network!")
    print("    -> It may be OFFLINE or disconnected from WiFi.")
