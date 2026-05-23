import time
import csv
import json
import math
import random
import os

random.seed(42)

LIMIT_MINUTES = 60
interval = 1

times_min = []
powers = []
temps = []
energies = []
currents = []
voltages = []
resistances = []
temp_rises = []
tuya_raws = []

initial_temp = 32.0
base_voltage = 220.0
max_current = 14.5
charging_power_kw = 3.2

calculated_energy_kwh = 0.0
raw_energy_start = 0.0

filename_prefix = time.strftime('%Y%m%d_%H%M%S')
csv_filename = f"Research_Data_1Hr_Mock_{filename_prefix}.csv"

print(f"--- EV Research V4.1: MOCK MODE (1-Hour Simulation) ---")
print(f"Starting simulation at: {time.strftime('%H:%M:%S')}")
print(f"Sampling: Every {interval}s | Duration: {LIMIT_MINUTES} minutes")

total_points = LIMIT_MINUTES * 60

for i in range(total_points):
    elapsed_min = i / 60.0

    phase_factor = 1.0
    if elapsed_min < 2:
        phase_factor = min(1.0, elapsed_min / 2.0) * 0.3
    elif elapsed_min < 5:
        phase_factor = 0.3 + 0.7 * ((elapsed_min - 2) / 3.0)
    elif elapsed_min > 50:
        phase_factor = max(0.15, 1.0 - ((elapsed_min - 50) / 10.0) * 0.85)
    elif elapsed_min > 45:
        phase_factor = 1.0 - ((elapsed_min - 45) / 5.0) * 0.15

    current_amp = round(max_current * phase_factor + random.gauss(0, 0.15), 2)
    current_amp = max(0.0, current_amp)

    voltage_v = round(base_voltage + random.gauss(0, 1.5) - (phase_factor * 3), 1)

    power_kw = round((voltage_v * current_amp) / 1000.0, 4)

    resistance = round(voltage_v / current_amp, 2) if current_amp > 0.01 else 0.0

    heat_factor = phase_factor ** 1.3
    temp = round(initial_temp + (25.0 * heat_factor) + random.gauss(0, 0.3) + (2.0 * math.sin(elapsed_min / 10.0)), 1)
    temp_rise = round(temp - initial_temp, 1)

    calculated_energy_kwh += power_kw * (interval / 3600.0)

    raw_energy = raw_energy_start + calculated_energy_kwh * 1.02 + random.gauss(0, 0.0001)

    times_min.append(round(elapsed_min, 4))
    powers.append(power_kw)
    temps.append(temp)
    energies.append(round(calculated_energy_kwh, 6))
    currents.append(current_amp)
    voltages.append(voltage_v)
    resistances.append(resistance)
    temp_rises.append(temp_rise)
    tuya_raws.append(round(raw_energy, 6))

    if i % 600 == 0:
        print(f"  Mock Progress: {elapsed_min:.0f}/{LIMIT_MINUTES}m | {voltage_v}V | {current_amp}A | {power_kw:.2f}kW | Temp: {temp}°C (+{temp_rise}) | Energy: {calculated_energy_kwh:.3f} kWh")

print(f"\nSimulation complete. Total energy: {calculated_energy_kwh:.4f} kWh")

with open(csv_filename, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['Time_Min', 'Voltage(V)', 'Current(A)', 'Resistance(Ohm)', 'Power(kW)', 'Temp(C)', 'Temp_Rise(C)', 'Calculated_Energy(kWh)', 'Tuya_Raw_Energy(kWh)'])
    for i in range(len(times_min)):
        writer.writerow([
            times_min[i], voltages[i], currents[i], resistances[i],
            powers[i], temps[i], temp_rises[i], energies[i], tuya_raws[i]
        ])
print(f"CSV saved: {csv_filename}")

step = 30
t_s   = times_min[::step]
p_s   = powers[::step]
tp_s  = temps[::step]
e_s   = energies[::step]
c_s   = currents[::step]
v_s   = voltages[::step]

html_filename = f"EV_Research_Report_1Hr_{filename_prefix}.html"

total_energy = energies[-1]
peak_power = max(powers)
avg_power = sum(powers) / len(powers)
peak_temp = max(temps)
max_temp_rise = max(temps) - initial_temp
avg_voltage = sum(voltages) / len(voltages)
avg_current = sum(currents) / len(currents)
peak_current = max(currents)

summary_stats = {
    "total_energy_kwh": round(total_energy, 4),
    "peak_power_kw": round(peak_power, 3),
    "avg_power_kw": round(avg_power, 3),
    "peak_temp_c": peak_temp,
    "max_temp_rise_c": round(max_temp_rise, 1),
    "initial_temp_c": initial_temp,
    "avg_voltage_v": round(avg_voltage, 1),
    "avg_current_a": round(avg_current, 2),
    "peak_current_a": round(peak_current, 2),
    "duration_min": LIMIT_MINUTES,
    "total_samples": total_points
}

html_content = f"""<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>EV Charging Research Report - 1 Hour</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background: #0f0f1a;
    color: #e0e0e0;
    min-height: 100vh;
  }}
  .header {{
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    padding: 30px 40px;
    border-bottom: 3px solid #00d4ff;
  }}
  .header h1 {{
    font-size: 28px;
    color: #00d4ff;
    margin-bottom: 5px;
  }}
  .header .subtitle {{
    font-size: 14px;
    color: #8892b0;
  }}
  .container {{
    max-width: 1400px;
    margin: 0 auto;
    padding: 30px 20px;
  }}
  .stats-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 15px;
    margin-bottom: 30px;
  }}
  .stat-card {{
    background: linear-gradient(145deg, #1a1a2e, #16213e);
    border: 1px solid #2a2a4a;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    transition: transform 0.2s, border-color 0.2s;
  }}
  .stat-card:hover {{
    transform: translateY(-3px);
    border-color: #00d4ff;
  }}
  .stat-card .label {{
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: #8892b0;
    margin-bottom: 8px;
  }}
  .stat-card .value {{
    font-size: 26px;
    font-weight: 700;
    color: #00d4ff;
  }}
  .stat-card .unit {{
    font-size: 13px;
    color: #8892b0;
    margin-top: 2px;
  }}
  .chart-section {{
    background: #1a1a2e;
    border: 1px solid #2a2a4a;
    border-radius: 12px;
    padding: 25px;
    margin-bottom: 25px;
  }}
  .chart-section h2 {{
    font-size: 18px;
    color: #ccd6f6;
    margin-bottom: 15px;
    padding-bottom: 10px;
    border-bottom: 1px solid #2a2a4a;
  }}
  .chart-wrapper {{
    position: relative;
    height: 380px;
  }}
  .chart-row {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 25px;
    margin-bottom: 25px;
  }}
  .phase-bar {{
    display: flex;
    justify-content: space-around;
    background: #16213e;
    border-radius: 10px;
    padding: 15px;
    margin-bottom: 25px;
  }}
  .phase-item {{
    text-align: center;
    padding: 10px 20px;
    border-radius: 8px;
  }}
  .phase-item .phase-label {{
    font-size: 11px;
    color: #8892b0;
    text-transform: uppercase;
    letter-spacing: 1px;
  }}
  .phase-item .phase-value {{
    font-size: 16px;
    font-weight: 600;
    margin-top: 4px;
  }}
  .phase-ramp {{ color: #ffd93d; }}
  .phase-cc {{ color: #6bcb77; }}
  .phase-cv {{ color: #4d96ff; }}
  .phase-taper {{ color: #ff6b6b; }}
  table.data-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
    margin-top: 10px;
  }}
  table.data-table th {{
    background: #16213e;
    color: #00d4ff;
    padding: 10px 8px;
    text-align: center;
    font-weight: 600;
    position: sticky;
    top: 0;
  }}
  table.data-table td {{
    padding: 6px 8px;
    text-align: center;
    border-bottom: 1px solid #2a2a4a;
    color: #ccd6f6;
  }}
  table.data-table tr:hover td {{
    background: #16213e;
  }}
  .table-container {{
    max-height: 400px;
    overflow-y: auto;
    border-radius: 8px;
    border: 1px solid #2a2a4a;
  }}
  .badge {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
  }}
  .badge-mock {{
    background: #ff6b6b22;
    color: #ff6b6b;
    border: 1px solid #ff6b6b44;
  }}
  .footer {{
    text-align: center;
    padding: 20px;
    color: #555;
    font-size: 12px;
  }}
  @media (max-width: 768px) {{
    .chart-row {{ grid-template-columns: 1fr; }}
    .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
  }}
</style>
</head>
<body>

<div class="header">
  <h1>EV Charging Research Report</h1>
  <div class="subtitle">
    1-Hour Charging Profile Analysis &nbsp;
    <span class="badge badge-mock">MOCK DATA</span>
    &nbsp;|&nbsp; Generated: {time.strftime('%d/%m/%Y %H:%M:%S')}
  </div>
</div>

<div class="container">

  <div class="stats-grid">
    <div class="stat-card">
      <div class="label">Total Energy</div>
      <div class="value">{summary_stats['total_energy_kwh']}</div>
      <div class="unit">kWh</div>
    </div>
    <div class="stat-card">
      <div class="label">Peak Power</div>
      <div class="value">{summary_stats['peak_power_kw']}</div>
      <div class="unit">kW</div>
    </div>
    <div class="stat-card">
      <div class="label">Average Power</div>
      <div class="value">{summary_stats['avg_power_kw']}</div>
      <div class="unit">kW</div>
    </div>
    <div class="stat-card">
      <div class="label">Peak Temperature</div>
      <div class="value">{summary_stats['peak_temp_c']}°C</div>
      <div class="unit">Rise: +{summary_stats['max_temp_rise_c']}°C</div>
    </div>
    <div class="stat-card">
      <div class="label">Average Voltage</div>
      <div class="value">{summary_stats['avg_voltage_v']}</div>
      <div class="unit">V</div>
    </div>
    <div class="stat-card">
      <div class="label">Average Current</div>
      <div class="value">{summary_stats['avg_current_a']}</div>
      <div class="unit">A</div>
    </div>
    <div class="stat-card">
      <div class="label">Peak Current</div>
      <div class="value">{summary_stats['peak_current_a']}</div>
      <div class="unit">A</div>
    </div>
    <div class="stat-card">
      <div class="label">Duration</div>
      <div class="value">{summary_stats['duration_min']}</div>
      <div class="unit">minutes ({summary_stats['total_samples']} samples)</div>
    </div>
  </div>

  <div class="phase-bar">
    <div class="phase-item">
      <div class="phase-label">Phase 1: Ramp Up</div>
      <div class="phase-value phase-ramp">0 - 5 min</div>
    </div>
    <div class="phase-item">
      <div class="phase-label">Phase 2: CC (Const Current)</div>
      <div class="phase-value phase-cc">5 - 45 min</div>
    </div>
    <div class="phase-item">
      <div class="phase-label">Phase 3: CV Transition</div>
      <div class="phase-value phase-cv">45 - 50 min</div>
    </div>
    <div class="phase-item">
      <div class="phase-label">Phase 4: Taper Off</div>
      <div class="phase-value phase-taper">50 - 60 min</div>
    </div>
  </div>

  <div class="chart-section">
    <h2>Power & Temperature Profile</h2>
    <div class="chart-wrapper"><canvas id="chartPowerTemp"></canvas></div>
  </div>

  <div class="chart-row">
    <div class="chart-section">
      <h2>Voltage Profile</h2>
      <div class="chart-wrapper"><canvas id="chartVoltage"></canvas></div>
    </div>
    <div class="chart-section">
      <h2>Current Profile</h2>
      <div class="chart-wrapper"><canvas id="chartCurrent"></canvas></div>
    </div>
  </div>

  <div class="chart-row">
    <div class="chart-section">
      <h2>Cumulative Energy (kWh)</h2>
      <div class="chart-wrapper"><canvas id="chartEnergy"></canvas></div>
    </div>
    <div class="chart-section">
      <h2>Resistance Profile (Ohm)</h2>
      <div class="chart-wrapper"><canvas id="chartResistance"></canvas></div>
    </div>
  </div>

  <div class="chart-section">
    <h2>Data Log (Sampled every 30s)</h2>
    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>Time (min)</th>
            <th>Voltage (V)</th>
            <th>Current (A)</th>
            <th>Resistance (&#8486;)</th>
            <th>Power (kW)</th>
            <th>Temp (&#176;C)</th>
            <th>Temp Rise (&#176;C)</th>
            <th>Energy (kWh)</th>
          </tr>
        </thead>
        <tbody>
"""

table_step = 30
for i in range(0, len(times_min), table_step):
    html_content += f"""          <tr>
            <td>{times_min[i]:.2f}</td>
            <td>{voltages[i]}</td>
            <td>{currents[i]}</td>
            <td>{resistances[i]}</td>
            <td>{powers[i]:.3f}</td>
            <td>{temps[i]}</td>
            <td>+{temp_rises[i]}</td>
            <td>{energies[i]:.4f}</td>
          </tr>
"""

html_content += f"""        </tbody>
      </table>
    </div>
  </div>

</div>

<div class="footer">EV Research V4.1 | Mock Simulation Report | {time.strftime('%Y-%m-%d %H:%M:%S')}</div>

<script>
const t = {json.dumps(t_s)};
const p = {json.dumps(p_s)};
const tp = {json.dumps(tp_s)};
const e = {json.dumps(e_s)};
const c = {json.dumps(c_s)};
const v = {json.dumps(v_s)};

Chart.defaults.color = '#8892b0';
Chart.defaults.borderColor = '#2a2a4a';

var baseOpts = {{
  responsive: true,
  maintainAspectRatio: false,
  interaction: {{ mode: 'index', intersect: false }},
  plugins: {{
    legend: {{ labels: {{ color: '#ccd6f6', padding: 15 }} }},
    tooltip: {{
      backgroundColor: '#1a1a2e',
      titleColor: '#00d4ff',
      bodyColor: '#ccd6f6',
      borderColor: '#2a2a4a',
      borderWidth: 1,
      padding: 10
    }}
  }}
}};

function xScale() {{
  return {{ title: {{ display: true, text: 'Time (min)', color: '#8892b0' }}, ticks: {{ color: '#8892b0' }}, grid: {{ color: '#1e1e3a' }} }};
}}

function yScale(label, color, pos) {{
  return {{ type: 'linear', position: pos || 'left', title: {{ display: true, text: label, color: color || '#8892b0' }}, ticks: {{ color: color || '#8892b0' }}, grid: {{ color: '#1e1e3a' }} }};
}}

new Chart(document.getElementById('chartPowerTemp'), {{
  type: 'line',
  data: {{
    labels: t,
    datasets: [
      {{
        label: 'Power (kW)',
        data: p,
        borderColor: '#00d4ff',
        backgroundColor: 'rgba(0,212,255,0.1)',
        borderWidth: 2,
        fill: true,
        tension: 0.3,
        pointRadius: 0,
        yAxisID: 'y'
      }},
      {{
        label: 'Temperature (\\u00b0C)',
        data: tp,
        borderColor: '#ff6b6b',
        backgroundColor: 'rgba(255,107,107,0.1)',
        borderWidth: 2,
        borderDash: [5, 3],
        fill: true,
        tension: 0.3,
        pointRadius: 0,
        yAxisID: 'y1'
      }}
    ]
  }},
  options: Object.assign({{}}, baseOpts, {{
    scales: {{
      x: xScale(),
      y: {{ type: 'linear', position: 'left', title: {{ display: true, text: 'Power (kW)', color: '#00d4ff' }}, ticks: {{ color: '#00d4ff' }}, grid: {{ color: '#1e1e3a' }} }},
      y1: {{ type: 'linear', position: 'right', title: {{ display: true, text: 'Temperature (\\u00b0C)', color: '#ff6b6b' }}, ticks: {{ color: '#ff6b6b' }}, grid: {{ drawOnChartArea: false }} }}
    }}
  }})
}});

new Chart(document.getElementById('chartVoltage'), {{
  type: 'line',
  data: {{
    labels: t,
    datasets: [{{
      label: 'Voltage (V)',
      data: v,
      borderColor: '#6bcb77',
      backgroundColor: 'rgba(107,203,119,0.1)',
      borderWidth: 2,
      fill: true,
      tension: 0.3,
      pointRadius: 0
    }}]
  }},
  options: Object.assign({{}}, baseOpts, {{
    scales: {{ x: xScale(), y: yScale('Voltage (V)', '#6bcb77') }}
  }})
}});

new Chart(document.getElementById('chartCurrent'), {{
  type: 'line',
  data: {{
    labels: t,
    datasets: [{{
      label: 'Current (A)',
      data: c,
      borderColor: '#a855f7',
      backgroundColor: 'rgba(168,85,247,0.1)',
      borderWidth: 2,
      fill: true,
      tension: 0.3,
      pointRadius: 0
    }}]
  }},
  options: Object.assign({{}}, baseOpts, {{
    scales: {{ x: xScale(), y: yScale('Current (A)', '#a855f7') }}
  }})
}});

new Chart(document.getElementById('chartEnergy'), {{
  type: 'line',
  data: {{
    labels: t,
    datasets: [{{
      label: 'Cumulative Energy (kWh)',
      data: e,
      borderColor: '#ffd93d',
      backgroundColor: 'rgba(255,217,61,0.15)',
      borderWidth: 2,
      fill: true,
      tension: 0.3,
      pointRadius: 0
    }}]
  }},
  options: Object.assign({{}}, baseOpts, {{
    scales: {{ x: xScale(), y: yScale('Energy (kWh)', '#ffd93d') }}
  }})
}});

var r_data = v.map(function(voltage, i) {{ return c[i] > 0.01 ? +(voltage / c[i]).toFixed(2) : 0; }});
new Chart(document.getElementById('chartResistance'), {{
  type: 'line',
  data: {{
    labels: t,
    datasets: [{{
      label: 'Resistance (\\u2126)',
      data: r_data,
      borderColor: '#f97316',
      backgroundColor: 'rgba(249,115,22,0.1)',
      borderWidth: 2,
      fill: true,
      tension: 0.3,
      pointRadius: 0
    }}]
  }},
  options: Object.assign({{}}, baseOpts, {{
    scales: {{ x: xScale(), y: yScale('Resistance (\\u2126)', '#f97316') }}
  }})
}});
</script>

</body>
</html>
"""

with open(html_filename, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"\nHTML Report saved: {html_filename}")
print(f"File size: {os.path.getsize(html_filename) / 1024:.1f} KB")
print(f"\nOpen in browser: file:///{os.path.abspath(html_filename).replace(os.sep, '/')}")
