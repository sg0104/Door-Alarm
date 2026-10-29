
from gpiozero import DistanceSensor, Button, Buzzer
from time import sleep
from datetime import datetime
from statistics import median

# Component setup

ultrasonic = DistanceSensor(
    echo=18,
    trigger=17,
    max_distance=2
)

tilt = Button(23, pull_up=True)
button = Button(27, pull_up=True, bounce_time=0.1)
buzzer = Buzzer(22)

# Alarm settings

TOLERANCE = 5
CHECK_INTERVAL = 0.1

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

    with open("alarm_log.txt", "a") as file:
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

    return baseline_distance, baseline_tilt

# Arm and disarm alarm

def toggle_alarm():
    global armed, door_open
    global closed_distance, normal_tilt

    if armed:
        armed = False
        door_open = False
        buzzer.off()
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

            distance_changed = (
                abs(distance - closed_distance) > TOLERANCE
            )

            tilt_changed = (
                current_tilt != normal_tilt
            )

            if distance_changed or tilt_changed:
                buzzer.on()

                if not door_open:
                    door_open = True
                    log_event("DOOR OPEN - ALARM ON")

                    if distance_changed:
                        log_event("Ultrasonic sensor triggered")

                    if tilt_changed:
                        log_event("Tilt sensor triggered")

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
    ultrasonic.close()
    tilt.close()
    button.close()
    buzzer.close()
