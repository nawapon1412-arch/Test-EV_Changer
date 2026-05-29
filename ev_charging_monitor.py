import tinytuya
import time
import csv
import json
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ============================================
#  CONFIG - Edit these values for your device
# ============================================
DEVICE_ID  = "YOUR_DEVICE_ID"
LOCAL_KEY  = "YOUR_LOCAL_KEY"
IP_ADDRESS = "192.168.1.XXX"
TUYA_VERSION = 3.5

# ============================================
#  EXPERIMENT SETTINGS
# ============================================
CAR_NAME       = "MY_CAR"
LIMIT_MINUTES  = 60
INTERVAL_SEC   = 1.0

# ============================================
#  DPS MAPPING (EDIT THIS SECTION)
#  Put the DPS keys used by your device here.
#  Use None if your device doesn't provide it.
# ============================================
DPS_MAP = {
    "switch": "1",
    "voltage": "20",
    "current": "4",
    "power":   None,
    "temp":    "24",
    "energy_total": None,
}

# ============================================
#  SCALING (EDIT THIS SECTION)
#  Convert raw DPS values -> engineering units
# ============================================
SCALE = {
    "voltage_div": 10.0,
    "current_div": 1000.0,
    "power_div":   10.0,
    "temp_div":    1.0,
    "energy_div":  100.0,
    "power_unit":  "W",
    "energy_unit": "kWh",
}

# ============== helpers ==============

def safe_get_dps(dps: dict, key: str, default=None):
    if key is None:
        return default
    return dps.get(key, default)

def to_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return float(default)

def now_str():
    return time.strftime("%Y%m%d_%H%M%S")

# ============== device init ==============

d = tinytuya.OutletDevice(DEVICE_ID, IP_ADDRESS, LOCAL_KEY)
d.set_version(TUYA_VERSION)
d.set_socketTimeout(5)

print(f"--- EV Charging Monitor: {CAR_NAME} ---")
print(f"Start: {time.strftime('%H:%M:%S')}")
print(f"Interval: {INTERVAL_SEC}s | Duration: {LIMIT_MINUTES} min")

# ============== data buffers ==============

times_min   = []
voltages_v  = []
currents_a  = []
powers_kw   = []
temps_c     = []
energies_kwh = []
energy_raw_kwh = []

calculated_energy_kwh = 0.0

start_ts = time.time()
last_good_ts = None
initial_temp = None

prefix = now_str()
csv_name   = f"Research_Data_{CAR_NAME}_{prefix}.csv"
graph_name = f"EV_Graph_{CAR_NAME}_{prefix}.png"

# ============== main loop ==============

try:
    with open(csv_name, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "Time_Min",
            "Voltage_V",
            "Current_A",
            "Power_kW",
            "Temp_C",
            "Temp_Rise_C",
            "Calc_Energy_kWh",
            "Device_Energy_kWh",
            "DPS_Raw_JSON"
        ])

        next_tick = time.time()

        while True:
            now = time.time()
            if now < next_tick:
                time.sleep(next_tick - now)
            now = time.time()
            next_tick = next_tick + INTERVAL_SEC

            elapsed_min = (now - start_ts) / 60.0
            if elapsed_min > LIMIT_MINUTES:
                print(f"\n[!] Reached {LIMIT_MINUTES} minutes. Stopping...")
                break

            data = None
            try:
                data = d.status()
            except Exception as e:
                print(f"Read error: {e}")

            if not (data and isinstance(data, dict) and "dps" in data and isinstance(data["dps"], dict)):
                last_good_ts = None
                print("Connecting... (Check IP / Close Smart Life app)")
                continue

            dps = data["dps"]
            dps_raw_json = json.dumps(dps, ensure_ascii=False)

            raw_v = safe_get_dps(dps, DPS_MAP["voltage"], None)
            raw_i = safe_get_dps(dps, DPS_MAP["current"], None)
            raw_p = safe_get_dps(dps, DPS_MAP["power"],   None)
            raw_t = safe_get_dps(dps, DPS_MAP["temp"],    None)
            raw_e = safe_get_dps(dps, DPS_MAP["energy_total"], None)

            voltage_v = to_float(raw_v, 0.0) / SCALE["voltage_div"] if raw_v is not None else float("nan")
            current_a = to_float(raw_i, 0.0) / SCALE["current_div"] if raw_i is not None else float("nan")
            temp_c    = to_float(raw_t, 0.0) / SCALE["temp_div"]    if raw_t is not None else float("nan")

            power_kw = float("nan")
            if raw_p is not None:
                p_val = to_float(raw_p, 0.0) / SCALE["power_div"]
                if SCALE["power_unit"].lower() == "w":
                    power_kw = p_val / 1000.0
                else:
                    power_kw = p_val
            else:
                if not (math.isnan(voltage_v) or math.isnan(current_a)):
                    power_kw = (voltage_v * current_a) / 1000.0

            if initial_temp is None and not math.isnan(temp_c):
                initial_temp = temp_c
            temp_rise = (temp_c - initial_temp) if (initial_temp is not None and not math.isnan(temp_c)) else float("nan")

            dev_energy = float("nan")
            if raw_e is not None:
                dev_energy = to_float(raw_e, 0.0) / SCALE["energy_div"]

            if last_good_ts is None:
                dt = 0.0
            else:
                dt = now - last_good_ts
            last_good_ts = now

            if not math.isnan(power_kw) and dt > 0:
                calculated_energy_kwh += power_kw * (dt / 3600.0)

            times_min.append(elapsed_min)
            voltages_v.append(voltage_v)
            currents_a.append(current_a)
            powers_kw.append(power_kw)
            temps_c.append(temp_c)
            energies_kwh.append(calculated_energy_kwh)
            energy_raw_kwh.append(dev_energy)

            w.writerow([
                round(elapsed_min, 3),
                None if math.isnan(voltage_v) else round(voltage_v, 2),
                None if math.isnan(current_a) else round(current_a, 3),
                None if math.isnan(power_kw)  else round(power_kw, 4),
                None if math.isnan(temp_c)    else round(temp_c, 2),
                None if math.isnan(temp_rise) else round(temp_rise, 2),
                round(calculated_energy_kwh, 6),
                None if math.isnan(dev_energy) else round(dev_energy, 6),
                dps_raw_json
            ])
            f.flush()

            print(
                f"{elapsed_min:6.2f}/{LIMIT_MINUTES}m | "
                f"V={voltage_v:7.2f}V | I={current_a:6.3f}A | P={power_kw:7.3f}kW | "
                f"T={temp_c:6.2f}C (+{temp_rise:5.2f}) | "
                f"E(calc)={calculated_energy_kwh:8.4f} kWh"
            )

    # ============== graphs ==============
    print("\n--- Generating Graphs ---")

    fig, axes = plt.subplots(3, 1, figsize=(11, 10), sharex=True)

    ax = axes[0]
    ax.plot(times_min, powers_kw, label="Power (kW)", linewidth=2)
    ax.set_ylabel("Power (kW)")
    ax.grid(True, linestyle=":", alpha=0.6)

    ax_t = ax.twinx()
    ax_t.plot(times_min, temps_c, label="Temp (C)", linestyle="--", linewidth=2)
    ax_t.set_ylabel("Temp (C)")

    ax = axes[1]
    ax.plot(times_min, voltages_v, label="Voltage (V)", linewidth=2)
    ax.set_ylabel("Voltage (V)")
    ax.grid(True, linestyle=":", alpha=0.6)

    ax_i = ax.twinx()
    ax_i.plot(times_min, currents_a, label="Current (A)", linestyle="-.", linewidth=2)
    ax_i.set_ylabel("Current (A)")

    ax = axes[2]
    ax.plot(times_min, energies_kwh, label="Calculated Energy (kWh)", linewidth=2)
    if any([not math.isnan(x) for x in energy_raw_kwh]):
        ax.plot(times_min, energy_raw_kwh, label="Device Energy (kWh)", linewidth=2, alpha=0.8)
    ax.set_xlabel("Time (Minutes)")
    ax.set_ylabel("Energy (kWh)")
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="best")

    title = f"EV Charging - {CAR_NAME} | Calc Energy: {energies_kwh[-1]:.4f} kWh"
    if initial_temp is not None:
        valid_temps = [x for x in temps_c if not math.isnan(x)]
        if valid_temps:
            title += f" | Temp Rise: +{(max(valid_temps)-initial_temp):.2f} C"
    fig.suptitle(title)

    fig.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(graph_name, dpi=300)
    print(f"Graph saved: {graph_name}")
    print(f"CSV saved: {csv_name}")

except KeyboardInterrupt:
    print("\n[!] Stopped by user. Check CSV for partial data.")
