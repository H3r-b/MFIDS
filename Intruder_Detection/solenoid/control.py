import traceback
from queue import Queue
from threading import Event
from time import sleep

solenoid_running = Event()
solenoid_running.set()


def solenoid_loop(activate: Event, queue: Queue):
    global solenoid_running
    while solenoid_running.is_set():
        try:
            activate.wait()
            print("Opening Door for:", queue.get())
            sleep(8.5)
            print("Closing Door")
            activate.clear()
        except BaseException as e:
            traceback.print_exception(e)
            break
