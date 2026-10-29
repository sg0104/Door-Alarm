
from gpiozero import Button
from time import sleep

tilt = Button(27, pull_up=True)

print("Tilt Sensor Test Started")
print("Move or tilt the sensor to test it")
print("Press Ctrl+C to stop")

try:
    while True:
        if tilt.is_pressed:
            print("TILT DETECTED")
        else:
            print("NORMAL POSITION")

        sleep(0.2)

except KeyboardInterrupt:
    print("Test stopped")

finally:
    tilt.close()
