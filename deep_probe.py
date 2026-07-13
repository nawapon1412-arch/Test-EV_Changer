import tinytuya
import socket
import sys
import struct

sys.stdout.reconfigure(encoding="utf-8")

TARGET_IP = "192.168.137.18"
FOUND_ID  = "a30ceb56ee9c2ed183qrqz"
SUBNET    = "192.168.137"

print("=" * 55)
print("  Deep Network Probe")
print("=" * 55)

# -------------------------------------------------------
# 1. Ping check
# -------------------------------------------------------
print(f"\n[1] Pinging {TARGET_IP}...")
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    result = s.connect_ex((TARGET_IP, 6668))  # Tuya local port
    if result == 0:
        print(f"    Port 6668 OPEN - Tuya device is listening!")
    else:
        print(f"    Port 6668 CLOSED/FILTERED (code: {result})")
    s.close()
except Exception as e:
    print(f"    Error: {e}")

# -------------------------------------------------------
# 2. Try reading the found device (a30ceb56...) 
#    WITHOUT key to see what it reports
# -------------------------------------------------------
print(f"\n[2] Probing device {FOUND_ID} at {TARGET_IP} (no key)...")
try:
    d = tinytuya.OutletDevice(FOUND_ID, TARGET_IP, "0000000000000000")
    d.set_version(3.5)
    d.set_socketTimeout(3)
    data = d.status()
    if data and "dps" in data:
        dps = data["dps"]
        print(f"    DPS keys: {list(dps.keys())}")
        print(f"    Full DPS: {dps}")
        print(f"\n    >>> This device reports these DPS values.")
        print(f"    >>> If it shows voltage/current/temp, it IS your charger!")
    else:
        print(f"    Response (no dps): {data}")
except Exception as e:
    print(f"    Error: {e}")

# -------------------------------------------------------
# 3. Scan ALL IPs in subnet for Tuya port 6668
# -------------------------------------------------------
print(f"\n[3] Scanning subnet {SUBNET}.0/24 for Tuya devices (port 6668)...")
print(f"    (This checks every IP from 1-254)...")
found_ips = []
for i in range(1, 255):
    ip = f"{SUBNET}.{i}"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.3)
        if s.connect_ex((ip, 6668)) == 0:
            print(f"    FOUND: {ip} - port 6668 open!")
            found_ips.append(ip)
        s.close()
    except:
        pass

if not found_ips:
    print(f"    No devices with port 6668 found (besides already known).")
elif TARGET_IP not in found_ips:
    print(f"\n    >>> {TARGET_IP} NOT in open-port list!")

# -------------------------------------------------------
# 4. forcescan mode
# -------------------------------------------------------
print(f"\n[4] Running Tuya forcescan...")
try:
    devices = tinytuya.deviceScan(forcescan=True, maxretry=30)
    for ip, info in devices.items():
        gw = info.get("gwId", "?")
        tag = " <--- YOUR EV CHARGER" if gw == "a340147c1b6fd42df3wzzn" else ""
        print(f"    {ip}  ->  {gw}{tag}")
    if not devices:
        print("    No devices found in forcescan.")
except Exception as e:
    print(f"    Error: {e}")

print("\n" + "=" * 55)
print("  Done.")
