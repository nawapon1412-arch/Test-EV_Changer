import csv
import json
import time
import os

CSV_FILE = "Research_Data_Real.csv"

times_min = []
powers = []
temps = []
energies = []
currents = []
voltages = []
resistances = []
temp_rises = []
tuya_raws = []

with open(CSV_FILE, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f, delimiter='\t')
    for row in reader:
        times_min.append(float(row['Time_Min']))
        voltages.append(float(row['Voltage(V)']))
        currents.append(float(row['Current(A)']))
        resistances.append(float(row['Resistance(Ohm)']))
        powers.append(float(row['Power(kW)']))
        temps.append(float(row['Temp(C)']))
        temp_rises.append(float(row['Temp_Rise(C)']))
        energies.append(float(row['Calculated_Energy(kWh)']))
        tuya_raws.append(float(row['Tuya_Raw_Energy(kWh)']))

total_points = len(times_min)
initial_temp = temps[0]
total_energy = energies[-1]
peak_power = max(powers)
avg_power = sum(powers) / len(powers)
peak_temp = max(temps)
max_temp_rise = max(temps) - initial_temp
avg_voltage = sum(voltages) / len(voltages)
avg_current = sum(currents) / len(currents)
peak_current = max(currents)
duration_min = times_min[-1]

print(f"--- EV Research: CSV -> HTML Report ---")
print(f"Loaded {total_points} rows from {CSV_FILE}")
print(f"Duration: {duration_min:.1f} min | Energy: {total_energy:.4f} kWh | Peak Power: {peak_power:.3f} kW")

summary = {
    "total_energy_kwh": round(total_energy, 4),
    "peak_power_kw": round(peak_power, 3),
    "avg_power_kw": round(avg_power, 3),
    "peak_temp_c": peak_temp,
    "max_temp_rise_c": round(max_temp_rise, 1),
    "initial_temp_c": initial_temp,
    "avg_voltage_v": round(avg_voltage, 1),
    "avg_current_a": round(avg_current, 2),
    "peak_current_a": round(peak_current, 2),
    "duration_min": round(duration_min, 1),
    "total_samples": total_points,
    "tuya_start_kwh": tuya_raws[0],
    "tuya_end_kwh": tuya_raws[-1],
    "tuya_delta_kwh": round(tuya_raws[-1] - tuya_raws[0], 4)
}

json_t = json.dumps(times_min)
json_p = json.dumps(powers)
json_tp = json.dumps(temps)
json_e = json.dumps(energies)
json_c = json.dumps(currents)
json_v = json.dumps(voltages)
json_r = json.dumps(resistances)
json_tr = json.dumps(tuya_raws)

filename_prefix = time.strftime('%Y%m%d_%H%M%S')
html_filename = f"EV_Research_Report_Real_{filename_prefix}.html"

table_rows = ""
for i in range(len(times_min)):
    table_rows += f"""          <tr>
            <td>{times_min[i]:.2f}</td>
            <td>{voltages[i]}</td>
            <td>{currents[i]}</td>
            <td>{resistances[i]}</td>
            <td>{powers[i]:.3f}</td>
            <td>{temps[i]}</td>
            <td>+{temp_rises[i]}</td>
            <td>{energies[i]:.4f}</td>
            <td>{tuya_raws[i]}</td>
          </tr>
"""

html = f"""<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>EV Charging Research Report - Real Data</title>
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
  .header h1 {{ font-size: 28px; color: #00d4ff; margin-bottom: 5px; }}
  .header .subtitle {{ font-size: 14px; color: #8892b0; }}
  .container {{ max-width: 1400px; margin: 0 auto; padding: 30px 20px; }}
  .stats-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
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
  .stat-card:hover {{ transform: translateY(-3px); border-color: #00d4ff; }}
  .stat-card .label {{
    font-size: 11px; text-transform: uppercase;
    letter-spacing: 1.5px; color: #8892b0; margin-bottom: 8px;
  }}
  .stat-card .value {{ font-size: 24px; font-weight: 700; color: #00d4ff; }}
  .stat-card .unit {{ font-size: 13px; color: #8892b0; margin-top: 2px; }}
  .chart-section {{
    background: #1a1a2e; border: 1px solid #2a2a4a;
    border-radius: 12px; padding: 25px; margin-bottom: 25px;
  }}
  .chart-section h2 {{
    font-size: 18px; color: #ccd6f6; margin-bottom: 15px;
    padding-bottom: 10px; border-bottom: 1px solid #2a2a4a;
  }}
  .chart-wrapper {{ position: relative; height: 380px; }}
  .chart-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 25px; margin-bottom: 25px; }}
  table.data-table {{
    width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 10px;
  }}
  table.data-table th {{
    background: #16213e; color: #00d4ff; padding: 10px 8px;
    text-align: center; font-weight: 600; position: sticky; top: 0;
  }}
  table.data-table td {{
    padding: 6px 8px; text-align: center;
    border-bottom: 1px solid #2a2a4a; color: #ccd6f6;
  }}
  table.data-table tr:hover td {{ background: #16213e; }}
  .table-container {{
    max-height: 400px; overflow-y: auto;
    border-radius: 8px; border: 1px solid #2a2a4a;
  }}
  .badge {{
    display: inline-block; padding: 3px 10px;
    border-radius: 12px; font-size: 11px; font-weight: 600;
  }}
  .badge-real {{
    background: #6bcb7722; color: #6bcb77; border: 1px solid #6bcb7744;
  }}
  .footer {{ text-align: center; padding: 20px; color: #555; font-size: 12px; }}
  @keyframes fadeInUp {{
    from {{ opacity: 0; transform: translateY(30px); }}
    to {{ opacity: 1; transform: translateY(0); }}
  }}
  @keyframes slideInLeft {{
    from {{ opacity: 0; transform: translateX(-40px); }}
    to {{ opacity: 1; transform: translateX(0); }}
  }}
  @keyframes pulseGlow {{
    0%, 100% {{ box-shadow: 0 0 0 0 rgba(0,212,255,0); }}
    50% {{ box-shadow: 0 0 20px 5px rgba(0,212,255,0.15); }}
  }}
  @keyframes countUp {{
    from {{ opacity: 0; transform: scale(0.5); }}
    to {{ opacity: 1; transform: scale(1); }}
  }}
  .header {{ animation: slideInLeft 0.8s ease-out; }}
  .stat-card {{
    opacity: 0;
    animation: fadeInUp 0.6s ease-out forwards;
  }}
  .stat-card:nth-child(1) {{ animation-delay: 0.1s; }}
  .stat-card:nth-child(2) {{ animation-delay: 0.15s; }}
  .stat-card:nth-child(3) {{ animation-delay: 0.2s; }}
  .stat-card:nth-child(4) {{ animation-delay: 0.25s; }}
  .stat-card:nth-child(5) {{ animation-delay: 0.3s; }}
  .stat-card:nth-child(6) {{ animation-delay: 0.35s; }}
  .stat-card:nth-child(7) {{ animation-delay: 0.4s; }}
  .stat-card:nth-child(8) {{ animation-delay: 0.45s; }}
  .stat-card .value {{ animation: countUp 0.5s ease-out 0.6s both; }}
  .chart-section {{
    opacity: 0;
    transform: translateY(20px);
    transition: opacity 0.7s ease-out, transform 0.7s ease-out;
  }}
  .chart-section.visible {{
    opacity: 1;
    transform: translateY(0);
  }}
  .chart-section:hover {{
    animation: pulseGlow 2s ease-in-out;
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
    <span class="badge badge-real">REAL DATA</span>
    &nbsp;|&nbsp; Generated: {time.strftime('%d/%m/%Y %H:%M:%S')}
    &nbsp;|&nbsp; Source: {CSV_FILE}
  </div>
</div>

<div class="container">

  <div class="stats-grid">
    <div class="stat-card">
      <div class="label">Total Energy (Calculated)</div>
      <div class="value">{summary['total_energy_kwh']}</div>
      <div class="unit">kWh</div>
    </div>
    <div class="stat-card">
      <div class="label">Tuya Raw Energy</div>
      <div class="value">{summary['tuya_delta_kwh']}</div>
      <div class="unit">kWh (Delta)</div>
    </div>
    <div class="stat-card">
      <div class="label">Peak Power</div>
      <div class="value">{summary['peak_power_kw']}</div>
      <div class="unit">kW</div>
    </div>
    <div class="stat-card">
      <div class="label">Average Power</div>
      <div class="value">{summary['avg_power_kw']}</div>
      <div class="unit">kW</div>
    </div>
    <div class="stat-card">
      <div class="label">Temperature</div>
      <div class="value">{summary['peak_temp_c']}°C</div>
      <div class="unit">Rise: +{summary['max_temp_rise_c']}°C</div>
    </div>
    <div class="stat-card">
      <div class="label">Average Voltage</div>
      <div class="value">{summary['avg_voltage_v']}</div>
      <div class="unit">V</div>
    </div>
    <div class="stat-card">
      <div class="label">Average Current</div>
      <div class="value">{summary['avg_current_a']}</div>
      <div class="unit">A</div>
    </div>
    <div class="stat-card">
      <div class="label">Duration</div>
      <div class="value">{summary['duration_min']}</div>
      <div class="unit">min ({summary['total_samples']} samples)</div>
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
    <h2>Tuya Raw Energy vs Calculated Energy</h2>
    <div class="chart-wrapper"><canvas id="chartEnergyCompare"></canvas></div>
  </div>

  <div class="chart-section">
    <h2>Data Log (All {total_points} rows)</h2>
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
            <th>Calc Energy (kWh)</th>
            <th>Tuya Raw (kWh)</th>
          </tr>
        </thead>
        <tbody>
{table_rows}
        </tbody>
      </table>
    </div>
  </div>

</div>

<div class="footer">EV Research V4.1 | Real Data Report | {time.strftime('%Y-%m-%d %H:%M:%S')}</div>

<script>
document.addEventListener('DOMContentLoaded', function() {{
  var sections = document.querySelectorAll('.chart-section');
  var observer = new IntersectionObserver(function(entries) {{
    entries.forEach(function(entry) {{
      if (entry.isIntersecting) {{
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }}
    }});
  }}, {{ threshold: 0.1 }});
  sections.forEach(function(s) {{ observer.observe(s); }});

  document.querySelectorAll('.stat-card .value').forEach(function(el) {{
    var text = el.textContent.trim();
    var numMatch = text.match(/([\\d.]+)/);
    if (!numMatch) return;
    var target = parseFloat(numMatch[1]);
    var suffix = text.replace(numMatch[1], '');
    var decimals = numMatch[1].includes('.') ? numMatch[1].split('.')[1].length : 0;
    var duration = 1500;
    var start = performance.now();
    function step(now) {{
      var progress = Math.min((now - start) / duration, 1);
      var eased = 1 - Math.pow(1 - progress, 3);
      var current = target * eased;
      el.textContent = current.toFixed(decimals) + suffix;
      if (progress < 1) requestAnimationFrame(step);
    }}
    el.textContent = '0' + suffix;
    setTimeout(function() {{ requestAnimationFrame(step); }}, 500);
  }});
}});
</script>

<script>
var t = {json_t};
var p = {json_p};
var tp = {json_tp};
var e = {json_e};
var c = {json_c};
var v = {json_v};
var r = {json_r};
var tr = {json_tr};

Chart.defaults.color = '#8892b0';
Chart.defaults.borderColor = '#2a2a4a';

var baseOpts = {{
  responsive: true,
  maintainAspectRatio: false,
  interaction: {{ mode: 'index', intersect: false }},
  animation: {{
    duration: 2000,
    easing: 'easeInOutQuart',
    delay: function(context) {{
      var delay = 0;
      if (context.type === 'data' && context.mode === 'default') {{
        delay = context.dataIndex * 30 + context.datasetIndex * 100;
      }}
      return delay;
    }}
  }},
  plugins: {{
    legend: {{ labels: {{ color: '#ccd6f6', padding: 15, animation: {{ duration: 1000 }} }} }},
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

function yScale(label, color) {{
  return {{ type: 'linear', position: 'left', title: {{ display: true, text: label, color: color || '#8892b0' }}, ticks: {{ color: color || '#8892b0' }}, grid: {{ color: '#1e1e3a' }} }};
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

new Chart(document.getElementById('chartResistance'), {{
  type: 'line',
  data: {{
    labels: t,
    datasets: [{{
      label: 'Resistance (\\u2126)',
      data: r,
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

new Chart(document.getElementById('chartEnergyCompare'), {{
  type: 'line',
  data: {{
    labels: t,
    datasets: [
      {{
        label: 'Calculated Energy (kWh)',
        data: e,
        borderColor: '#ffd93d',
        backgroundColor: 'rgba(255,217,61,0.1)',
        borderWidth: 2,
        fill: false,
        tension: 0.3,
        pointRadius: 0,
        yAxisID: 'y'
      }},
      {{
        label: 'Tuya Raw Energy (kWh)',
        data: tr,
        borderColor: '#4d96ff',
        backgroundColor: 'rgba(77,150,255,0.1)',
        borderWidth: 2,
        borderDash: [5, 3],
        fill: false,
        tension: 0.3,
        pointRadius: 0,
        yAxisID: 'y1'
      }}
    ]
  }},
  options: Object.assign({{}}, baseOpts, {{
    scales: {{
      x: xScale(),
      y: {{ type: 'linear', position: 'left', title: {{ display: true, text: 'Calculated Energy (kWh)', color: '#ffd93d' }}, ticks: {{ color: '#ffd93d' }}, grid: {{ color: '#1e1e3a' }} }},
      y1: {{ type: 'linear', position: 'right', title: {{ display: true, text: 'Tuya Raw Energy (kWh)', color: '#4d96ff' }}, ticks: {{ color: '#4d96ff' }}, grid: {{ drawOnChartArea: false }} }}
    }}
  }})
}});
</script>

</body>
</html>
"""

with open(html_filename, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"\nHTML Report saved: {html_filename}")
print(f"File size: {os.path.getsize(html_filename) / 1024:.1f} KB")
print(f"Open in browser: file:///{os.path.abspath(html_filename).replace(os.sep, '/')}")
