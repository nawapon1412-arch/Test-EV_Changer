import tinytuya
import time
import csv
import sys
import argparse
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# --- 1. ข้อมูลประจำเครื่อง ---
DEVICE_ID = "a340147c1b6fd42df3wzzn"
LOCAL_KEY = r"`=6Cxm1(CTG1i|?b"
IP_ADDRESS = "192.168.137.18"  # <--- เปลี่ยน IP ได้จาก --ip หรือแก้ตรงนี้

# --- รายชื่อรถและค่า A ที่รองรับ ---
CAR_NAMES = {
    'mg':  'MG ZS EV',
    'rd6': 'RD6 Riddara',
}
VALID_AMPS = [8, 10, 13, 16]
VALID_SOURCES = ['home', 'generator']


def parse_args():
    p = argparse.ArgumentParser(description='EV Charging Data Logger V4.2')
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
    return p.parse_args()


def main():
    args = parse_args()

    ip = args.ip or IP_ADDRESS
    car_label = CAR_NAMES[args.car]
    limit_minutes = args.minutes
    interval = 1

    # --- ตั้งชื่อไฟล์ตามรถ + ค่า A + แหล่งไฟ ---
    filename_prefix = time.strftime('%Y%m%d_%H%M%S')
    file_tag = f"{args.car}_{args.amp}A_{args.source}_{filename_prefix}"
    csv_filename = f"Research_Data_1Hr_{file_tag}.csv"
    graph_filename = f"EV_Research_Graph_1Hr_{file_tag}.png"

    # --- เตรียมตัวแปรเก็บข้อมูล ---
    times_min = []
    powers = []
    temps = []
    energies = []
    currents = []
    voltages = []
    calculated_energy_kwh = 0.0

    d = tinytuya.OutletDevice(DEVICE_ID, ip, LOCAL_KEY)
    d.set_version(3.5)
    d.set_socketTimeout(5)

    print(f"--- EV Research V4.2 ---")
    print(f"  Car     : {car_label}")
    print(f"  Current : {args.amp}A")
    print(f"  Source  : {args.source}")
    print(f"  IP      : {ip}")
    print(f"  Start   : {time.strftime('%H:%M:%S')}")
    print(f"  Duration: {limit_minutes} min | Interval: {interval}s")
    print(f"  CSV     : {csv_filename}")
    print()

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
                    print(f"\n[!] {limit_minutes} min reached. Stopping...")
                    break

                try:
                    data = d.status()
                except Exception as e:
                    print(f"[!] Connection error: {e}. Retrying...")
                    data = None

                if data and 'dps' in data:
                    dps = data['dps']

                    raw_total = dps.get('1', 0) / 100.0
                    current_amp = dps.get('4', 0)
                    temp = dps.get('24', 0)
                    voltage_v = dps.get('20', 2300) / 10.0

                    # Auto-detect: ถ้า current > 100 แสดงว่าเป็น mA ให้แปลงเป็น A
                    if current_amp > 100:
                        current_amp = current_amp / 1000.0

                    if initial_temp is None:
                        initial_temp = temp

                    power_kw = (voltage_v * current_amp) / 1000.0
                    resistance = round((voltage_v / current_amp), 2) if current_amp > 0 else 0.0
                    temp_rise = round(temp - initial_temp, 2)

                    calculated_energy_kwh += power_kw * (dt_seconds / 3600.0)

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

                    print(f"Progress: {elapsed_min:.1f}/{limit_minutes}m | {voltage_v}V | {current_amp}A | {power_kw:.2f}kW | Temp: {temp}C (+{temp_rise}) | Energy: {calculated_energy_kwh:.3f} kWh")
                else:
                    print("Connecting to charger... (Check IP and close Smart Life app)")

                time.sleep(interval)

        # --- วาดกราฟ ---
        if not times_min:
            print("[!] No data collected. Skipping graph generation.")
            sys.exit(0)

        print("\n--- Generating Research Graphs ---")

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
        print(f"SUCCESS: Graph saved as {graph_filename}")

    except KeyboardInterrupt:
        print("\n[!] Experiment stopped manually. Check CSV for partial data.")


if __name__ == '__main__':
    main()
