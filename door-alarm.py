from gpiozero import DistanceSensor, Button, Buzzer, OutputDevice
from time import sleep, monotonic
from datetime import datetime
from statistics import median

# ===== SETTINGS (change these if something acts backwards) =====

# Your buzzer and vibrator are the "reverse" kind (they turn ON when
# the pin is LOW), so these are set to False.
BUZZER_ACTIVE_HIGH = False
VIBRATOR_ACTIVE_HIGH = False

# If the ON/OFF switch works backwards, change True to False
SWITCH_ON_WHEN_PRESSED = True

# Vibrate when you press the time button.
# OFF for now: the vibrator pulls too much power and reboots the Pi.
# Only change to True after the vibrator is wired through a transistor.
VIBRATE_ON_MODE_CHANGE = True
VIBRATE_TIME = 0.3

TOLERANCE = 5                # cm the object must move to set off the alarm
TIME_MODES = [1, 5, 10, 15]  # hours
ARM_DELAY = 3                # seconds after your last time-button press before it arms
CHECK_INTERVAL = 0.1

# ===== Component setup =====

ultrasonic = DistanceSensor(echo=18, trigger=17, max_distance=2)

power_switch = Button(27, pull_up=True, bounce_time=0.1)  # ON / OFF
mode_button = Button(24, pull_up=True, bounce_time=0.1)   # pick time
buzzer = Buzzer(22, active_high=BUZZER_ACTIVE_HIGH, initial_value=False)
vibrator = OutputDevice(25, active_high=VIBRATOR_ACTIVE_HIGH, initial_value=False)

# ===== State =====

system_on = False
mode_index = -1           # -1 = no time picked yet
last_mode_press = None    # when the time button was last pressed
armed = False
door_open = False
closed_distance = None
arm_end_time = None
last_mode_state = False

# ===== Helpers =====

def log_event(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] {message}"
    print("\n" + entry)
    with open("alarm_log.txt", "a") as file:
        file.write(entry + "\n")

def beep(times):
    for i in range(times):
        buzzer.on()
        sleep(0.15)
        buzzer.off()
        sleep(0.15)

def get_distance():
    return ultrasonic.distance * 100

def calibrate():
    print("\nCalibrating sensor... keep the door closed and still.")
    readings = []
    for i in range(10):
        readings.append(get_distance())
        sleep(0.1)
    baseline = median(readings)
    print(f"Closed distance: {baseline:.1f} cm")
    return baseline

def switch_is_on():
    if SWITCH_ON_WHEN_PRESSED:
        return power_switch.is_pressed
    return not power_switch.is_pressed

def everything_off():
    global armed, door_open, mode_index, last_mode_press
    armed = False
    door_open = False
    mode_index = -1
    last_mode_press = None
    buzzer.off()
    vibrator.off()

def pick_next_time():
    global mode_index, last_mode_press, armed, door_open

    # Picking a new time cancels the current countdown until it re-arms
    armed = False
    door_open = False
    buzzer.off()

    mode_index = (mode_index + 1) % len(TIME_MODES)
    last_mode_press = monotonic()
    print(f"\nTime picked: {TIME_MODES[mode_index]} hour(s) "
          f"(arms in {ARM_DELAY} seconds)")

    if VIBRATE_ON_MODE_CHANGE:
        vibrator.on()
        sleep(VIBRATE_TIME)
        vibrator.off()

    beep(mode_index + 1)   # 1 beep = 1h, 2 = 5h, 3 = 10h, 4 = 15h

def arm():
    global armed, door_open, closed_distance, arm_end_time, last_mode_press
    closed_distance = calibrate()
    hours = TIME_MODES[mode_index]
    arm_end_time = monotonic() + hours * 3600
    door_open = False
    armed = True
    last_mode_press = None
    log_event(f"Alarm ARMED for {hours} hour(s)")

# ===== Main program =====

print("UNIVERSAL DOOR ALARM")
print("Switch (GPIO 27): ON / OFF")
print("Time button (GPIO 24): pick 1, 5, 10 or 15 hours")

everything_off()

try:
    while True:
        try:

            # ---- ON/OFF switch ----
            if switch_is_on() and not system_on:
                system_on = True
                log_event("System ON - press the time button to pick a time")

            elif not switch_is_on() and system_on:
                system_on = False
                everything_off()
                log_event("System OFF")

            if not system_on:
                buzzer.off()
                vibrator.off()
                last_mode_state = mode_button.is_pressed
                sleep(CHECK_INTERVAL)
                continue

            # ---- Time button ----
            mode_state = mode_button.is_pressed
            if mode_state and not last_mode_state:
                pick_next_time()
            last_mode_state = mode_state

            # ---- Arm a few seconds after the last time-button press ----
            if (not armed and last_mode_press is not None
                    and monotonic() - last_mode_press >= ARM_DELAY):
                arm()

            # ---- Watch the door while armed ----
            if armed:
                if monotonic() >= arm_end_time:
                    armed = False
                    door_open = False
                    mode_index = -1
                    buzzer.off()
                    log_event("Time finished - press the time button to start again")

                else:
                    distance = get_distance()

                    if abs(distance - closed_distance) > TOLERANCE:
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
        except Exception as error:
            # Never crash: keep everything quiet and show the error
            buzzer.off()
            vibrator.off()
            log_event(f"ERROR (program kept running): {error}")
            sleep(1)

except KeyboardInterrupt:
    print("\nProgram stopped")

finally:
    buzzer.off()
    vibrator.off()
    ultrasonic.close()
    power_switch.close()
    mode_button.close()
    buzzer.close()
    vibrator.close()
