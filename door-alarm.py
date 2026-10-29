from gpiozero import DistanceSensor, Button, Buzzer
from time import sleep
from statistics import median

# Set up components
ultrasonic = DistanceSensor(
    echo=18,
    trigger=17,
    max_distance=2
)

tilt = Button(27, pull_up=True)
buzzer = Buzzer(22)

# Alarm settings
TOLERANCE = 5       # Distance change in cm
REQUIRED_READINGS = 3

print("Close the doors before calibration.")
input("Press Enter when ready...")

# Measure the closed-door distance
readings = []

for i in range(10):
    readings.append(ultrasonic.distance * 100)
    sleep(0.2)

closed_distance = median(readings)

print(f"Calibrated distance: {closed_distance:.1f} cm")
print("Alarm armed!")

change_count = 0

try:
    while True:
        distance = ultrasonic.distance * 100

        # Detect target movement
        distance_changed = (
            abs(distance - closed_distance) > TOLERANCE
        )

        # Detect tilt switch activation
        tilt_detected = tilt.is_pressed

        if distance_changed or tilt_detected:
            change_count += 1
        else:
            change_count = 0

        if change_count >= REQUIRED_READINGS:
            buzzer.on()
            print("ALARM! Door opened!")

        else:
            buzzer.off()
            print(f"Door closed | Distance: {distance:.1f} cm")

        sleep(0.2)

except KeyboardInterrupt:
    print("Alarm stopped.")

finally:
    buzzer.off()
    ultrasonic.close()
    tilt.close()
    buzzer.close()

