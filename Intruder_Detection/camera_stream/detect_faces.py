import re
import traceback
from dataclasses import dataclass
from os import uname
from pathlib import Path
from queue import Queue
from threading import Event, Thread
from time import sleep
from typing import Literal

import cv2 as cv
import face_recognition
import numpy as np
from aiohttp.web_runner import GracefulExit
from mjpeg_streamer import MjpegServer, Stream

if linux := uname().sysname == "Linux":
    from picamera2 import Picamera2


class detect_and_stream_thread(Thread):
    @dataclass
    class camera_settings:
        camera_read: int | str = 0
        camera_width: int = 640
        camera_height: int = 480
        camera_fps: int = 60

    @dataclass
    class stream_settings:
        stream_push: str = "localhost"
        stream_push_port: int = 6006
        stream_name: str = "Intruder Cam"
        stream_width: int = 640
        stream_height: int = 480
        stream_quality: int = 100
        stream_fps: int = 30

    def __init__(
        self,
        hardware_event: Event,
        name_queue: Queue,
        read_from: Literal["Capture-OCV", "Capture-Pi", "Test"] = "Test",
        camera_read: int | str = camera_settings.camera_read,
        camera_width: int = camera_settings.camera_width,
        camera_height: int = camera_settings.camera_height,
        camera_fps: int = camera_settings.camera_fps,
        stream_push: str = stream_settings.stream_push,
        stream_push_port: int = stream_settings.stream_push_port,
        stream_name: str = stream_settings.stream_name,
        stream_width: int = stream_settings.stream_width,
        stream_height: int = stream_settings.stream_height,
        stream_quality: int = stream_settings.stream_quality,
        stream_fps: int = stream_settings.stream_fps,
    ) -> None:
        super().__init__()

        # Check if running in pi
        self.linux = linux

        # Stopping thread on signal
        self.run_event = Event()
        self.run_event.set()
        # Event for hardware signals
        self.hardware_event = hardware_event
        # Communication between threads
        self.name_queue = name_queue

        # Frames to skip when processing
        self.frames_to_skip = 0
        if camera_fps >= stream_fps:
            self.frames_to_skip = (camera_fps // stream_fps) - 1
        else:
            raise RuntimeError("Stream FPS cannot be greater than that of Camera FPS.")

        self.read_from = read_from

        # Intialize capture values to read frames from input
        self.camera_settings.camera_read = camera_read
        self.camera_settings.camera_width = camera_width
        self.camera_settings.camera_height = camera_height
        self.camera_settings.camera_fps = camera_fps
        self.cap = None

        # Intialize stream to push frames after processing
        self.stream_settings.stream_name = stream_name
        self.stream_settings.stream_width = stream_width
        self.stream_settings.stream_height = stream_height
        self.stream_settings.stream_quality = stream_quality
        self.stream_settings.stream_fps = stream_fps
        self.stream_settings.stream_push = stream_push
        self.stream_settings.stream_push_port = stream_push_port
        self.stream = None
        self.stream_server = None

        # Load faces
        self.known_face_encodings = []
        self.known_face_names = []

        # Reads all faces present in images found in non intruder dir, along with names which are specified as file names
        non_intruder_dir = Path(
            str(Path(__file__).parent.absolute()) + "/Non_Intruder/"
        )
        image_pattern = (
            r"\.apng|\.avif|\.gif|\.jpg|\.jfif|\.pjpeg|\.pjp|\.png|\.svg|\.webp"
        )
        image_re = re.compile(image_pattern)
        image_paths = [f for f in non_intruder_dir.glob("*") if image_re.search(f.name)]
        for i in image_paths:
            image = face_recognition.load_image_file(str(i))
            self.known_face_encodings.append(face_recognition.face_encodings(image)[0])
            self.known_face_names.append(i.stem)

    def __set_camera__(
        self,
        camera_read: int | str = camera_settings.camera_read,
        camera_width: int = camera_settings.camera_width,
        camera_height: int = camera_settings.camera_height,
        camera_fps: int = camera_settings.camera_fps,
    ) -> None:
        self.camera_settings.camera_read = camera_read
        self.camera_settings.camera_width = camera_width
        self.camera_settings.camera_height = camera_height
        self.camera_settings.camera_fps = camera_fps

        match self.read_from:
            case "Capture-OCV":
                self.cap = cv.VideoCapture(camera_read)
                self.cap.set(cv.CAP_PROP_FRAME_WIDTH, camera_width)
                self.cap.set(cv.CAP_PROP_FRAME_HEIGHT, camera_height)
                self.cap.set(cv.CAP_PROP_FPS, camera_fps)
            case "Capture-Pi":
                self.cap = Picamera2()
                self.cap.preview_configuration.main.size = (camera_width, camera_height)
                self.cap.preview_configuration.main.format = "RGB888"
                self.cap.configure("preview")
                self.cap.start()

    def __set_stream__(
        self,
        stream_push: str = stream_settings.stream_push,
        stream_push_port: int = stream_settings.stream_push_port,
        stream_name: str = stream_settings.stream_name,
        stream_width: int = stream_settings.stream_width,
        stream_height: int = stream_settings.stream_height,
        stream_quality: int = stream_settings.stream_quality,
        stream_fps: int = stream_settings.stream_fps,
    ):
        self.stream_settings.stream_name = stream_name
        self.stream_settings.stream_width = stream_width
        self.stream_settings.stream_height = stream_height
        self.stream_settings.stream_quality = stream_quality
        self.stream_settings.stream_fps = stream_fps
        self.stream_settings.stream_push = stream_push
        self.stream_settings.stream_push_port = stream_push_port

        self.stream = Stream(
            name=stream_name,
            size=(stream_width, stream_height),
            quality=stream_quality,
            fps=stream_fps,
        )
        self.stream_server = MjpegServer(stream_push, stream_push_port)
        self.stream_server.add_stream(self.stream)

    def run(self) -> None:
        frames_skipped = 0
        match self.read_from:
            case "Capture-OCV" | "Capture-Pi":
                self.__set_camera__()
        self.__set_stream__()
        self.stream_server.start()
        try:
            while self.run_event.is_set():
                # Grab a single frame
                match self.read_from:
                    case "Test":
                        unknown_image_dir = Path(
                            str(Path(__file__).parent.absolute())
                            + "/Unknown/Unknown.jpg"
                        )
                        frame = cv.imread(str(unknown_image_dir))
                    case "Capture-OCV":
                        _, frame = self.cap.read()
                    case "Capture-Pi":
                        frame = self.cap.capture_array()

                frame = cv.flip(frame, 1)

                # Only process certain frames to save time
                if frames_skipped >= self.frames_to_skip:
                    frames_skipped = 0

                    # Resize frame of video to 1/4 size for faster face recognition processing
                    small_frame = cv.resize(frame, (0, 0), fx=0.25, fy=0.25)

                    # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
                    rgb_small_frame = cv.cvtColor(small_frame, cv.COLOR_BGR2RGB)

                    # Find all the faces and face encodings in the current frame of video
                    face_locations = face_recognition.face_locations(rgb_small_frame)
                    face_encodings = face_recognition.face_encodings(
                        rgb_small_frame, face_locations
                    )

                    face_names = []
                    for face_encoding in face_encodings:
                        matches = face_recognition.compare_faces(
                            self.known_face_encodings, face_encoding
                        )
                        name = "Unknown"

                        face_distances = face_recognition.face_distance(
                            self.known_face_encodings, face_encoding
                        )
                        best_match_index = np.argmin(face_distances)
                        if matches[best_match_index]:
                            name = self.known_face_names[best_match_index]

                        face_names.append(name)

                    # Display the results
                    for (top, right, bottom, left), name in zip(
                        face_locations, face_names
                    ):
                        # Scale back up face locations since the frame we detected in was scaled to 1/4 size
                        top *= 4
                        right *= 4
                        bottom *= 4
                        left *= 4

                        cv.rectangle(
                            frame, (left, top), (right, bottom), (0, 0, 255), 1
                        )

                        cv.rectangle(
                            frame,
                            (left, bottom - 15),
                            (right, bottom),
                            (0, 0, 255),
                            cv.FILLED,
                        )
                        font = cv.FONT_HERSHEY_DUPLEX
                        cv.putText(
                            frame,
                            name,
                            (left + 6, bottom - 6),
                            font,
                            0.5,
                            (255, 255, 255),
                            1,
                        )

                    self.stream.set_frame(frame)

                    # To activate hardware
                    if (
                        any([i != "Unknown" for i in face_names])
                        and not self.hardware_event.is_set()
                    ):
                        self.name_queue.put(face_names)
                        self.hardware_event.set()

                frames_skipped += 1
        except Exception as e:
            if type(e) != GracefulExit:
                traceback.print_exception(e)
                self.quit()

    def quit(self):
        if self.is_alive():
            self.run_event.clear()
            while self.is_alive():
                sleep(0.01)
            match self.read_from:
                case "Capture-OCV":
                    self.cap.release()
                case "Capture-PI":
                    self.cap.stop()
                    self.cap.close()
            print("Released camera")
            try:
                self.stream_server.stop()
            except GracefulExit:
                pass
            print("Stopped server")
        else:
            raise RuntimeError("Thread was not running when quit was performed.")


if __name__ == "__main__":
    hardware = Event()
    hardware.set()
    name_queue = Queue()
    cam = detect_and_stream_thread(
        hardware, name_queue=name_queue, read_from="Capture-OCV"
    )
    cam.start()
    while input("Quit? [y/n]:") != "y":
        ...
    cam.quit()
    cam.join()
