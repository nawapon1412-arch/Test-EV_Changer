import tinytuya
import time
import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

DEVICE_ID = "a340147c1b6fd42df3wzzn"
LOCAL_KEY = r"`=6Cxm1(CTG1i|?b"
IP_ADDRESS = "192.168.137.9"

LIMIT_MINUTES = 60
interval = 1

times_min = []
powers = []
temps = []
energies = []
currents = []
voltages = []

calculated_energy_kwh = 0.0

d = tinytuya.OutletDevice(DEVICE_ID, IP_ADDRESS, LOCAL_KEY)
d.set_version(3.5)
d.set_socketTimeout(5)

print(f"--- EV Research V4.1: 1-Hour Automation Mode ---")
print(f"Starting experiment at: {time.strftime('%H:%M:%S')}")
print(f"Sampling interval: Every {interval} second | Duration: {LIMIT_MINUTES} minutes")

start_timestamp = time.time()
last_loop_time = start_timestamp
initial_temp = None

filename_prefix = time.strftime('%Y%m%d_%H%M%S')

try:
    with open(f"Research_Data_1Hr_{filename_prefix}.csv", mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Time_Min', 'Voltage(V)', 'Current(A)', 'Resistance(Ohm)', 'Power(kW)', 'Temp(C)', 'Temp_Rise(C)', 'Calculated_Energy(kWh)', 'Tuya_Raw_Energy(kWh)'])

        while True:
            current_time = time.time()
            elapsed_sec = current_time - start_timestamp
            elapsed_min = elapsed_sec / 60.0

            dt_seconds = current_time - last_loop_time
            last_loop_time = current_time

            if elapsed_min > LIMIT_MINUTES:
                print(f"\n[!] 1 Hour reached ({LIMIT_MINUTES} mins). Stopping and plotting...")
                break

            data = d.status()
            if data and 'dps' in data:
                dps = data['dps']

                raw_total = dps.get('1', 0) / 100.0
                current_amp = dps.get('4', 0)
                temp = dps.get('24', 0)
                voltage_v = dps.get('20', 2300) / 10.0 if '20' in dps else 230.0

                if initial_temp is None:
                    initial_temp = temp

                power_kw = (voltage_v * current_amp) / 1000.0
                resistance = round((voltage_v / current_amp), 2) if current_amp > 0 else 0.0
                temp_rise = temp - initial_temp

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

                print(f"Progress: {elapsed_min:.1f}/{LIMIT_MINUTES}m | {voltage_v}V | {current_amp}A | {power_kw:.2f}kW | Temp: {temp}°C (+{temp_rise}) | Energy: {calculated_energy_kwh:.3f} kWh")
            else:
                print("Connecting to charger... (Please double check IP and close Smart Life app)")

            time.sleep(interval)

    print("\n--- Generating 1-Hour Research Graphs ---")

    step = 10
    t   = times_min[::step]
    p   = powers[::step]
    tp  = temps[::step]
    e   = energies[::step]
    c   = currents[::step]
    v   = voltages[::step]
    fig, (ax1, ax3) = plt.subplots(2, 1, figsize=(11, 8), sharex=True)

    color1 = 'tab:blue'
    ax1.set_ylabel('Power (kW)', color=color1, fontweight='bold')
    ax1.plot(t, p, color=color1, linewidth=2, label='Power (kW)')
    ax1.tick_params(axis='y', labelcolor=color1)
    ax1.grid(True, linestyle=':', alpha=0.6)

    ax2 = ax1.twinx()
    color2 = 'tab:red'
    ax2.set_ylabel('Temperature (°C)', color=color2, fontweight='bold')
    ax2.plot(t, tp, color=color2, linestyle='--', linewidth=2, label='Temperature (°C)')
    ax2.tick_params(axis='y', labelcolor=color2)
    ax1.set_title(f'EV Charging Research Profile (1 Hour Summary)\nTrue Total Energy: {energies[-1]:.4f} kWh | Temperature Rise: +{max(temps)-initial_temp}°C')

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

    graph_filename = f"EV_Research_Graph_1Hr_{filename_prefix}.png"
    plt.savefig(graph_filename, dpi=300)
    print(f"SUCCESS: 1-Hour Graph saved as {graph_filename}")

except KeyboardInterrupt:
    print("\n[!] Experiment stopped manually by user. Check CSV file for partially saved data.")