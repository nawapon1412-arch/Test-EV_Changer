# Tuya Raw Energy vs Calculated Energy - สรุปหลักการคำนวณ

## 1. Calculated Energy (สคริปต์คำนวณเอง)

**ต้นทาง:** `ev_research_v4.py:67-71`

```
power_kw = (voltage_v × current_amp) / 1000
energy_kwh += power_kw × (dt_seconds / 3600)
```

- เริ่มนับจาก **0 kWh** เมื่อเริ่มทดลอง
- คำนวณ Instantaneous Power = `Voltage × Current` → แปลงเป็น kW
- สะสมพลังงานด้วย Numerical Integration: `Energy += Power × Δt`
- ค่านี้คือ **Apparent Power (S)** ในหน่วย kVA ไม่ได้คำนึง Power Factor

## 2. Tuya Raw Energy (มิเตอร์ภายในอุปกรณ์)

**ต้นทาง:** `ev_research_v4.py:59`

```
raw_total = dps.get('1', 0) / 100.0
```

- อ่านจาก DPS (Data Point) `1` ของ Tuya Smart Plug
- เป็นค่า **Cumulative Energy** สะสมทั้งหมดตั้งแต่รีเซ็ตล่าสุด
- หน่วยดิบ = 0.01 kWh (หาร 100 เพื่อแปลงเป็น kWh)
- วัด **Real Power (P)** ที่คำนึง Power Factor แล้ว

## 3. เปรียบเทียบจากข้อมูลจริง

| ตัวชี้วัด | Calculated Energy | Tuya Raw Energy |
|---|---|---|
| จุดเริ่มต้น | 0.0000 kWh | 27.79 kWh |
| จุดสิ้นสุด (60 นาที) | 1.8337 kWh | 29.44 kWh |
| **Delta (พลังงานชาร์จ)** | **1.8337 kWh** | **1.65 kWh** |

## 4. สาเหตุที่ค่าไม่เท่ากัน

```
สัดส่วน = Tuya Delta / Calculated = 1.65 / 1.83 ≈ 0.90
```

ตรงกับ Power Factor ≈ 0.9 ของ EV Charger ทั่วไป

| ประเภท | Calculated (V×I) | Tuya Raw (มิเตอร์) |
|---|---|---|
| สิ่งที่วัด | Apparent Power (kVA) | Real Power (kW) |
| Power Factor | ไม่สน → ค่าสูงกว่า | คิดแล้ว → ค่าต่ำกว่า |
| ความแม่นยำ | ต่ำกว่า (ไม่มี PF) | สูงกว่า (วัดจริง) |

## 5. สรุป

- **Calculated Energy** = การ integrate `V × I` แบบง่าย ไม่มี Power Factor → ค่าจะสูงกว่าเสมอ
- **Tuya Raw Energy** = ค่าสะสมจากมิเตอร์ภายในอุปกรณ์ที่วัด Real Power แล้ว → คือพลังงานจริงที่ใช้
- ผลต่างประมาณ **10%** เกิดจาก Power Factor ของ EV Charger
- หากต้องการค่าพลังงานที่แม่นยำ ควรใช้ **Tuya Raw Energy Delta** เป็นหลัก

## 6. สูตรสรุป

```
Apparent Power (VA)    = V × I
Real Power (W)         = V × I × PF
Energy (kWh)           = Σ (Power × Δt / 3600)
Tuya Raw (kWh)         = DPS_1 / 100      (cumulative)
Tuya Delta (kWh)       = Tuya_End - Tuya_Start
```
