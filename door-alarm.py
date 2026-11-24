from gpiozero import DistanceSensor, Button, Buzzer, OutputDevice
from time import sleep, monotonic
from datetime import datetime
from statistics import median

# Component setup

ultrasonic = DistanceSensor(
    echo=18,
    trigger=17,
    max_distance=2
)

button = Button(27, pull_up=True, bounce_time=0.1)       # ARM / DISARM
mode_button = Button(24, pull_up=True, bounce_time=0.1)  # change time mode
buzzer = Buzzer(22)
vibrator = OutputDevice(25)


# Alarm settings

TOLERANCE = 5
CHECK_INTERVAL = 0.1

VIBRATE_ON_MODE_CHANGE = True  # False = don't vibrate when changing modes
VIBRATE_TIME = 0.3             # seconds the vibrator buzzes

TIME_MODES = [1, 5, 10, 15]   # hours the alarm stays armed
mode_index = 0                # starts on 1 hour

armed = False
door_open = False
closed_distance = None
arm_end_time = None
last_button_state = False
last_mode_state = False

# Record events

def log_event(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] {message}"

    print("\n" + entry)

    with open("alarm_log.txt", "a") as file:
        file.write(entry + "\n")

# Short beeps (so you can hear the mode without a screen)

def beep(times):
    for i in range(times):
        buzzer.on()
        sleep(0.15)
        buzzer.off()
        sleep(0.15)

# Read ultrasonic sensor

def get_distance():
    return ultrasonic.distance * 100

# Calibrate sensor

def calibrate():
    print("\nCalibrating sensor...")
    print("Keep the door closed and still.")

    readings = []

    for i in range(10):
        readings.append(get_distance())
        sleep(0.1)

    baseline_distance = median(readings)

    print(f"Closed distance: {baseline_distance:.1f} cm")

    return baseline_distance

# Change time mode

def next_mode():
    global mode_index, arm_end_time

    mode_index = (mode_index + 1) % len(TIME_MODES)
    hours = TIME_MODES[mode_index]

    if armed:
        # Restart the timer with the new time
        arm_end_time = monotonic() + hours * 3600
        log_event(f"Time mode changed: alarm now on for {hours} hour(s) from now")
    else:
        print(f"\nTime mode: {hours} hour(s)")

    # Short vibration to confirm the button press
    if VIBRATE_ON_MODE_CHANGE:
        vibrator.on()
        sleep(VIBRATE_TIME)
        vibrator.off()

    beep(mode_index + 1)   # 1 beep = 1h, 2 = 5h, 3 = 10h, 4 = 15h

# Arm and disarm alarm

def disarm(reason="Alarm DISARMED"):
    global armed, door_open

    armed = False
    door_open = False
    buzzer.off()
    log_event(reason)

def toggle_alarm():
    global armed, door_open
    global closed_distance, arm_end_time

    if armed:
        disarm()

    else:
        closed_distance = calibrate()
        hours = TIME_MODES[mode_index]
        arm_end_time = monotonic() + hours * 3600
        door_open = False
        armed = True
        log_event(f"Alarm ARMED for {hours} hour(s)")

# Main program

print("UNIVERSAL DOOR ALARM")
print("Button 1 (GPIO 27): ARM or DISARM")
print("Button 2 (GPIO 24): change time mode")
print(f"Time mode: {TIME_MODES[mode_index]} hour(s)")
print("System currently DISARMED")

# Wiring check: neither button should read as pressed at startup
if button.is_pressed:
    print("\nWARNING: Button 1 (GPIO 27) reads as PRESSED without touching it!")
    print("Check its wiring - use DIAGONAL legs on a 4-leg button,")
    print("one to GPIO 27 and one to GND.")
if mode_button.is_pressed:
    print("\nWARNING: Button 2 (GPIO 24) reads as PRESSED without touching it!")
    print("Check its wiring - use DIAGONAL legs on a 4-leg button,")
    print("one to GPIO 24 and one to GND.")

# Start with the real button states so nothing triggers by itself
last_button_state = button.is_pressed
last_mode_state = mode_button.is_pressed

try:
    while True:

        # Check arm/disarm button

        button_state = button.is_pressed

        if button_state and not last_button_state:
            toggle_alarm()

        last_button_state = button_state

        # Check mode button

        mode_state = mode_button.is_pressed

        if mode_state and not last_mode_state:
            next_mode()

        last_mode_state = mode_state

        # Check sensor when armed

        if armed:

            # Time's up - turn the alarm off
            if monotonic() >= arm_end_time:
                disarm("Time finished - alarm DISARMED")

            else:
                distance = get_distance()

                distance_changed = (
                    abs(distance - closed_distance) > TOLERANCE
                )

                if distance_changed:
                    buzzer.on()

                    if not door_open:
                        door_open = True
                        log_event("DOOR OPEN - ALARM ON")

                else:
                    buzzer.off()
                    if door_open:
                        door_open = False
                        log_event("DOOR CLOSED - ALARM OFF")

        else:
            buzzer.off()

        sleep(CHECK_INTERVAL)

except KeyboardInterrupt:
    print("\nProgram stopped")

finally:
    buzzer.off()
    vibrator.off()
    vibrator.close()
    ultrasonic.close()
    button.close()
    mode_button.close()
    buzzer.close()
