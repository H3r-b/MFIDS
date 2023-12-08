import traceback
from dataclasses import dataclass
from os import uname
from queue import Queue
from threading import Event, Thread
from time import sleep

if linux := uname().sysname == "Linux":
    import RPi.GPIO as GPIO


class solenoid_thread(Thread):
    @dataclass
    class solenoid_settings:
        sleep_before_activation: float = 1.5
        wait_time_per_loop: float = 2.5
        sleep_after_activation: float = 5
        pre_activation_message: str = "Opening door for: {}"
        post_activation_message: str = "Closing door..."

    def __init__(
        self,
        hardware_event: Event,
        queue: Queue,
        sleep_before_activation: float = solenoid_settings.sleep_before_activation,
        wait_time_per_loop: float = solenoid_settings.wait_time_per_loop,
        sleep_after_activation: float = solenoid_settings.sleep_after_activation,
        pre_activation_message: str = solenoid_settings.pre_activation_message,
        post_activation_message: str = solenoid_settings.post_activation_message,
    ):
        super().__init__()

        # Check if running in pi
        self.linux = linux

        # Stopping thread on signal
        self.run_event = Event()
        self.run_event.set()
        # Event for hardware signals
        self.hardware_event = hardware_event
        # Communication between threads
        self.queue = queue

        # Initialize settings
        self.solenoid_settings.sleep_before_activation = sleep_before_activation
        self.solenoid_settings.wait_time_per_loop = wait_time_per_loop
        self.solenoid_settings.sleep_after_activation = sleep_after_activation
        self.solenoid_settings.pre_activation_message = pre_activation_message
        self.solenoid_settings.post_activation_message = post_activation_message

    def run(self) -> None:
        try:
            if self.linux:
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(19, GPIO.OUT)
            while self.run_event.is_set():
                sleep(self.solenoid_settings.sleep_before_activation)
                self.hardware_event.wait(
                    timeout=self.solenoid_settings.wait_time_per_loop
                )
                if self.hardware_event.is_set():
                    print(
                        self.solenoid_settings.pre_activation_message.format(
                            self.queue.get()
                        )
                    )
                    if self.linux:
                        GPIO.output(18, 1)
                    sleep(5)
                    print(self.solenoid_settings.post_activation_message)
                    if self.linux:
                        GPIO.output(18, 0)
                    self.hardware_event.clear()
        except BaseException as e:
            traceback.print_exception(e)
            self.quit()

    def quit(self):
        if self.is_alive():
            self.run_event.clear()
            while self.is_alive():
                sleep(0.01)
            if self.linux:
                GPIO.cleanup()
