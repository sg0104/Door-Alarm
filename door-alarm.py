
from gpiozero import DistanceSensor, Button, Buzzer
from time import sleep
from statistics import median
from datetime import datetime

# Component setup
ultrasonic = DistanceSensor(
    echo=18,
    trigger=17,
    max_distance=2
)

button = Button(27, pull_up=True, bounce_time=0.1)
buzzer = Buzzer(22)

# Alarm settings
TOLERANCE = 5
CHECK_INTERVAL = 0.1

armed = False
closed_distance = None
door_open = False

# Record events
def log_event(message):
    time = datetime.now().strftime("%H:%M:%S")
    entry = f"[{time}] {message}"
    print("\n" + entry)

    with open("alarm_log.txt", "a") as file:
        file.write(entry + "\n")

# Read ultrasonic distance
def get_distance():
    return ultrasonic.distance * 100

# Calibrate closed-door position
def calibrate():
    print("\nCalibrating sensor...")
    print("Keep both doors closed.")

    readings = []

    for i in range(10):
        readings.append(get_distance())
        sleep(0.1)

    baseline = median(readings)

    print(f"Closed distance: {baseline:.1f} cm")
    return baseline

# Button controls alarm power state
def toggle_alarm():
    global armed, closed_distance, door_open

    if armed:
        armed = False
        buzzer.off()
        door_open = False
        log_event("Alarm DISARMED")

    else:
        closed_distance = calibrate()
        door_open = False
        armed = True
        log_event("Alarm ARMED")

# Button event
button.when_pressed = toggle_alarm

print("UNIVERSAL DOOR ALARM")
print("Press button to ARM or DISARM")
print("System currently DISARMED")

try:
    while True:
        if armed and closed_distance is not None:
            distance = get_distance()

            difference = abs(distance - closed_distance)

            if difference > TOLERANCE:
                buzzer.on()

                if not door_open:
                    door_open = True
                    log_event("DOOR OPEN - ALARM ON")

            else:
                buzzer.off()

                if door_open:
                    door_open = False
                    log_event("DOOR CLOSED - ALARM OFF")

        sleep(CHECK_INTERVAL)

except KeyboardInterrupt:
    print("\nProgram stopped")

finally:
    buzzer.off()
    button.close()
    ultrasonic.close()
    buzzer.close()


