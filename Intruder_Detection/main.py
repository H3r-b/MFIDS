
if __name__ == "__main__":
    import traceback
    from threading import Thread
    import solenoid.control
    import camera_stream.detect_faces
    
    detect_thread = Thread(target=camera_stream.detect_faces.detect)
    solenoid_thread = Thread(target=solenoid.control.solenoid_loop, kwargs={"activate": camera_stream.detect_faces.enable_solenoid, "queue": camera_stream.detect_faces.name_queue})
    detect_thread.start()
    solenoid_thread.start()
    
    def quit(detect_thread, solenoid_thread):
        # print("Releasing Camera")
        # camera_stream.detect_faces.cap.release()
        
        print("Stopping server")
        camera_stream.detect_faces.stream_server.stop()

        print("Setting to dont run")
        camera_stream.detect_faces.run_detection.clear()
        camera_stream.detect_faces.enable_solenoid.set()
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

