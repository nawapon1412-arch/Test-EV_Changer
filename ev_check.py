import tinytuya
import time
import sys

# แก้ปัญหาภาษาไทยใน Windows Terminal (cp1252)
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# --- ดึงข้อมูลประจำเครื่องจาก ev_logger (เพื่อเช็คค่าเดียวกัน) ---
DEVICE_ID  = "a340147c1b6fd42df3wzzn"
LOCAL_KEY  = r"`=6Cxm1(CTG1i|?b"
IP_ADDRESS = "192.168.137.18"


def section(title):
    print("\n" + "=" * 55)
    print(f"  {title}")
    print("=" * 55)


def check_pass(msg):
    print(f"  [OK]   {msg}")


def check_fail(msg):
    print(f"  [X]    {msg}")


def check_warn(msg):
    print(f"  [!]    {msg}")


def main():
    all_ok = True

    section("EV Logger - Pre-flight Check")
    print(f"  Target Device ID : {DEVICE_ID}")
    print(f"  Target IP        : {IP_ADDRESS}")
    print(f"  Local Key        : {LOCAL_KEY[:4]}{'*' * (len(LOCAL_KEY) - 4)}")

    # ----------------------------------------------------------
    # 1. สแกนหาอุปกรณ์ Tuya ในเครือข่าย
    # ----------------------------------------------------------
    section("1. Scanning local network for Tuya devices...")

    try:
        devices = tinytuya.deviceScan()
    except Exception as e:
        check_fail(f"Scan failed: {e}")
        sys.exit(1)

    if not devices:
        check_fail("No Tuya devices found on this network.")
        check_warn(" -> ตรวจสอบว่าคอมพิวเตอร์และเครื่องชาร์จอยู่ WiFi เดียวกัน")
        check_warn(" -> ตรวจสอบว่าเครื่องชาร์จเปิดอยู่และเสียบปลั๊ก")
        sys.exit(1)

    print(f"  Found {len(devices)} device(s) on network:")
    for ip, info in devices.items():
        print(f"    - {ip}  (ID: {info.get('gwId', '?')})")

    # ----------------------------------------------------------
    # 2. เช็คว่ามีอุปกรณ์ที่ IP ที่ตั้งค่าไว้ไหม
    # ----------------------------------------------------------
    section(f"2. Checking IP address: {IP_ADDRESS}")

    if IP_ADDRESS not in devices:
        check_fail(f"No device found at {IP_ADDRESS}")
        check_warn(" -> IP อาจเปลี่ยนไปแล้ว กรุณาตรวจสอบ IP ล่าสุดจาก:")
        check_warn("    แอป Smart Life > เครื่องชาร์จ > ตั้งค่า > Device Info")
        check_warn(" -> หรือดูจากรายการสแกนด้านบน แล้วแก้ IP_ADDRESS ในไฟล์")
        check_warn(f"    อุปกรณ์ที่เจอทั้งหมด: {', '.join(devices.keys())}")
        all_ok = False
    else:
        check_pass(f"Device found at {IP_ADDRESS}")

    # ----------------------------------------------------------
    # 3. เช็คว่า Device ID ตรงกันไหม
    # ----------------------------------------------------------
    section("3. Checking Device ID match...")

    actual_id = devices.get(IP_ADDRESS, {}).get("gwId", "")

    if not actual_id:
        check_warn("Could not read Device ID from scanned device.")
    elif actual_id == DEVICE_ID:
        check_pass("Device ID matches!")
    else:
        check_fail("Device ID does NOT match!")
        check_warn(f"     ในสคริปต์: {DEVICE_ID}")
        check_warn(f"     อุปกรณ์จริง: {actual_id}")
        check_warn(" -> อุปกรณ์อาจถูกรีเซ็ตหรือเปลี่ยนตัวใหม่")
        check_warn(" -> ดึง Device ID และ Local Key ใหม่ด้วยคำสั่ง:  python -m tinytuya wizard")
        all_ok = False

    # ----------------------------------------------------------
    # 4. ทดสอบเชื่อมต่อจริง (เช็ค Local Key)
    # ----------------------------------------------------------
    section("4. Testing live connection (Device ID + Local Key)...")

    try:
        d = tinytuya.OutletDevice(DEVICE_ID, IP_ADDRESS, LOCAL_KEY)
        d.set_version(3.5)
        d.set_socketTimeout(5)
        data = d.status()

        if data and "dps" in data:
            check_pass("Connection successful! Data received.")
            dps = data["dps"]
            print(f"     Voltage : {dps.get('20', 0) / 10.0} V")
            print(f"     Current : {dps.get('4', 0)} A")
            print(f"     Temp    : {dps.get('24', 0)} C")
        else:
            check_fail("Connected but no DPS data returned.")
            check_warn(" -> Local Key อาจไม่ถูกต้อง หรืออุปกรณ์ไม่ตอบสนอง")
            check_warn(" -> ตรวจสอบว่าปิดแอป Smart Life บนมือถือแล้ว")
            all_ok = False
    except Exception as e:
        check_fail(f"Connection failed: {e}")
        check_warn(" -> Local Key อาจผิด หรือแอป Smart Life เปิดอยู่")
        check_warn(" -> ลองดึงค่าใหม่ด้วย:  python -m tinytuya wizard")
        all_ok = False

    # ----------------------------------------------------------
    # สรุปผล
    # ----------------------------------------------------------
    section("SUMMARY")

    if all_ok:
        check_pass("All checks passed! Ready to run ev_logger.py")
        print("\n  >> รันได้เลย:  python ev_logger.py\n")
    else:
        check_fail("Some checks failed. Please fix the issues above before running.")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
