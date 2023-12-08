if __name__ == "__main__":
    import traceback
    from queue import Queue
    from threading import Event

    from camera_stream import detect_faces
    from controls import solenoid

    hardware = Event()
    name_queue = Queue()

    detect_thread = detect_faces.detect_and_stream_thread(
        hardware_event=hardware, name_queue=name_queue, read_from="Capture-OCV"
    )
    solenoid_thread = solenoid.solenoid_thread(
        hardware_event=hardware, queue=name_queue
    )
    detect_thread.start()
    solenoid_thread.start()

    def quit(detect_thread, solenoid_thread):
        print("Releasing detecting and streaming thread")
        detect_thread.quit()
        print("Releasing solenoid thread")
        solenoid_thread.quit()

        print("Joining threads")
        detect_thread.join()
        solenoid_thread.join()

        print("Joined threads")

    try:
        while input("Quit? [y/n]: ") != "y":
            ...
        quit(detect_thread, solenoid_thread)
    except BaseException as e:
        traceback.print_exception(e)
        quit(detect_thread, solenoid_thread)
