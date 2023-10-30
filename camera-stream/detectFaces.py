import os
import traceback
from pathlib import Path
import re
import face_recognition
import numpy as np
from mjpeg_streamer import MjpegServer, Stream

os.environ["OPENCV_VIDEOIO_DEBUG"]="1"
os.environ["OPENCV_LOG_LEVEL"]="d"
import cv2 as cv

width = 640
height = 480
cap = cv.VideoCapture(0)
cap.set(cv.CAP_PROP_FRAME_WIDTH, width)
cap.set(cv.CAP_PROP_FRAME_HEIGHT, height)

stream = Stream("Intruder Cam", size=(640, 480), quality=50, fps=30)

server = MjpegServer("localhost", 6006)
server.add_stream(stream)
server.start()

known_face_encodings = []
known_face_names = []

non_intruder_dir = Path(str(Path(__file__).parent.absolute()) + "/Non-Intruder/")
image_pattern =  r"\.apng|\.avif|\.gif|\.jpg|\.jfif|\.pjpeg|\.pjp|\.png|\.svg|\.webp"
image_re = re.compile(image_pattern)
image_paths = [f for f in non_intruder_dir.glob("*") if image_re.search(f.name)]
for i in image_paths:
    
    image = face_recognition.load_image_file(str(i))
    known_face_encodings.append(face_recognition.face_encodings(image)[0])
    known_face_names.append(i.stem)

# Initialize some variables
face_locations = []
face_encodings = []
face_names = []
process_this_frame = True

while True:
    try:
        # Grab a single frame of video
        ret, frame = cap.read()

        # Only process every other frame of video to save time
        if process_this_frame:
            # Resize frame of video to 1/4 size for faster face recognition processing
            small_frame = cv.resize(frame, (0, 0), fx=0.25, fy=0.25)

            # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
            rgb_small_frame = cv.cvtColor(small_frame, cv.COLOR_BGR2RGB)
            
            # Find all the faces and face encodings in the current frame of video
            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

            face_names = []
            for face_encoding in face_encodings:
                matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
                name = "Unknown"

                face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    name = known_face_names[best_match_index]

                face_names.append(name)

        process_this_frame = not process_this_frame


        # Display the results
        for (top, right, bottom, left), name in zip(face_locations, face_names):
            # Scale back up face locations since the frame we detected in was scaled to 1/4 size
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4

            cv.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 1)

            cv.rectangle(frame, (left, bottom - 15), (right, bottom), (0, 0, 255), cv.FILLED)
            font = cv.FONT_HERSHEY_DUPLEX
            cv.putText(frame, name, (left + 6, bottom - 6), font, 0.5, (255, 255, 255), 1)

        stream.set_frame(frame)
        if cv.waitKey(1) & 0xFF == ord('q'):
            break
    except BaseException as e:
        traceback.print_exception(e)
        break

cap.release()
server.stop()
cv.destroyAllWindows()