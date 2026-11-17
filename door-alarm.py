from gpiozero import DistanceSensor, Button, Buzzer, OutputDevice
from time import sleep
from datetime import datetime
from statistics import median
import os

# Save the log next to this script, no matter where it's started from
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alarm_log.txt")

# Component setup

ultrasonic = DistanceSensor(
    echo=18,
    trigger=17,
    max_distance=2
)

tilt = Button(23, pull_up=True)
button = Button(27, pull_up=True, bounce_time=0.1)
# ===== BUZZER SETTING =====
# True  = normal buzzer (turns ON when pin is HIGH)
# False = "reverse" buzzer (turns ON when pin is LOW)
# If the buzzer beeps NONSTOP even before you press the button, flip this.
BUZZER_ACTIVE_HIGH = True

buzzer = Buzzer(22, active_high=BUZZER_ACTIVE_HIGH, initial_value=False)

# ===== VIBRATOR SETTING =====
# True  = normal vibrator (turns ON when pin is HIGH)  <-- try this first
# False = "reverse" vibrator (turns ON when pin is LOW)
# If the vibrator does the OPPOSITE of what it should, flip this.
VIBRATOR_ACTIVE_HIGH = True

vibrator = OutputDevice(
    25,
    active_high=VIBRATOR_ACTIVE_HIGH,
    initial_value=False
)


# Alarm settings

TOLERANCE = 5          # how many cm the object must move to set off the alarm
TRIGGER_COUNT = 3      # readings in a row needed (stops false alarms from glitches)
CHECK_INTERVAL = 0.1
MAX_CM = 200           # sensor's max range (max_distance=2 metres)

moved_count = 0
tilt_count = 0

armed = False
door_open = False
closed_distance = None
normal_tilt = None
last_button_state = False

# Record events

def log_event(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] {message}"

    print("\n" + entry)

    with open(LOG_FILE, "a") as file:
        file.write(entry + "\n")

# Read ultrasonic sensor

def get_distance():
    return ultrasonic.distance * 100

# Calibrate both sensors

def calibrate():
    print("\nCalibrating sensors...")
    print("Keep the door closed and still.")

    readings = []

    for i in range(10):
        readings.append(get_distance())
        sleep(0.1)

    baseline_distance = median(readings)
    baseline_tilt = tilt.is_pressed

    print(f"Closed distance: {baseline_distance:.1f} cm")
    print(f"Normal tilt state: {baseline_tilt}")

    if baseline_distance >= MAX_CM - 5:
        print("WARNING: Ultrasonic sensor can't see the object!")
        print("Point it straight at the object (2 cm to 2 m away)")
        print("and check the Trig/Echo wires.")
    elif baseline_distance < 3:
        print("WARNING: Object is too close to the sensor.")
        print("Move it at least 3 cm away.")

    return baseline_distance, baseline_tilt

# Arm and disarm alarm

def toggle_alarm():
    global armed, door_open, moved_count, tilt_count
    moved_count = 0
    tilt_count = 0
    global closed_distance, normal_tilt

    if armed:
        armed = False
        door_open = False
        buzzer.off()
        vibrator.off()
        log_event("Alarm DISARMED")

    else:
        closed_distance, normal_tilt = calibrate()
        door_open = False
        armed = True
        log_event("Alarm ARMED")

# Main program

print("UNIVERSAL DOOR ALARM")
print("Press the button to ARM or DISARM")
print("System currently DISARMED")

# Make sure outputs start off
buzzer.off()
vibrator.off()

# Quick startup test: vibrator should buzz for 1 second, then stop.
# If it does the opposite (silent, then buzzes nonstop),
# change VIBRATOR_ACTIVE_HIGH at the top of the file.
print("Testing buzzer for 1 second...")
buzzer.on()
sleep(1)
buzzer.off()
print("Testing vibrator for 1 second...")
vibrator.on()
sleep(1)
vibrator.off()
print("Startup test done - both should now be QUIET")

status_timer = 0

try:
    while True:

        # Check push button

        button_state = button.is_pressed

        if button_state and not last_button_state:
            toggle_alarm()

        last_button_state = button_state

        # Check sensors when armed

        if armed:
            distance = get_distance()
            current_tilt = tilt.is_pressed

            # Count how many readings in a row the object has moved
            if abs(distance - closed_distance) > TOLERANCE:
                moved_count += 1
            else:
                moved_count = 0

            distance_changed = moved_count >= TRIGGER_COUNT

            # Same for tilt (tilt switches can flicker)
            if current_tilt != normal_tilt:
                tilt_count += 1
            else:
                tilt_count = 0

            tilt_changed = tilt_count >= TRIGGER_COUNT

            # Show live readings once a second so you can see what's happening
            status_timer += 1
            if status_timer >= 10:
                status_timer = 0
                dist_status = "MOVED" if distance_changed else "ok"
                tilt_status = "MOVED" if tilt_changed else "ok"
                print(
                    f"Distance: {distance:.1f} cm "
                    f"(closed was {closed_distance:.1f}) [{dist_status}]  |  "
                    f"Tilt: {tilt_status}"
                )

            if distance_changed or tilt_changed:
                buzzer.on()
                vibrator.on()

                if not door_open:
                    door_open = True
                    log_event("DOOR OPEN - ALARM ON")

                    if distance_changed:
                        log_event("Ultrasonic sensor triggered")

                    if tilt_changed:
                        log_event("Tilt sensor triggered")

            else:
                buzzer.off()
                vibrator.off()
                if door_open:
                    door_open = False
                    log_event("DOOR CLOSED - ALARM OFF")

        else:
            buzzer.off()
            vibrator.off()

        sleep(CHECK_INTERVAL)

except KeyboardInterrupt:
    print("\nProgram stopped")

finally:
    buzzer.off()
    vibrator.off()
    ultrasonic.close()
    tilt.close()
    button.close()
    buzzer.close()
    vibrator.close()

