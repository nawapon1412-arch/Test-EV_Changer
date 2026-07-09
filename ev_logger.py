import tinytuya
import time
import csv
import sys
import os
import argparse
import traceback
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# --- 1. ข้อมูลประจำเครื่อง ---
DEVICE_ID = "a340147c1b6fd42df3wzzn"
LOCAL_KEY = r"`=6Cxm1(CTG1i|?b"
IP_ADDRESS = "192.168.137.18"

# --- รายชื่อรถและค่า A ที่รองรับ ---
CAR_NAMES = {
    'mg':  'MG ZS EV',
    'rd6': 'RD6 Riddara',
}
VALID_AMPS = [8, 10, 13, 16]
VALID_SOURCES = ['home', 'generator']

# --- ค่าขอบเขตสำหรับตรวจสอบความผิดปกติ ---
SANITY_CHECKS = {
    'voltage_min': 200.0, 'voltage_max': 250.0,
    'current_min': 0.0,   'current_max': 32.0,
    'temp_min': 0.0,      'temp_max': 90.0,
    'power_max': 10.0,
}

# ANSI colors
def c_ok(msg):   return f"\033[92m{msg}\033[0m"
def c_warn(msg): return f"\033[93m{msg}\033[0m"
def c_err(msg):  return f"\033[91m{msg}\033[0m"
def c_info(msg): return f"\033[96m{msg}\033[0m"
def c_bold(msg): return f"\033[1m{msg}\033[0m"


def parse_args():
    p = argparse.ArgumentParser(
        description='EV Charging Data Logger V4.3 (Self-Debug Edition)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
ตัวอย่างการใช้งาน:

  Pre-flight check (แนะนำให้รันก่อนทุกครั้ง):
    python ev_logger.py --car mg --amp 10 --source generator --check

  เริ่มเก็บข้อมูลจริง 1 ชั่วโมง:
    python ev_logger.py --car mg --amp 10 --source generator --ip 192.168.137.18

  ทดสอบ 1 นาทีก่อน:
    python ev_logger.py --car mg --amp 10 --source generator --minutes 1
        """)
    p.add_argument('--car', required=True, choices=CAR_NAMES.keys(),
                   help='รุ่นรถ: mg (MG ZS EV) หรือ rd6 (RD6 Riddara)')
    p.add_argument('--amp', required=True, type=int, choices=VALID_AMPS,
                   help='ค่ากระแส: 8, 10, 13, 16')
    p.add_argument('--source', required=True, choices=VALID_SOURCES,
                   help='แหล่งไฟ: home หรือ generator')
    p.add_argument('--ip', default=None,
                   help='Override IP address (เช่น 192.168.137.18)')
    p.add_argument('--minutes', type=int, default=60,
                   help='ระยะเวลาเก็บข้อมูล (นาที) default=60')
    p.add_argument('--check', action='store_true',
                   help='รัน pre-flight diagnostic เท่านั้น (ไม่เก็บข้อมูล)')
    p.add_argument('--debug', action='store_true',
                   help='แสดง raw DPS ทุกรอบ (verbose)')
    return p.parse_args()


# ============================================================
#  PRE-FLIGHT CHECK
# ============================================================
def preflight_check(device_id, local_key, ip):
    print(c_bold("\n" + "=" * 60))
    print(c_bold("  PRE-FLIGHT DIAGNOSTIC"))
    print(c_bold("=" * 60))

    all_ok = True

    # --- 1. เช็ค tinytuya ---
    print(c_info("\n[1] Checking tinytuya..."))
    try:
        ver = tinytuya.__version__
        print(c_ok(f"    OK - tinytuya v{ver}"))
    except Exception:
        print(c_err("    FAIL - tinytuya not installed"))
        print(c_warn("    Fix: pip install tinytuya"))
        return False

    # --- 2. สแกนเครือข่าย ---
    print(c_info("\n[2] Scanning local network for Tuya devices..."))
    try:
        devices = tinytuya.deviceScan()
    except Exception as e:
        print(c_err(f"    FAIL - Scan error: {e}"))
        return False

    if not devices:
        print(c_err("    FAIL - No Tuya devices found"))
        print(c_warn("    -> คอมพิวเตอร์และเครื่องชาร์จต้องอยู่ WiFi เดียวกัน"))
        print(c_warn("    -> เครื่องชาร์จต้องเปิดและเสียบปลั๊ก"))
        return False

    print(c_ok(f"    Found {len(devices)} device(s):"))
    for found_ip, info in devices.items():
        marker = " <--- TARGET" if found_ip == ip else ""
        print(f"      {found_ip}  (ID: {info.get('gwId', '?')}){marker}")

    if ip not in devices:
        print(c_err(f"\n    FAIL - Target IP '{ip}' not found in scan results"))
        print(c_warn("    -> IP เปลี่ยนไปแล้ว! ลอง IP เหล่านี้แทน:"))
        for found_ip in devices.keys():
            print(c_warn(f"       --ip {found_ip}"))
        all_ok = False
    else:
        print(c_ok(f"    OK - Device found at {ip}"))

    # --- 3. เช็ค Device ID ---
    print(c_info("\n[3] Checking Device ID..."))
    actual_id = devices.get(ip, {}).get("gwId", "")
    if actual_id == device_id:
        print(c_ok(f"    OK - ID matches ({device_id})"))
    elif actual_id:
        print(c_err(f"    FAIL - ID mismatch!"))
        print(c_warn(f"    Script : {device_id}"))
        print(c_warn(f"    Device : {actual_id}"))
        print(c_warn("    -> อุปกรณ์อาจถูกรีเซ็ต ดึงค่าใหม่: python -m tinytuya wizard"))
        all_ok = False
    else:
        print(c_warn("    WARN - Could not verify Device ID"))

    # --- 4. ทดสอบเชื่อมต่อ + อ่าน DPS ---
    print(c_info("\n[4] Testing live connection + reading DPS..."))
    try:
        d = tinytuya.OutletDevice(device_id, ip, local_key)
        d.set_version(3.5)
        d.set_socketTimeout(5)
        data = d.status()
    except Exception as e:
        print(c_err(f"    FAIL - Connection error: {e}"))
        print(c_warn("    -> Local Key อาจผิด หรือแอป Smart Life เปิดอยู่ (ปิดแอปก่อน)"))
        print(c_warn("    -> ดึงค่าใหม่: python -m tinytuya wizard"))
        return False

    if not data or 'dps' not in data:
        print(c_err("    FAIL - No DPS data returned"))
        print(c_warn("    -> ปิดแอป Smart Life บนมือถือแล้วลองใหม่"))
        return False

    dps = data['dps']
    print(c_ok("    OK - Connection successful!\n"))

    # --- 5. Dump DPS ทั้งหมด + ตรวจสอบ mapping ---
    print(c_bold("[5] Raw DPS Dump (ทุกค่าที่อุปกรณ์ส่งกลับ):"))
    print("    " + "-" * 50)
    for key in sorted(dps.keys(), key=lambda x: (len(x), x)):
        val = dps[key]
        val_str = str(val)
        if len(val_str) > 60:
            val_str = val_str[:60] + "..."
        print(f"    DPS[{key:>4}] = {val_str}")
    print("    " + "-" * 50)

    # --- 6. ตรวจสอบ DPS ที่ใช้ ---
    print(c_bold("\n[6] DPS Mapping Check:"))
    checks = [
        ('1',  'Energy (raw)',    True),
        ('4',  'Current',         True),
        ('20', 'Voltage (raw)',   False),
        ('24', 'Temperature',     False),
    ]
    for dps_key, label, required in checks:
        if dps_key in dps:
            raw = dps[dps_key]
            if dps_key == '4' and isinstance(raw, (int, float)) and raw > 100:
                converted = raw / 1000.0
                print(c_warn(f"    DPS[{dps_key:>2}] {label}: {raw} -> detected mA, converted = {converted} A"))
            elif dps_key == '20':
                print(c_ok(f"    DPS[{dps_key:>2}] {label}: {raw} -> {raw / 10.0} V"))
            elif dps_key == '1':
                print(c_ok(f"    DPS[{dps_key:>2}] {label}: {raw} -> {raw / 100.0} kWh"))
            else:
                print(c_ok(f"    DPS[{dps_key:>2}] {label}: {raw}"))
        else:
            tag = c_err("MISSING") if required else c_warn("optional, using default")
            print(f"    DPS[{dps_key:>2}] {label}: {tag}")

    # --- 7. คำนวณค่าที่จะใช้ ---
    print(c_bold("\n[7] Computed Values:"))
    raw_total = dps.get('1', 0) / 100.0
    current_amp = dps.get('4', 0)
    if current_amp > 100:
        current_amp = current_amp / 1000.0
    temp = dps.get('24', 0)
    voltage_v = dps.get('20', 2300) / 10.0 if '20' in dps else 230.0
    power_kw = (voltage_v * current_amp) / 1000.0
    resistance = round(voltage_v / current_amp, 2) if current_amp > 0 else 0.0

    print(f"    Voltage    = {voltage_v} V")
    print(f"    Current    = {current_amp} A")
    print(f"    Power      = {power_kw:.3f} kW")
    print(f"    Resistance = {resistance} Ohm")
    print(f"    Temp       = {temp} C")
    print(f"    Energy(raw)= {raw_total} kWh")

    # --- 8. Sanity check ---
    print(c_bold("\n[8] Sanity Check:"))
    issues = []
    if not (SANITY_CHECKS['voltage_min'] <= voltage_v <= SANITY_CHECKS['voltage_max']):
        issues.append(f"Voltage {voltage_v}V ผิดปกติ (ควรอยู่ในช่วง {SANITY_CHECKS['voltage_min']}-{SANITY_CHECKS['voltage_max']}V)")
    if not (SANITY_CHECKS['current_min'] <= current_amp <= SANITY_CHECKS['current_max']):
        issues.append(f"Current {current_amp}A ผิดปกติ (ควรอยู่ในช่วง {SANITY_CHECKS['current_min']}-{SANITY_CHECKS['current_max']}A)")
    if not (SANITY_CHECKS['temp_min'] <= temp <= SANITY_CHECKS['temp_max']):
        issues.append(f"Temp {temp}C ผิดปกติ (ควรอยู่ในช่วง {SANITY_CHECKS['temp_min']}-{SANITY_CHECKS['temp_max']}C)")
    if power_kw > SANITY_CHECKS['power_max']:
        issues.append(f"Power {power_kw}kW สูงผิดปกติ (ควร < {SANITY_CHECKS['power_max']}kW)")
    if current_amp == 0:
        issues.append("Current = 0A เครื่องชาร์จอาจยังไม่เริ่มชาร์จ หรือสายไม่เสียบ")

    if issues:
        for issue in issues:
            print(c_warn(f"    [!] {issue}"))
        print(c_warn("\n    ค่าบางอย่างผิดปกติ แต่สามารถรันต่อได้ (ข้อมูลจะถูกบันทึกตามจริง)"))
    else:
        print(c_ok("    All values look normal!"))

    # --- สรุป ---
    print(c_bold("\n" + "=" * 60))
    if all_ok:
        print(c_ok("  ALL CHECKS PASSED - Ready to run!"))
        print(c_bold(f"\n  รันเก็บข้อมูลจริง:\n"))
        print(f"    python ev_logger.py --car {{car}} --amp {{A}} --source {{source}} --ip {ip}\n")
    else:
        print(c_err("  SOME CHECKS FAILED - แก้ปัญหาก่อนรัน"))
    print("=" * 60)

    return all_ok


# ============================================================
#  MAIN LOGGING LOOP
# ============================================================
def main():
    args = parse_args()

    ip = args.ip or IP_ADDRESS
    car_label = CAR_NAMES[args.car]
    limit_minutes = args.minutes
    interval = 1

    # --- ถ้า --check รัน pre-flight แล้วออก ---
    if args.check:
        preflight_check(DEVICE_ID, LOCAL_KEY, ip)
        return

    # --- ตั้งชื่อไฟล์ ---
    filename_prefix = time.strftime('%Y%m%d_%H%M%S')
    file_tag = f"{args.car}_{args.amp}A_{args.source}_{filename_prefix}"
    csv_filename = f"Research_Data_1Hr_{file_tag}.csv"
    graph_filename = f"EV_Research_Graph_1Hr_{file_tag}.png"
    log_filename = f"debug_{file_tag}.log"

    # --- เตรียมตัวแปร ---
    times_min = []
    powers = []
    temps = []
    energies = []
    currents = []
    voltages = []
    calculated_energy_kwh = 0.0

    # --- สถิติการทำงาน ---
    stats = {
        'total_reads': 0,
        'success_reads': 0,
        'error_reads': 0,
        'consecutive_errors': 0,
        'max_consecutive_errors': 0,
        'warnings': [],
        'first_dps_dumped': False,
    }

    def log(msg, level='INFO'):
        line = f"[{time.strftime('%H:%M:%S')}] [{level}] {msg}"
        print(line)
        try:
            with open(log_filename, 'a', encoding='utf-8') as lf:
                lf.write(line + '\n')
        except Exception:
            pass

    # --- สร้าง device ---
    d = tinytuya.OutletDevice(DEVICE_ID, ip, LOCAL_KEY)
    d.set_version(3.5)
    d.set_socketTimeout(5)

    print(c_bold(f"\n{'=' * 60}"))
    print(c_bold(f"  EV Research V4.3 - Self-Debug Edition"))
    print(c_bold(f"{'=' * 60}"))
    print(f"  Car       : {car_label}")
    print(f"  Current   : {args.amp}A")
    print(f"  Source    : {args.source}")
    print(f"  IP        : {ip}")
    print(f"  Start     : {time.strftime('%H:%M:%S')}")
    print(f"  Duration  : {limit_minutes} min | Interval: {interval}s")
    print(f"  CSV       : {csv_filename}")
    print(f"  Debug log : {log_filename}")
    print(c_bold(f"{'=' * 60}\n"))

    start_timestamp = time.time()
    last_loop_time = start_timestamp
    initial_temp = None

    try:
        with open(csv_filename, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([
                'Time_Min', 'Voltage(V)', 'Current(A)', 'Resistance(Ohm)',
                'Power(kW)', 'Temp(C)', 'Temp_Rise(C)',
                'Calculated_Energy(kWh)', 'Tuya_Raw_Energy(kWh)'
            ])

            while True:
                current_time = time.time()
                elapsed_sec = current_time - start_timestamp
                elapsed_min = elapsed_sec / 60.0

                dt_seconds = current_time - last_loop_time
                last_loop_time = current_time

                if elapsed_min > limit_minutes:
                    log(f"Time limit reached ({limit_minutes} min). Stopping.", 'DONE')
                    break

                stats['total_reads'] += 1

                # --- อ่านข้อมูลจากอุปกรณ์ ---
                try:
                    data = d.status()
                except Exception as e:
                    stats['error_reads'] += 1
                    stats['consecutive_errors'] += 1
                    stats['max_consecutive_errors'] = max(
                        stats['max_consecutive_errors'],
                        stats['consecutive_errors']
                    )
                    log(f"Connection error #{stats['error_reads']}: {e}", 'ERROR')

                    if stats['consecutive_errors'] >= 5:
                        log("5 consecutive errors! ตรวจสอบ:", 'WARN')
                        log("  1. คอมและเครื่องชาร์จอยู่ WiFi เดียวกัน?", 'WARN')
                        log("  2. ปิดแอป Smart Life แล้ว?", 'WARN')
                        log("  3. IP เปลี่ยน? รัน --check เพื่อสแกนใหม่", 'WARN')
                        log("  (จะลองต่อไป... ข้อมูลจะไม่หาย)", 'WARN')

                    data = None
                    time.sleep(interval)
                    continue

                if not data or 'dps' not in data:
                    stats['error_reads'] += 1
                    stats['consecutive_errors'] += 1
                    log(f"No DPS data (attempt #{stats['error_reads']})", 'WARN')
                    time.sleep(interval)
                    continue

                # --- ติดต่อสำเร็จ ---
                stats['consecutive_errors'] = 0
                stats['success_reads'] += 1
                dps = data['dps']

                # --- Dump DPS ครั้งแรก ---
                if not stats['first_dps_dumped']:
                    stats['first_dps_dumped'] = True
                    log("First successful DPS dump:", 'INFO')
                    for k in sorted(dps.keys(), key=lambda x: (len(x), x)):
                        log(f"  DPS[{k}] = {dps[k]}", 'INFO')

                # --- Debug mode: แสดง raw DPS ทุกรอบ ---
                if args.debug:
                    log(f"Raw DPS: {dps}", 'DEBUG')

                # --- อ่านค่า + auto-detect หน่วย ---
                raw_total = dps.get('1', 0) / 100.0
                current_amp = dps.get('4', 0)
                temp = dps.get('24', 0)
                voltage_v = dps.get('20', 2300) / 10.0 if '20' in dps else 230.0

                unit_note = ""
                if current_amp > 100:
                    unit_note = " (mA->A)"
                    current_amp = current_amp / 1000.0

                # --- ตรวจสอบค่าผิดปกติ ---
                if voltage_v == 230.0 and '20' not in dps:
                    msg = f"DPS['20'] (Voltage) หาย! ใช้ค่า default 230V"
                    if msg not in stats['warnings']:
                        stats['warnings'].append(msg)
                        log(msg, 'WARN')

                if current_amp == 0:
                    msg = "Current = 0A เครื่องชาร์จอาจยังไม่ชาร์จ"
                    if msg not in stats['warnings']:
                        stats['warnings'].append(msg)
                        log(msg, 'WARN')

                if power_kw_check := (voltage_v * current_amp) / 1000.0:
                    if power_kw_check > SANITY_CHECKS['power_max']:
                        msg = f"Power {power_kw_check:.2f}kW สูงผิดปกติ! (V={voltage_v}, A={current_amp})"
                        if msg not in stats['warnings']:
                            stats['warnings'].append(msg)
                            log(msg, 'WARN')

                # --- คำนวณ ---
                if initial_temp is None:
                    initial_temp = temp
                    log(f"Initial temperature set: {temp}C", 'INFO')

                power_kw = (voltage_v * current_amp) / 1000.0
                resistance = round((voltage_v / current_amp), 2) if current_amp > 0 else 0.0
                temp_rise = round(temp - initial_temp, 2)

                calculated_energy_kwh += power_kw * (dt_seconds / 3600.0)

                # --- เก็บข้อมูล ---
                times_min.append(elapsed_min)
                powers.append(power_kw)
                temps.append(temp)
                energies.append(calculated_energy_kwh)
                currents.append(current_amp)
                voltages.append(voltage_v)

                writer.writerow([
                    round(elapsed_min, 2),
                    voltage_v,
                    current_amp,
                    resistance,
                    round(power_kw, 3),
                    temp,
                    temp_rise,
                    round(calculated_energy_kwh, 4),
                    raw_total
                ])
                file.flush()

                # --- แสดงสถานะ ---
                err_rate = (stats['error_reads'] / stats['total_reads']) * 100 if stats['total_reads'] > 0 else 0
                status = f"Progress: {elapsed_min:.1f}/{limit_minutes}m | {voltage_v}V | {current_amp}A{unit_note} | {power_kw:.2f}kW | Temp: {temp}C (+{temp_rise}) | Energy: {calculated_energy_kwh:.3f} kWh"
                if stats['error_reads'] > 0:
                    status += f" | ERR: {stats['error_reads']} ({err_rate:.0f}%)"
                print(status)

                time.sleep(interval)

        # ============================================================
        #  วาดกราฟ
        # ============================================================
        if not times_min:
            log("No data collected. Skipping graph.", 'WARN')
            _print_summary(stats, csv_filename, log_filename)
            sys.exit(0)

        print(c_info("\n--- Generating Research Graphs ---"))

        step = 10
        t = times_min[::step]
        p = powers[::step]
        tp = temps[::step]
        e = energies[::step]
        c = currents[::step]
        v = voltages[::step]

        fig, (ax1, ax3) = plt.subplots(2, 1, figsize=(11, 8), sharex=True)

        color1 = 'tab:blue'
        ax1.set_ylabel('Power (kW)', color=color1, fontweight='bold')
        ax1.plot(t, p, color=color1, linewidth=2, label='Power (kW)')
        ax1.tick_params(axis='y', labelcolor=color1)
        ax1.grid(True, linestyle=':', alpha=0.6)

        ax2 = ax1.twinx()
        color2 = 'tab:red'
        ax2.set_ylabel('Temperature (C)', color=color2, fontweight='bold')
        ax2.plot(t, tp, color=color2, linestyle='--', linewidth=2, label='Temperature (C)')
        ax2.tick_params(axis='y', labelcolor=color2)
        ax1.set_title(f'{car_label} - {args.amp}A - {args.source}\n'
                      f'Energy: {energies[-1]:.4f} kWh | Temp Rise: +{max(temps)-initial_temp:.1f}C')

        color3 = 'tab:green'
        ax3.set_xlabel('Time (Minutes)', fontweight='bold')
        ax3.set_ylabel('Voltage (V)', color=color3, fontweight='bold')
        ax3.plot(t, v, color=color3, linewidth=2, label='Voltage (V)')
        ax3.tick_params(axis='y', labelcolor=color3)
        ax3.grid(True, linestyle=':', alpha=0.6)

        ax4 = ax3.twinx()
        color4 = 'tab:purple'
        ax4.set_ylabel('Current (A)', color=color4, fontweight='bold')
        ax4.plot(t, c, color=color4, linestyle='-.', linewidth=2, label='Current (A)')
        ax4.tick_params(axis='y', labelcolor=color4)

        fig.tight_layout()
        plt.savefig(graph_filename, dpi=300)
        print(c_ok(f"Graph saved: {graph_filename}"))

        # --- สรุปผล ---
        _print_summary(stats, csv_filename, log_filename, graph_filename,
                       times_min, powers, temps, voltages, currents, energies, initial_temp)

    except KeyboardInterrupt:
        print(c_warn("\n[!] Stopped manually (Ctrl+C). CSV has partial data."))
        _print_summary(stats, csv_filename, log_filename)

    except Exception as e:
        print(c_err(f"\n[!] Unexpected error: {e}"))
        traceback.print_exc()
        log(f"CRASH: {e}\n{traceback.format_exc()}", 'CRASH')
        _print_summary(stats, csv_filename, log_filename)


def _print_summary(stats, csv_filename, log_filename, graph_filename=None,
                   times_min=None, powers=None, temps=None, voltages=None,
                   currents=None, energies=None, initial_temp=None):
    print(c_bold(f"\n{'=' * 60}"))
    print(c_bold("  SUMMARY"))
    print(c_bold(f"{'=' * 60}"))

    print(f"  Total attempts : {stats['total_reads']}")
    print(f"  Successful     : {c_ok(str(stats['success_reads']))}")
    print(f"  Errors         : {c_err(str(stats['error_reads']))}" if stats['error_reads'] > 0
          else f"  Errors         : {c_ok('0')}")
    print(f"  Max consec err : {stats['max_consecutive_errors']}")

    if stats['warnings']:
        print(c_warn(f"\n  Warnings ({len(stats['warnings'])}):"))
        for w in stats['warnings']:
            print(c_warn(f"    - {w}"))

    if times_min and len(times_min) > 0:
        duration = times_min[-1]
        print(f"\n  Data points    : {len(times_min)}")
        print(f"  Duration       : {duration:.1f} min")
        if powers:
            print(f"  Power range    : {min(powers):.3f} - {max(powers):.3f} kW")
            print(f"  Avg power      : {sum(powers)/len(powers):.3f} kW")
        if voltages:
            print(f"  Voltage range  : {min(voltages):.1f} - {max(voltages):.1f} V")
        if currents:
            print(f"  Current range  : {min(currents):.2f} - {max(currents):.2f} A")
        if temps and initial_temp is not None:
            print(f"  Temp range     : {min(temps)} - {max(temps)} C (rise: +{max(temps)-initial_temp:.1f})")
        if energies:
            print(f"  Total energy   : {energies[-1]:.4f} kWh")

    print(f"\n  Files:")
    print(f"    CSV  : {csv_filename}")
    if graph_filename:
        print(f"    Graph: {graph_filename}")
    print(f"    Log  : {log_filename}")
    print(c_bold(f"{'=' * 60}\n"))


if __name__ == '__main__':
    main()
