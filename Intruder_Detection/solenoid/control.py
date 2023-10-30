import traceback
from queue import Queue
from threading import Event
from time import sleep
import os
linux = os.uname().sysname == "Linux"
if linux:
    import RPIO.GPIO as GPIO

solenoid_running = Event()
solenoid_running.set()


def solenoid_loop(activate: Event, queue: Queue):
    global solenoid_running, linux
    if linux:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(18, GPIO.OUT)
    while solenoid_running.is_set():
        try:
            activate.wait()
            print("Opening Door for:", queue.get())
            if linux:
                GPIO.output(18,1)
            sleep(8.5)
            print("Closing Door")
            if linux:
                GPIO.output(18,1)
            activate.clear()
        except BaseException as e:
            traceback.print_exception(e)
            break
