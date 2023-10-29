import traceback
import os
os.environ["OPENCV_LOG_LEVEL"]="d"
os.environ["OPENCV_VIDEOIO_DEBUG"]="1"
import cv2 as cv


width = 640
height = 480
cap = cv.VideoCapture(0)
cap.set(cv.CAP_PROP_FRAME_WIDTH, width)
cap.set(cv.CAP_PROP_FRAME_HEIGHT, height)
fps = int(cap.get(cv.CAP_PROP_FPS))

from mjpeg_streamer import MjpegServer, Stream

stream = Stream("Intruder Cam", size=(640, 480), quality=50, fps=30)

server = MjpegServer("localhost", 6006)
server.add_stream(stream)
server.start()


while cap.isOpened():
    try:
        ret, frame = cap.read()
        # if frame is read correctly ret is True
        if not ret:
            print("Can't receive frame (stream end?). Exiting ...")
            break
        frame = cv.flip(frame,  1)
        stream.set_frame(frame)
        if cv.waitKey(1) == ord("q"):
            break
    except BaseException as e:
        traceback.print_exception(e)
        break
else:
    print("Capture not available")

server.stop()
cap.release()
cv.destroyAllWindows()

