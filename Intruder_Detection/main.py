
if __name__ == "__main__":
    import traceback
    import threading
    import solenoid.control
    import camera_stream.detect_faces
    from queue import Queue
    
    hardware = threading.Event()
    name_queue = Queue()

    detect_thread = camera_stream.detect_faces.detect_and_stream_thread(hardware_event=hardware, name_queue=name_queue, read_from="Capture-OCV")
    solenoid_thread = threading.Thread(target=solenoid.control.solenoid_loop, kwargs={"activate": hardware, "queue": name_queue})
    detect_thread.start()
    solenoid_thread.start()
    
    def quit(detect_thread, solenoid_thread):
        print("Releasing detecting and streaming thread")
        print("Stopping server")
        detect_thread.quit()

        print("Setting to dont run")
        solenoid.control.solenoid_running.clear()
        
        print("Joining threads")
        detect_thread.join()
        solenoid_thread.join()
    
    while True:
        try:
            if input("Quit? [y/n]: ") == "y":
                quit(detect_thread, solenoid_thread)
                break
        except BaseException as e:
            traceback.print_exception(e)
            quit(detect_thread, solenoid_thread)
            break

