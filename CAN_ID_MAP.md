# CAN ID Mapping for Interactive Dashboard

## Overview
This document maps all CAN message IDs used by the dashboard for both sending and receiving data.

---

## Vehicle Data Messages (Dashboard Controls)

### 0x100 - Speed
- **Description**: Vehicle speed in km/h
- **Data Byte 0**: Speed value (0-260)
- **Range**: 0-260 km/h
- **Example**:
  ```bash
  cansend vcan0 100#00    # 0 km/h
  cansend vcan0 100#32    # 50 km/h
  cansend vcan0 100#64    # 100 km/h
  cansend vcan0 100#C8    # 200 km/h
  ```

### 0x101 - RPM (Engine Speed)
- **Description**: Engine RPM ÷ 100
- **Data Byte 0**: RPM value / 100
- **Range**: 0-80 (represents 0-8000 RPM)
- **Note**: Dashboard multiplies by 100
- **Example**:
  ```bash
  cansend vcan0 101#08    # 800 RPM (idle)
  cansend vcan0 101#19    # 2500 RPM
  cansend vcan0 101#28    # 4000 RPM
  cansend vcan0 101#41    # 6500 RPM (redline)
  cansend vcan0 101#50    # 8000 RPM (max)
  ```

### 0x102 - Gear Position
- **Description**: Current gear selection
- **Data Byte 0**: Gear index
  - `0` = Park (P)
  - `1` = Reverse (R)
  - `2` = Neutral (N)
  - `3` = Drive (D)
- **Example**:
  ```bash
  cansend vcan0 102#00    # Park
  cansend vcan0 102#01    # Reverse
  cansend vcan0 102#02    # Neutral
  cansend vcan0 102#03    # Drive
  ```

### 0x103 - Fuel Level
- **Description**: Fuel level percentage
- **Data Byte 0**: Fuel percentage (0-100)
- **Range**: 0-100%
- **Example**:
  ```bash
  cansend vcan0 103#64    # 100% full
  cansend vcan0 103#32    # 50%
  cansend vcan0 103#14    # 20% (warning)
  cansend vcan0 103#00    # Empty
  ```

### 0x104 - Engine Temperature
- **Description**: Engine coolant temperature
- **Data Byte 0**: Temperature in Celsius
- **Range**: 0-150°C
- **Example**:
  ```bash
  cansend vcan0 104#5A    # 90°C (normal)
  cansend vcan0 104#5F    # 95°C
  cansend vcan0 104#69    # 105°C (warning)
  cansend vcan0 104#78    # 120°C (overheat)
  ```

---

## Warning Indicator Messages

### 0x200 - Check Engine Light
- **Data Byte 0**: 
  - `0` = OFF
  - `1` = ON
- **Example**:
  ```bash
  cansend vcan0 200#01    # Turn on check engine
  cansend vcan0 200#00    # Turn off check engine
  ```

### 0x201 - Battery Warning
- **Data Byte 0**: Battery warning state (0=OFF, 1=ON)
- **Example**:
  ```bash
  cansend vcan0 201#01    # Battery warning ON
  ```

### 0x202 - Seatbelt Warning
- **Data Byte 0**: Seatbelt warning state (0=OFF, 1=ON)
- **Example**:
  ```bash
  cansend vcan0 202#01    # Seatbelt warning ON
  ```

### 0x203 - ABS Warning
- **Data Byte 0**: ABS warning state (0=OFF, 1=ON)
- **Example**:
  ```bash
  cansend vcan0 203#01    # ABS warning ON
  ```

### 0x204 - Oil Pressure Warning
- **Data Byte 0**: Oil pressure warning state (0=OFF, 1=ON)
- **Example**:
  ```bash
  cansend vcan0 204#01    # Oil pressure warning ON
  ```

### 0x205 - Parking Brake
- **Data Byte 0**: Parking brake state (0=OFF, 1=ON)
- **Example**:
  ```bash
  cansend vcan0 205#01    # Parking brake engaged
  cansend vcan0 205#00    # Parking brake released
  ```

### 0x206 - High Beam Indicator
- **Data Byte 0**: High beam state (0=OFF, 1=ON)
- **Example**:
  ```bash
  cansend vcan0 206#01    # High beam ON
  cansend vcan0 206#00    # High beam OFF
  ```

### 0x207 - TPMS (Tire Pressure Monitoring)
- **Data Byte 0**: TPMS warning state (0=OFF, 1=ON)
- **Example**:
  ```bash
  cansend vcan0 207#01    # TPMS warning ON
  ```

### 0x208 - Airbag Warning
- **Data Byte 0**: Airbag warning state (0=OFF, 1=ON)
- **Example**:
  ```bash
  cansend vcan0 208#01    # Airbag warning ON
  ```

---

## Turn Signal and Door Messages

### 0x300 - Left Turn Signal
- **Data Byte 0**: Left turn signal state (0=OFF, 1=ON)
- **Example**:
  ```bash
  cansend vcan0 300#01    # Left turn signal ON
  cansend vcan0 300#00    # Left turn signal OFF
  ```

### 0x301 - Right Turn Signal
- **Data Byte 0**: Right turn signal state (0=OFF, 1=ON)
- **Example**:
  ```bash
  cansend vcan0 301#01    # Right turn signal ON
  cansend vcan0 301#00    # Right turn signal OFF
  ```

### 0x302 - Door Ajar Warning
- **Data Byte 0**: Door state (0=Closed, 1=Open)
- **Example**:
  ```bash
  cansend vcan0 302#01    # Door open
  cansend vcan0 302#00    # Door closed
  ```

---

## Quick Test Scenarios

### Scenario 1: Normal Driving
```bash
cansend vcan0 102#03    # Drive gear
cansend vcan0 100#32    # 50 km/h
cansend vcan0 101#14    # 2000 RPM
cansend vcan0 103#50    # 80% fuel
cansend vcan0 104#5A    # 90°C temp
```

### Scenario 2: Highway Speed
```bash
cansend vcan0 102#03    # Drive gear
cansend vcan0 100#78    # 120 km/h
cansend vcan0 101#1E    # 3000 RPM
cansend vcan0 103#46    # 70% fuel
cansend vcan0 104#5F    # 95°C temp
```

### Scenario 3: Redline
```bash
cansend vcan0 102#03    # Drive gear
cansend vcan0 100#B4    # 180 km/h
cansend vcan0 101#41    # 6500 RPM (redline!)
cansend vcan0 103#28    # 40% fuel
cansend vcan0 104#69    # 105°C temp (hot!)
```

### Scenario 4: Warning Lights Test
```bash
cansend vcan0 200#01    # Check engine
cansend vcan0 202#01    # Seatbelt
cansend vcan0 205#01    # Parking brake
cansend vcan0 302#01    # Door open
cansend vcan0 103#0A    # 10% fuel (low fuel warning)
```

### Scenario 5: Turn Signals
```bash
# Left turn
cansend vcan0 300#01
sleep 3
cansend vcan0 300#00

# Right turn
cansend vcan0 301#01
sleep 3
cansend vcan0 301#00

# Hazards (both on)
cansend vcan0 300#01
cansend vcan0 301#01
```

---

## Data Conversion Reference

### Hex to Decimal Quick Reference
```
Hex  | Dec | Usage
-----|-----|------------------
00   | 0   | Zero / OFF
0A   | 10  | 10 units
14   | 20  | 20 units
19   | 25  | 25 units (2500 RPM)
1E   | 30  | 30 units (3000 RPM)
28   | 40  | 40 units (4000 RPM)
32   | 50  | 50 units / 50%
3C   | 60  | 60 units
46   | 70  | 70 units / 70%
50   | 80  | 80 units / 80%
5A   | 90  | 90°C / 90%
64   | 100 | 100% / 100 units
78   | 120 | 120 km/h
96   | 150 | 150 km/h
C8   | 200 | 200 km/h
FF   | 255 | Maximum value
```

---

## Monitoring CAN Traffic

### Monitor All Messages
```bash
candump vcan0
```

### Monitor Specific IDs
```bash
# Monitor only speed and RPM
candump vcan0,100:101

# Monitor all vehicle data
candump vcan0,100:104

# Monitor all warnings
candump vcan0,200:208
```

### Filter Dashboard Output
```bash
# Show only received messages (not sent by dashboard)
candump vcan0 | grep -v "vcan0  10[0-4]"
```

---

## Notes

1. **Dashboard Sends AND Receives** on 0x100-0x104 (vehicle data)
2. **Dashboard Only Sends** on 0x200-0x208 (warnings) and 0x300-0x302 (signals)
3. All warning indicators (0x200-0x208) are binary: 0=OFF, 1=ON
4. RPM is sent as value÷100, so 0x28 (40) = 4000 RPM
5. Gear values: 0=P, 1=R, 2=N, 3=D (anything else defaults to P)
6. The dashboard updates in real-time when it receives valid CAN messages

---

## Testing Your Setup

1. **Start the dashboard**:
   ```bash
   python3 main-dash.py
   ```

2. **In another terminal, monitor CAN**:
   ```bash
   candump vcan0
   ```

3. **In a third terminal, send commands**:
   ```bash
   cansend vcan0 100#64    # Should show 100 km/h on dashboard
   ```

If the dashboard updates, your setup is working correctly! 🚗✨

