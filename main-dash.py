import can
import tkinter as tk
import math
import time
import array
import warnings
import os

# Suppress ALSA warnings
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"
stderr = os.dup(2)
os.close(2)
os.open(os.devnull, os.O_RDWR)

# ================= CAN =================
bus = can.interface.Bus(channel="vcan0", interface="socketcan")

# ================= AUDIO SYSTEM =================
# Set to False to disable audio and improve performance
ENABLE_AUDIO_ATTEMPT = False  # Change to True to enable audio

AUDIO_ENABLED = False
AUDIO_DEVICE = None
audio = None

if ENABLE_AUDIO_ATTEMPT:
    try:
        import pyaudio
        # Restore stderr after import to see our messages
        os.dup2(stderr, 2)
        os.close(stderr)
        
        # Initialize PyAudio
        audio = pyaudio.PyAudio()
        SAMPLE_RATE = 22050
        
        # Find the best output device (prefer PulseAudio/default for mixing support)
        device_priority = []
        
        for i in range(audio.get_device_count()):
            info = audio.get_device_info_by_index(i)
            if info['maxOutputChannels'] > 0:
                name = info['name'].lower()
                # Prioritize software mixers over hardware devices
                if 'pulse' in name or 'default' in name:
                    priority = 0  # Highest priority
                elif 'sysdefault' in name:
                    priority = 1
                else:
                    priority = 2  # Hardware devices last
                device_priority.append((priority, i, info['name']))
        
        if device_priority:
            device_priority.sort()  # Sort by priority
            AUDIO_DEVICE = device_priority[0][1]
            print(f"✓ Using audio device {AUDIO_DEVICE}: {device_priority[0][2]}")
            
            # Test the device by trying to open a stream
            try:
                test_stream = audio.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=22050,
                    output=True,
                    output_device_index=AUDIO_DEVICE
                )
                test_stream.close()
                AUDIO_ENABLED = True
                print("✓ Audio system working - sounds enabled")
            except Exception as e:
                print(f"⚠ Audio device test failed: {e}")
                print("  Disabling audio to prevent lag")
                audio.terminate()
                AUDIO_ENABLED = False
        else:
            raise Exception("No audio output device found")
        
        # Audio state
        engine_stream = None
        last_rpm_sound = 0
        turn_signal_time = 0
        last_turn_signal_blink = False
        
    except ImportError:
        # Restore stderr
        try:
            os.dup2(stderr, 2)
            os.close(stderr)
        except:
            pass
        AUDIO_ENABLED = False
        print("⚠ PyAudio not installed. Audio disabled for better performance.")
    except Exception as e:
        # Restore stderr
        try:
            os.dup2(stderr, 2)
            os.close(stderr)
        except:
            pass
        AUDIO_ENABLED = False
        print(f"⚠ Audio system unavailable: {e}")
        print("  Dashboard will run without sound for better performance")
else:
    # Restore stderr
    try:
        os.dup2(stderr, 2)
        os.close(stderr)
    except:
        pass
    print("ℹ Audio disabled - Set ENABLE_AUDIO_ATTEMPT=True to enable")
    
# Initialize audio state even if disabled
if not AUDIO_ENABLED:
    SAMPLE_RATE = 22050
    engine_stream = None
    last_rpm_sound = 0
    turn_signal_time = 0
    last_turn_signal_blink = False

def generate_engine_sound(rpm, throttle):
    """Generate realistic engine sound based on RPM and throttle"""
    if not AUDIO_ENABLED or rpm < 500:
        return None
    
    duration = 0.15
    samples = int(SAMPLE_RATE * duration)
    
    # Base frequency from RPM
    base_freq = max(20, (rpm / 60.0) * 2)
    
    # Use array for efficient audio generation
    audio_array = array.array('h')  # signed short
    
    for i in range(samples):
        t = i / SAMPLE_RATE
        
        # Generate engine sound with harmonics
        fundamental = math.sin(2 * math.pi * base_freq * t)
        harmonic2 = 0.4 * math.sin(2 * math.pi * base_freq * 2 * t)
        harmonic3 = 0.2 * math.sin(2 * math.pi * base_freq * 3 * t)
        
        # Add roughness
        noise = ((i * 7919) % 200 - 100) / 1000.0
        
        # Combine
        sample = fundamental + harmonic2 + harmonic3 + noise
        
        # Volume based on throttle
        volume = 0.2 + (throttle / 100.0) * 0.4
        sample *= volume
        
        # Clamp
        sample = max(-1.0, min(1.0, sample))
        
        # Convert to 16-bit int
        audio_array.append(int(sample * 32767 * 0.8))
    
    return audio_array.tobytes()

def play_engine_sound(rpm, throttle):
    """Play engine sound"""
    global engine_stream, last_rpm_sound
    
    if not AUDIO_ENABLED or not audio:
        return
        
    if not engine_started or rpm < 500:
        return
    
    # Update every 400 RPM to reduce audio overhead
    if abs(rpm - last_rpm_sound) < 400:
        return
    
    last_rpm_sound = rpm
    
    try:
        sound_data = generate_engine_sound(rpm, throttle)
        if sound_data:
            stream = audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=SAMPLE_RATE,
                output=True,
                output_device_index=AUDIO_DEVICE,
                frames_per_buffer=2048
            )
            try:
                stream.write(sound_data)
            except:
                pass  # Ignore buffer overflow errors
            # Close immediately to free the device
            try:
                stream.stop_stream()
                stream.close()
            except:
                pass
    except Exception as e:
        pass  # Silently ignore audio errors to prevent spam

def play_turn_signal_sound():
    """Play turn signal click"""
    global turn_signal_time
    
    if not AUDIO_ENABLED or not audio:
        return
    
    current_time = time.time()
    if current_time - turn_signal_time < 0.3:
        return
    
    turn_signal_time = current_time
    
    try:
        duration = 0.08
        samples = int(SAMPLE_RATE * duration)
        
        audio_array = array.array('h')
        
        for i in range(samples):
            t = i / SAMPLE_RATE
            envelope = math.exp(-t * 25)
            sample = envelope * math.sin(2 * math.pi * 900 * t)
            audio_array.append(int(sample * 32767 * 0.5))
        
        sound_data = audio_array.tobytes()
        
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=SAMPLE_RATE,
            output=True,
            output_device_index=AUDIO_DEVICE,
            frames_per_buffer=2048
        )
        try:
            stream.write(sound_data)
        except:
            pass  # Ignore buffer overflow errors
        try:
            stream.stop_stream()
            stream.close()
        except:
            pass
    except Exception as e:
        pass  # Silently ignore audio errors

def play_warning_sound():
    """Play warning beep"""
    if not AUDIO_ENABLED or not audio:
        return
    
    try:
        duration = 0.15
        samples = int(SAMPLE_RATE * duration)
        
        audio_array = array.array('h')
        
        for i in range(samples):
            t = i / SAMPLE_RATE
            sample = math.sin(2 * math.pi * 1200 * t) * 0.5
            audio_array.append(int(sample * 32767 * 0.6))
        
        sound_data = audio_array.tobytes()
        
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=SAMPLE_RATE,
            output=True,
            output_device_index=AUDIO_DEVICE,
            frames_per_buffer=2048
        )
        try:
            stream.write(sound_data)
        except:
            pass  # Ignore buffer overflow errors
        try:
            stream.stop_stream()
            stream.close()
        except:
            pass
    except Exception as e:
        pass  # Silently ignore audio errors

# ================= WINDOW =================
W, H = 1600, 800
BG = "#000000"

root = tk.Tk()
root.title("Interactive Premium Instrument Cluster")
root.geometry(f"{W}x{H}")
root.configure(bg=BG)
root.resizable(False, False)

# Make it look more realistic
try:
    root.attributes('-alpha', 0.98)  # Slight transparency for realism
except:
    pass

canvas = tk.Canvas(root, width=W, height=H, bg=BG, highlightthickness=0)
canvas.pack()

# ================= STATE =================
speed = rpm = 0
disp_speed = disp_rpm = 0
gear = "P"
gear_index = 0  # 0=P, 1=R, 2=N, 3=D
fuel = 100
temp = 90
odo = 42358
trip = 156.8

# Control states
throttle = 0  # 0-100
brake = 0     # 0-100
engine_started = False

# Warning states
engine = absw = door = seatbelt = battery = oil_pressure = False
left = right = hazard = parking_brake = high_beam = tpms = airbag = False
blink_state = True
blink_counter = 0
time_str = "14:23"
outside_temp = 22

# Key press tracking
keys_pressed = set()

# Last CAN send times to avoid flooding
last_can_send = {}

# ================= HELPERS =================
def lerp(a, b, f=0.15):
    return a + (b - a) * f

def send_can(msg_id, data, min_interval=0.05):
    """Send CAN message with rate limiting"""
    current_time = time.time()
    if msg_id not in last_can_send or (current_time - last_can_send[msg_id]) >= min_interval:
        msg = can.Message(arbitration_id=msg_id, data=data, is_extended_id=False)
        try:
            bus.send(msg)
            last_can_send[msg_id] = current_time
        except Exception as e:
            print(f"CAN send error: {e}")

# ================= PHYSICS SIMULATION =================
def update_vehicle_physics():
    """Simulate realistic vehicle behavior with safety bounds"""
    global speed, rpm, fuel, temp, throttle, brake
    
    # Clamp inputs to safe ranges
    throttle = max(0, min(100, throttle))
    brake = max(0, min(100, brake))
    
    if not engine_started:
        # Engine off - everything decelerates
        if speed > 0:
            speed = max(0, speed - 2)
        if rpm > 0:
            rpm = max(0, rpm - 100)
        return
    
    # Calculate target RPM based on throttle and gear
    if gear == "P" or gear == "N":
        # In Park/Neutral - RPM based only on throttle
        target_rpm = 800 + (throttle * 60)  # Idle to 6800 RPM
        rpm = lerp(rpm, target_rpm, 0.1)
        # No speed change in P/N
        if speed > 0:
            speed = max(0, speed - 1.5)  # Coasting down
    
    elif gear == "R":
        # Reverse gear
        target_rpm = 800 + (throttle * 50)
        rpm = lerp(rpm, target_rpm, 0.1)
        target_speed = (throttle / 100.0) * 40  # Max 40 km/h reverse
        if brake > 0:
            speed = max(0, speed - brake * 0.3)
        else:
            speed = lerp(speed, target_speed, 0.05)
    
    elif gear == "D":
        # Drive gear - realistic acceleration
        if brake > 0:
            # Braking
            speed = max(0, speed - brake * 0.4)
            rpm = max(800, rpm - 300)
        else:
            # Accelerating or coasting
            if throttle > 0:
                # Acceleration based on RPM and gear simulation
                if speed < 60:
                    # Low gear (1st-2nd) - faster acceleration
                    speed += throttle * 0.15
                    target_rpm = 800 + (speed * 80) + (throttle * 30)
                elif speed < 120:
                    # Mid gear (3rd-4th)
                    speed += throttle * 0.08
                    target_rpm = 2000 + (speed * 35) + (throttle * 25)
                else:
                    # High gear (5th-6th)
                    speed += throttle * 0.04
                    target_rpm = 2500 + (speed * 25) + (throttle * 20)
                
                target_rpm = min(7800, target_rpm)
                rpm = lerp(rpm, target_rpm, 0.15)
            else:
                # Coasting - slow down gradually
                speed = max(0, speed - 0.3)
                # RPM follows speed when coasting
                if speed > 0:
                    target_rpm = 800 + (speed * 20)
                    rpm = lerp(rpm, target_rpm, 0.1)
                else:
                    rpm = lerp(rpm, 800, 0.1)
    
    # Fuel consumption
    if engine_started and throttle > 0:
        consumption = (throttle / 100.0) * 0.002
        fuel = max(0, fuel - consumption)
    
    # Engine temperature
    if engine_started:
        target_temp = 90 + (throttle / 100.0) * 15
        temp = lerp(temp, target_temp, 0.01)
    else:
        temp = lerp(temp, outside_temp, 0.005)
    
    # Clamp values
    speed = max(0, min(260, speed))
    rpm = max(0, min(8000, rpm))
    
    # Send values over CAN
    send_can(0x100, [int(speed)])
    send_can(0x101, [int(rpm / 100)])
    send_can(0x103, [int(fuel)])
    send_can(0x104, [int(temp)])

# ================= KEYBOARD CONTROLS =================
def on_key_press(event):
    """Handle key press events"""
    global throttle, brake, gear, gear_index, engine_started
    global left, right, hazard, parking_brake, high_beam, door, seatbelt
    global engine, battery, oil_pressure, absw, tpms, airbag
    
    key = event.keysym
    keys_pressed.add(key)
    
    # Engine start/stop
    if key == "e" or key == "E":
        engine_started = not engine_started
        engine = not engine_started  # Warning light when engine off
        send_can(0x200, [1 if engine else 0])
        if not engine_started:
            play_warning_sound()
    
    # Gear shifting
    if key == "g" or key == "G":
        gear_index = (gear_index + 1) % 4
        gear = ["P", "R", "N", "D"][gear_index]
        send_can(0x102, [gear_index])
    
    # Turn signals
    if key == "Left":
        left = not left
        if left:
            right = False
            play_turn_signal_sound()
        send_can(0x300, [1 if left else 0])
        send_can(0x301, [0])
    
    if key == "Right":
        right = not right
        if right:
            left = False
            play_turn_signal_sound()
        send_can(0x301, [1 if right else 0])
        send_can(0x300, [0])
    
    # Hazard lights
    if key == "h" or key == "H":
        hazard = not hazard
        left = right = hazard
        if hazard:
            play_turn_signal_sound()
        send_can(0x300, [1 if hazard else 0])
        send_can(0x301, [1 if hazard else 0])
    
    # High beam
    if key == "b" or key == "B":
        high_beam = not high_beam
        send_can(0x206, [1 if high_beam else 0])
    
    # Parking brake
    if key == "p" or key == "P":
        parking_brake = not parking_brake
        if parking_brake:
            play_warning_sound()
        send_can(0x205, [1 if parking_brake else 0])
    
    # Door
    if key == "d" or key == "D":
        door = not door
        if door:
            play_warning_sound()
        send_can(0x302, [1 if door else 0])
    
    # Seatbelt (use 't' key instead to avoid conflict)
    if key == "t" or key == "T":
        seatbelt = not seatbelt
        if seatbelt:
            play_warning_sound()
        send_can(0x202, [1 if seatbelt else 0])

def on_key_release(event):
    """Handle key release events"""
    keys_pressed.discard(event.keysym)

def update_controls():
    """Update throttle and brake based on held keys"""
    global throttle, brake
    
    # Throttle (Up arrow or W)
    if "Up" in keys_pressed or "w" in keys_pressed or "W" in keys_pressed:
        throttle = min(100, throttle + 2)
    else:
        throttle = max(0, throttle - 3)
    
    # Brake (Down arrow or S - but not lowercase 's' to avoid conflict)
    if "Down" in keys_pressed:
        brake = min(100, brake + 3)
    else:
        brake = max(0, brake - 4)

# Bind keyboard events
root.bind("<KeyPress>", on_key_press)
root.bind("<KeyRelease>", on_key_release)

# ================= SPEEDOMETER =================
def draw_speedometer(cx, cy, r):
    # Drop shadow for 3D effect
    canvas.create_oval(cx-r+4, cy-r+4, cx+r+4, cy+r+4,
                      outline="", fill="#000000", width=0)
    
    # Optimized chrome bezel - fewer rings for performance
    chrome_rings = [
        (r+10, "#0a0a0a", 4),
        (r+6, "#2a2a2a", 3),
        (r+2, "#3a3a3a", 2),
    ]
    for ring_r, color, width in chrome_rings:
        canvas.create_oval(cx-ring_r, cy-ring_r, cx+ring_r, cy+ring_r,
                          outline=color, width=width, fill="")
    
    # Main gauge background - deep black
    canvas.create_oval(cx-r, cy-r, cx+r, cy+r,
                      fill="#000000", outline="", width=0)
    
    # Inner shadow ring
    canvas.create_oval(cx-r+3, cy-r+3, cx+r-3, cy+r-3,
                      outline="#0a0a0a", width=2)
    
    # Optimized illuminated arc - every 2 degrees for performance
    arc_width = 25
    for i in range(140, -101, -2):  # Changed from -1 to -2 for better performance
        angle_deg = i
        norm = (140 - angle_deg) / 240.0
        speed_val = norm * 260
        
        # Premium color gradient
        if speed_val <= disp_speed:
            if speed_val < 60:
                # Blue zone
                ratio = speed_val / 60
                r_val = int(ratio * 30)
                g_val = int(180 + ratio * 75)
                b_val = 255
                color = f"#{r_val:02x}{g_val:02x}{b_val:02x}"
            elif speed_val < 120:
                # Cyan to green
                ratio = (speed_val - 60) / 60
                r_val = int(30 + ratio * 30)
                g_val = 255
                b_val = int(255 - ratio * 155)
                color = f"#{r_val:02x}{g_val:02x}{b_val:02x}"
            elif speed_val < 180:
                # Yellow to orange
                ratio = (speed_val - 120) / 60
                r_val = int(60 + ratio * 195)
                g_val = int(255 - ratio * 100)
                b_val = int(100 - ratio * 100)
                color = f"#{r_val:02x}{g_val:02x}{b_val:02x}"
            else:
                # Red zone
                ratio = min(1.0, (speed_val - 180) / 80)
                color = f"#{255:02x}{int(155-ratio*155):02x}{0:02x}"
        else:
            color = "#0d0d0d"
        
        rad = math.radians(angle_deg)
        x1 = cx + math.cos(rad) * (r - arc_width - 2)
        y1 = cy + math.sin(rad) * (r - arc_width - 2)
        x2 = cx + math.cos(rad) * (r - 2)
        y2 = cy + math.sin(rad) * (r - 2)
        canvas.create_line(x1, y1, x2, y2, fill=color, width=4, capstyle="round")
    
    # Tick marks and numbers
    for spd in range(0, 280, 20):
        norm = spd / 260.0
        angle_deg = 140 - (norm * 240)
        rad = math.radians(angle_deg)
        
        if spd % 40 == 0:
            # Major ticks with shadow
            x1 = cx + math.cos(rad) * (r - arc_width - 4)
            y1 = cy + math.sin(rad) * (r - arc_width - 4)
            x2 = cx + math.cos(rad) * (r - arc_width - 20)
            y2 = cy + math.sin(rad) * (r - arc_width - 20)
            canvas.create_line(x1+1, y1+1, x2+1, y2+1, fill="#000000", width=4)
            canvas.create_line(x1, y1, x2, y2, fill="#ffffff", width=3)
            
            # Numbers with shadow for depth
            tx = cx + math.cos(rad) * (r - arc_width - 42)
            ty = cy + math.sin(rad) * (r - arc_width - 42)
            canvas.create_text(tx+1, ty+1, text=str(spd),
                             fill="#000000", font=("Arial", 17, "bold"))
            canvas.create_text(tx, ty, text=str(spd),
                             fill="#f5f5f5", font=("Arial", 17, "bold"))
        else:
            # Minor ticks
            x1 = cx + math.cos(rad) * (r - arc_width - 4)
            y1 = cy + math.sin(rad) * (r - arc_width - 4)
            x2 = cx + math.cos(rad) * (r - arc_width - 12)
            y2 = cy + math.sin(rad) * (r - arc_width - 12)
            canvas.create_line(x1, y1, x2, y2, fill="#888888", width=2)
    
    # Premium needle with realistic appearance
    norm = min(1.0, disp_speed / 260.0)
    needle_angle = 140 - (norm * 240)
    rad = math.radians(needle_angle)
    
    needle_length = r - 32
    nx = cx + math.cos(rad) * needle_length
    ny = cy + math.sin(rad) * needle_length
    
    # Needle shadow
    canvas.create_line(cx+3, cy+3, nx+3, ny+3, fill="#000000", width=6, capstyle="round")
    
    # Optimized needle - fewer layers
    if disp_speed > 100:
        # Glow at high speed
        canvas.create_line(cx, cy, nx, ny, fill="#ff6600", width=8)
    
    # Main needle body - simplified gradient
    canvas.create_line(cx, cy, nx, ny, fill="#cc0000", width=5, capstyle="round")
    canvas.create_line(cx, cy, nx, ny, fill="#ff0000", width=3, capstyle="round")
    
    # Needle center cap - metallic appearance
    canvas.create_oval(cx-16, cy-16, cx+16, cy+16, fill="#1a1a1a", outline="#444444", width=2)
    canvas.create_oval(cx-12, cy-12, cx+12, cy+12, fill="#2a2a2a", outline="#555555", width=1)
    canvas.create_oval(cx-8, cy-8, cx+8, cy+8, fill="#3a3a3a", outline="")
    canvas.create_oval(cx-4, cy-4, cx+4, cy+4, fill="#555555", outline="")
    # Highlight for metallic effect
    canvas.create_oval(cx-3, cy-6, cx+1, cy-2, fill="#888888", outline="")
    
    # Digital display with glow
    speed_int = int(disp_speed)
    
    # Outer glow
    canvas.create_text(cx+3, cy-17, text=str(speed_int),
                      fill="#001a33", font=("Arial", 95, "bold"))
    # Inner glow
    canvas.create_text(cx+1, cy-19, text=str(speed_int),
                      fill="#0088cc", font=("Arial", 93, "bold"))
    # Main display
    canvas.create_text(cx, cy-20, text=str(speed_int),
                      fill="#00ffff", font=("Arial", 90, "bold"))
    
    # Unit label
    canvas.create_text(cx, cy+42, text="km/h",
                      fill="#a0a0a0", font=("Arial", 17))
    
    # Bottom label
    canvas.create_text(cx, cy+r-46, text="SPEED",
                      fill="#7a7a7a", font=("Arial", 12, "bold"))

# ================= TACHOMETER =================
def draw_tachometer(cx, cy, r):
    # Drop shadow for 3D effect
    canvas.create_oval(cx-r+4, cy-r+4, cx+r+4, cy+r+4,
                      outline="", fill="#000000", width=0)
    
    # Optimized chrome bezel - fewer rings for performance
    chrome_rings = [
        (r+10, "#0a0a0a", 4),
        (r+6, "#2a2a2a", 3),
        (r+2, "#3a3a3a", 2),
    ]
    for ring_r, color, width in chrome_rings:
        canvas.create_oval(cx-ring_r, cy-ring_r, cx+ring_r, cy+ring_r,
                          outline=color, width=width, fill="")
    
    # Main gauge background - deep black
    canvas.create_oval(cx-r, cy-r, cx+r, cy+r,
                      fill="#000000", outline="", width=0)
    
    # Inner shadow ring
    canvas.create_oval(cx-r+3, cy-r+3, cx+r-3, cy+r-3,
                      outline="#0a0a0a", width=2)
    
    # Optimized illuminated arc - every 2 degrees for performance
    arc_width = 25
    for i in range(40, 281, 2):  # Changed from 1 to 2 for better performance
        angle_deg = i
        norm = (angle_deg - 40) / 240.0
        rpm_val = norm * 8000
        
        # Premium color gradient matching RPM zones
        if rpm_val <= disp_rpm:
            if rpm_val < 2500:
                # Green zone
                ratio = rpm_val / 2500
                r_val = int(ratio * 50)
                g_val = 255
                b_val = int(150 - ratio * 50)
                color = f"#{r_val:02x}{g_val:02x}{b_val:02x}"
            elif rpm_val < 5000:
                # Yellow zone
                ratio = (rpm_val - 2500) / 2500
                r_val = int(50 + ratio * 205)
                g_val = 255
                b_val = int(100 - ratio * 100)
                color = f"#{r_val:02x}{g_val:02x}{b_val:02x}"
            elif rpm_val < 6500:
                # Orange zone
                ratio = (rpm_val - 5000) / 1500
                r_val = 255
                g_val = int(255 - ratio * 100)
                b_val = 0
                color = f"#{r_val:02x}{g_val:02x}{b_val:02x}"
            else:
                # Red zone
                ratio = min(1.0, (rpm_val - 6500) / 1500)
                r_val = 255
                g_val = int(155 - ratio * 155)
                b_val = 0
                color = f"#{r_val:02x}{g_val:02x}{b_val:02x}"
        else:
            color = "#0d0d0d"
        
        rad = math.radians(angle_deg)
        x1 = cx + math.cos(rad) * (r - arc_width - 2)
        y1 = cy + math.sin(rad) * (r - arc_width - 2)
        x2 = cx + math.cos(rad) * (r - 2)
        y2 = cy + math.sin(rad) * (r - 2)
        canvas.create_line(x1, y1, x2, y2, fill=color, width=4, capstyle="round")
    
    # Redline marker - prominent red indicator
    redline_norm = 6500 / 8000.0
    redline_angle = 40 + (redline_norm * 240)
    rad = math.radians(redline_angle)
    x1 = cx + math.cos(rad) * (r - arc_width - 4)
    y1 = cy + math.sin(rad) * (r - arc_width - 4)
    x2 = cx + math.cos(rad) * (r - arc_width - 28)
    y2 = cy + math.sin(rad) * (r - arc_width - 28)
    canvas.create_line(x1+1, y1+1, x2+1, y2+1, fill="#330000", width=7)
    canvas.create_line(x1, y1, x2, y2, fill="#ff0000", width=6)
    
    # Tick marks and numbers
    for i in range(0, 9):
        rpm_val = i * 1000
        norm = rpm_val / 8000.0
        angle_deg = 40 + (norm * 240)
        rad = math.radians(angle_deg)
        
        # Color coding for redline zone
        is_redline = rpm_val >= 7000
        tick_color = "#ff9999" if is_redline else "#ffffff"
        text_color = "#ffaaaa" if is_redline else "#f5f5f5"
        
        # Major ticks with shadow
        x1 = cx + math.cos(rad) * (r - arc_width - 4)
        y1 = cy + math.sin(rad) * (r - arc_width - 4)
        x2 = cx + math.cos(rad) * (r - arc_width - 20)
        y2 = cy + math.sin(rad) * (r - arc_width - 20)
        canvas.create_line(x1+1, y1+1, x2+1, y2+1, fill="#000000", width=4)
        canvas.create_line(x1, y1, x2, y2, fill=tick_color, width=3)
        
        # Numbers with shadow for depth
        tx = cx + math.cos(rad) * (r - arc_width - 42)
        ty = cy + math.sin(rad) * (r - arc_width - 42)
        canvas.create_text(tx+1, ty+1, text=str(i),
                         fill="#000000", font=("Arial", 17, "bold"))
        canvas.create_text(tx, ty, text=str(i),
                         fill=text_color, font=("Arial", 17, "bold"))
    
    # Minor ticks (500 RPM intervals)
    for i in range(0, 16):
        rpm_val = i * 500
        if rpm_val % 1000 != 0:
            norm = rpm_val / 8000.0
            angle_deg = 40 + (norm * 240)
            rad = math.radians(angle_deg)
            
            x1 = cx + math.cos(rad) * (r - arc_width - 4)
            y1 = cy + math.sin(rad) * (r - arc_width - 4)
            x2 = cx + math.cos(rad) * (r - arc_width - 12)
            y2 = cy + math.sin(rad) * (r - arc_width - 12)
            canvas.create_line(x1, y1, x2, y2, fill="#888888", width=2)
    
    # Premium needle with realistic appearance
    norm = min(1.0, disp_rpm / 8000.0)
    needle_angle = 40 + (norm * 240)
    rad = math.radians(needle_angle)
    
    needle_length = r - 32
    nx = cx + math.cos(rad) * needle_length
    ny = cy + math.sin(rad) * needle_length
    
    # Needle shadow
    canvas.create_line(cx+3, cy+3, nx+3, ny+3, fill="#000000", width=6, capstyle="round")
    
    # Optimized needle with conditional glow
    if disp_rpm > 6500:
        # Redline glow
        canvas.create_line(cx, cy, nx, ny, fill="#ff0000", width=10)
        # Red needle
        canvas.create_line(cx, cy, nx, ny, fill="#cc0000", width=5, capstyle="round")
        canvas.create_line(cx, cy, nx, ny, fill="#ff0000", width=3, capstyle="round")
    elif disp_rpm > 5000:
        # High RPM glow
        canvas.create_line(cx, cy, nx, ny, fill="#ff8800", width=8)
        # Green needle
        canvas.create_line(cx, cy, nx, ny, fill="#00cc66", width=5, capstyle="round")
        canvas.create_line(cx, cy, nx, ny, fill="#00ff88", width=3, capstyle="round")
    else:
        # Normal - green needle only
        canvas.create_line(cx, cy, nx, ny, fill="#00cc66", width=5, capstyle="round")
        canvas.create_line(cx, cy, nx, ny, fill="#00ff88", width=3, capstyle="round")
    
    # Needle center cap - metallic appearance
    canvas.create_oval(cx-16, cy-16, cx+16, cy+16, fill="#1a1a1a", outline="#444444", width=2)
    canvas.create_oval(cx-12, cy-12, cx+12, cy+12, fill="#2a2a2a", outline="#555555", width=1)
    canvas.create_oval(cx-8, cy-8, cx+8, cy+8, fill="#3a3a3a", outline="")
    canvas.create_oval(cx-4, cy-4, cx+4, cy+4, fill="#555555", outline="")
    # Highlight for metallic effect
    canvas.create_oval(cx-3, cy-6, cx+1, cy-2, fill="#888888", outline="")
    
    # Digital display with glow
    rpm_display = int(disp_rpm)
    display_color = "#ff3333" if rpm_display > 6500 else "#00ff88"
    shadow_color = "#330000" if rpm_display > 6500 else "#003320"
    glow_color = "#ff6666" if rpm_display > 6500 else "#00cc66"
    
    # Outer glow
    canvas.create_text(cx+3, cy-15, text=str(rpm_display),
                      fill=shadow_color, font=("Arial", 75, "bold"))
    # Inner glow
    canvas.create_text(cx+1, cy-17, text=str(rpm_display),
                      fill=glow_color, font=("Arial", 73, "bold"))
    # Main display
    canvas.create_text(cx, cy-18, text=str(rpm_display),
                      fill=display_color, font=("Arial", 70, "bold"))
    
    # Unit label
    canvas.create_text(cx, cy+34, text="RPM",
                      fill="#a0a0a0", font=("Arial", 15))
    
    # Bottom label
    canvas.create_text(cx, cy+r-46, text="ENGINE",
                      fill="#7a7a7a", font=("Arial", 12, "bold"))

# ================= CENTER DISPLAY =================
def draw_center_display(cx, cy):
    # Top info bar - clean design
    canvas.create_rectangle(cx-200, 25, cx+200, 65,
                           fill="#0a0a0a", outline="#2a2a2a", width=2)
    
    # Time display
    canvas.create_text(cx-120, 45, text=time_str,
                      fill="#ffffff", font=("Arial", 22, "bold"))
    
    # Engine status
    engine_status = "ENGINE ON" if engine_started else "ENGINE OFF"
    status_color = "#00ff88" if engine_started else "#ff3333"
    canvas.create_text(cx+120, 45, text=engine_status,
                      fill=status_color, font=("Arial", 14, "bold"))
    
    # Gear display configurations
    gear_configs = {
        "P": ("#999999", "#1a1a1a", "#2a2a2a"),
        "R": ("#ff3333", "#330000", "#ff3333"),
        "N": ("#ffdd00", "#332a00", "#ffdd00"),
        "D": ("#00ff88", "#003322", "#00ff88")
    }
    text_color, bg_color, border_color = gear_configs.get(gear, ("#ffffff", "#0a0a0a", "#2a2a2a"))
    
    gear_size = 140
    gear_y = cy - 140
    
    # Outer border for active gears
    if gear in ["D", "R", "N"]:
        canvas.create_rectangle(cx-gear_size/2-5, gear_y-gear_size/2-5,
                              cx+gear_size/2+5, gear_y+gear_size/2+5,
                              fill="", outline=border_color, width=2)
    
    # Main gear box
    canvas.create_rectangle(cx-gear_size/2, gear_y-gear_size/2,
                          cx+gear_size/2, gear_y+gear_size/2,
                          fill=bg_color, outline=border_color, width=3)
    
    # Gear letter
    canvas.create_text(cx, gear_y, text=gear,
                      fill=text_color, font=("Arial", 95, "bold"))
    
    # Drive mode indicator
    mode_y = gear_y + 95
    canvas.create_rectangle(cx-65, mode_y-15, cx+65, mode_y+15,
                           fill="#1a0a00", outline="#ff6600", width=2)
    canvas.create_text(cx, mode_y, text="⚡ SPORT",
                      fill="#ff8800", font=("Arial", 14, "bold"))
    
    # Odometer - simple and clean
    odo_y = cy + 20
    canvas.create_text(cx, odo_y, text=f"ODO",
                      fill="#4a4a4a", font=("Arial", 11, "bold"))
    canvas.create_text(cx, odo_y+22, text=f"{odo:,}",
                      fill="#ffffff", font=("Arial", 18, "bold"))
    canvas.create_text(cx+65, odo_y+22, text="km",
                      fill="#6b7280", font=("Arial", 12))
    
    # Trip meter
    canvas.create_text(cx, odo_y+48, text=f"TRIP  {trip:.1f} km",
                      fill="#6b7280", font=("Arial", 13))
    
    # Fuel gauge - clean bars
    fuel_y = cy + 105
    bar_w, bar_h = 240, 18
    
    canvas.create_text(cx-bar_w/2-25, fuel_y+1, text="⛽",
                      fill="#888888", font=("Arial", 18))
    
    canvas.create_rectangle(cx-bar_w/2, fuel_y-bar_h/2,
                          cx+bar_w/2, fuel_y+bar_h/2,
                          outline="#2a2a2a", width=2, fill="#0a0a0a")
    
    # Fuel segments
    segments = 10
    seg_w = (bar_w - 8) / segments
    for i in range(segments):
        if (i + 1) * 10 <= fuel:
            if fuel < 20:
                seg_color = "#ff3333"
            elif fuel < 40:
                seg_color = "#ffaa00"
            else:
                seg_color = "#00ff88"
            
            x1 = cx - bar_w/2 + 4 + i * seg_w
            canvas.create_rectangle(x1, fuel_y-bar_h/2+4,
                                  x1+seg_w-2, fuel_y+bar_h/2-4,
                                  fill=seg_color, outline="")
    
    fuel_color = "#ff3333" if fuel < 20 else "#ffaa00" if fuel < 40 else "#00ff88"
    canvas.create_text(cx+bar_w/2+30, fuel_y+1, text=f"{int(fuel)}%",
                      fill=fuel_color, font=("Arial", 12, "bold"))
    
    # Temperature gauge - clean
    temp_y = fuel_y + 40
    canvas.create_text(cx-bar_w/2-25, temp_y+1, text="🌡",
                      fill="#888888", font=("Arial", 18))
    
    canvas.create_rectangle(cx-bar_w/2, temp_y-bar_h/2,
                          cx+bar_w/2, temp_y+bar_h/2,
                          outline="#2a2a2a", width=2, fill="#0a0a0a")
    
    # Temperature fill
    temp_norm = max(0, min(1, (temp - 60) / 60))
    temp_w = (bar_w - 8) * temp_norm
    
    if temp > 105:
        temp_color = "#ff3333"
    elif temp > 95:
        temp_color = "#ffaa00"
    else:
        temp_color = "#00aaff"
    
    if temp_w > 0:
        canvas.create_rectangle(cx-bar_w/2+4, temp_y-bar_h/2+4,
                              cx-bar_w/2+4+temp_w, temp_y+bar_h/2-4,
                              fill=temp_color, outline="")
    
    canvas.create_text(cx+bar_w/2+35, temp_y+1, text=f"{int(temp)}°",
                      fill=temp_color, font=("Arial", 12, "bold"))

# ================= WARNING INDICATORS =================
def draw_indicator_light(x, y, symbol, active, color, label, size=26):
    if active:
        # Multiple glow rings for premium effect
        canvas.create_oval(x-size-6, y-size-6, x+size+6, y+size+6,
                          fill="", outline=color, width=2)
        canvas.create_oval(x-size-3, y-size-3, x+size+3, y+size+3,
                          fill="", outline=color, width=1)
        
        # Main indicator body
        canvas.create_oval(x-size, y-size, x+size, y+size,
                          fill=color, outline="")
        
        # Bright center for glass dome effect
        canvas.create_oval(x-size//2, y-size//2, x+size//2, y+size//2,
                          fill=color, outline="")
        
        # Glass highlight
        canvas.create_arc(x-size+4, y-size+4, x+size-4, y+size-4,
                         start=45, extent=90, fill="", outline="#ffffff",
                         width=2, style="arc")
        
        symbol_color = "#000000"
        label_color = color
    else:
        # Inactive - recessed look
        canvas.create_oval(x-size, y-size, x+size, y+size,
                          fill="#0f0f0f", outline="#2a2a2a", width=2)
        canvas.create_oval(x-size+2, y-size+2, x+size-2, y+size-2,
                          fill="#0a0a0a", outline="#151515", width=1)
        symbol_color = "#2a2a2a"
        label_color = "#2a2a2a"
    
    # Symbol with shadow
    canvas.create_text(x+1, y+1, text=symbol,
                      fill="#000000", font=("Arial", 15, "bold"))
    canvas.create_text(x, y, text=symbol,
                      fill=symbol_color, font=("Arial", 15, "bold"))
    
    if label:
        canvas.create_text(x, y+size+11, text=label,
                          fill=label_color, font=("Arial", 7, "bold"))

def draw_all_indicators():
    indicator_y = 730
    spacing = 70
    start_x = 250
    
    indicators = [
        ("!", engine, "#ff0000", "CHECK"),
        ("🔋", battery, "#ff0000", "BATT"),
        ("🛢", oil_pressure, "#ffaa00", "OIL"),
        ("ABS", absw, "#ffaa00", ""),
        ("(P)", parking_brake, "#ff0000", "BRAKE"),
        ("⚠", airbag, "#ff0000", "BAG"),
        ("💺", seatbelt, "#ff0000", "BELT"),
        ("🚪", door, "#ff6600", "DOOR"),
        ("TPMS", tpms, "#ffaa00", ""),
        ("☀", high_beam, "#0099ff", "HIGH"),
        ("❄", False, "#0099ff", ""),
        ("⚙", False, "#4a4a4a", "SVC"),
    ]
    
    for i, (symbol, active, color, label) in enumerate(indicators):
        x = start_x + (i * spacing)
        draw_indicator_light(x, indicator_y, symbol, active, color, label)

# ================= TURN SIGNALS =================
def draw_turn_signals():
    signal_y = 400
    arrow_size = 40
    
    if (left or hazard) and blink_state:
        x_pos = 120
        
        points = [
            x_pos-arrow_size, signal_y,
            x_pos, signal_y-arrow_size//2,
            x_pos, signal_y-arrow_size//4,
            x_pos+arrow_size//2, signal_y-arrow_size//4,
            x_pos+arrow_size//2, signal_y+arrow_size//4,
            x_pos, signal_y+arrow_size//4,
            x_pos, signal_y+arrow_size//2
        ]
        
        # Glow layers
        points_glow = [p-2 if i % 2 == 0 else p for i, p in enumerate(points)]
        canvas.create_polygon(points_glow, fill="#00aa00", outline="")
        points_glow2 = [p-1 if i % 2 == 0 else p for i, p in enumerate(points)]
        canvas.create_polygon(points_glow2, fill="#00ff00", outline="")
        
        # Main arrow
        canvas.create_polygon(points, fill="#00ff00", outline="")
    
    if (right or hazard) and blink_state:
        x_pos = 1480
        
        points = [
            x_pos+arrow_size, signal_y,
            x_pos, signal_y-arrow_size//2,
            x_pos, signal_y-arrow_size//4,
            x_pos-arrow_size//2, signal_y-arrow_size//4,
            x_pos-arrow_size//2, signal_y+arrow_size//4,
            x_pos, signal_y+arrow_size//4,
            x_pos, signal_y+arrow_size//2
        ]
        
        # Glow layers
        points_glow = [p+2 if i % 2 == 0 else p for i, p in enumerate(points)]
        canvas.create_polygon(points_glow, fill="#00aa00", outline="")
        points_glow2 = [p+1 if i % 2 == 0 else p for i, p in enumerate(points)]
        canvas.create_polygon(points_glow2, fill="#00ff00", outline="")
        
        # Main arrow
        canvas.create_polygon(points, fill="#00ff00", outline="")

# ================= CONTROLS DISPLAY =================
def draw_controls_help():
    """Display keyboard controls on screen"""
    help_x = W - 200
    help_y = 100
    
    canvas.create_text(help_x, help_y, text="CONTROLS",
                      fill="#6b7280", font=("Arial", 12, "bold"))
    
    controls = [
        "E - Engine On/Off",
        "G - Change Gear",
        "↑/W - Accelerate",
        "↓ - Brake",
        "← - Left Turn",
        "→ - Right Turn",
        "H - Hazard",
        "B - High Beam",
        "P - Park Brake",
        "D - Door",
        "T - Seatbelt"
    ]
    
    for i, text in enumerate(controls):
        canvas.create_text(help_x, help_y + 25 + i*20, text=text,
                          fill="#4a4a4a", font=("Arial", 9))

# ================= RENDER =================
def render():
    global disp_speed, disp_rpm, blink_state, blink_counter, last_turn_signal_blink

    try:
        # Update controls
        update_controls()
        
        # Update physics simulation
        update_vehicle_physics()
        
        # Play engine sound (silently in background)
        if AUDIO_ENABLED and engine_started and rpm > 500:
            play_engine_sound(rpm, throttle)
        
        # Smooth display values with bounds checking
        disp_speed = max(0, min(260, lerp(disp_speed, speed)))
        disp_rpm = max(0, min(8000, lerp(disp_rpm, rpm)))
        
        blink_counter += 1
        if blink_counter >= 10:
            blink_state = not blink_state
            blink_counter = 0
            
            # Turn signal sound on state change
            if AUDIO_ENABLED and blink_state and (left or right):
                play_turn_signal_sound()

        canvas.delete("all")
        
        # Draw all components with error handling
        draw_speedometer(350, 400, 240)
        draw_tachometer(1250, 400, 240)
        draw_center_display(800, 400)
        draw_all_indicators()
        draw_turn_signals()
        draw_controls_help()
        
    except Exception as e:
        print(f"Render error: {e}")
        # Continue rendering even if there's an error
    
    # Schedule next frame (40ms = 25 FPS for stability)
    try:
        root.after(40, render)
    except:
        pass

# ================= CAN RECEIVER =================
def read_can():
    """Listen for external CAN messages with rate limiting"""
    global speed, rpm, gear, fuel, temp
    global engine, absw, door, left, right, seatbelt
    global battery, oil_pressure, parking_brake, high_beam, tpms, airbag

    try:
        # Process up to 10 messages per cycle to prevent overwhelming
        for _ in range(10):
            msg = bus.recv(timeout=0.0001)
            if msg:
                # Validate data length
                if len(msg.data) > 0:
                    d = msg.data[0]
                    # Only accept external messages (not our own echoes)
                    # Add bounds checking for safety
                    if msg.arbitration_id == 0x110:
                        speed = max(0, min(260, d))
                    elif msg.arbitration_id == 0x111:
                        rpm = max(0, min(8000, d * 100))
                    elif msg.arbitration_id == 0x112: 
                        gear_idx = d if d < 4 else 0
                        gear = ["P","R","N","D"][gear_idx]
                    elif msg.arbitration_id == 0x113:
                        fuel = max(0, min(100, d))
                    elif msg.arbitration_id == 0x114:
                        temp = max(0, min(150, d))
            else:
                break  # No more messages, exit loop
    except Exception as e:
        pass  # Silently handle CAN errors

    # Schedule next CAN read
    try:
        root.after(5, read_can)
    except:
        pass

# ================= START =================
print("=== Interactive Dashboard Started ===")
if AUDIO_ENABLED:
    print("✓ Audio enabled - Engine and indicator sounds active")
else:
    print("ℹ Audio disabled for optimal performance")
    if not ENABLE_AUDIO_ATTEMPT:
        print("  To enable audio: Edit main-dash.py and set ENABLE_AUDIO_ATTEMPT = True")
print("")
print("Controls:")
print("  E - Engine Start/Stop")
print("  G - Change Gear (P→R→N→D)")
print("  ↑/W - Accelerate")
print("  ↓ - Brake")
print("  ← - Left Turn Signal")
print("  → - Right Turn Signal")
print("  H - Hazard Lights")
print("  B - High Beam")
print("  P - Parking Brake")
print("  D - Door Open/Close")
print("  T - Seatbelt Toggle")
print("")
print("CAN Messages being sent on vcan0:")
print("  0x100 - Speed")
print("  0x101 - RPM")
print("  0x102 - Gear")
print("  0x103 - Fuel")
print("  0x104 - Temperature")
print("  0x200-0x208 - Warning Indicators")
print("  0x300-0x302 - Turn Signals & Door")
print("")
print("Use 'candump vcan0' to monitor CAN traffic")

render()
read_can()
root.mainloop()

# Cleanup audio on exit
if AUDIO_ENABLED:
    try:
        audio.terminate()
    except:
        pass