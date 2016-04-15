from hallcam.tempimage import TempImage
from dropbox.client import DropboxOAuth2FlowNoRedirect
from dropbox.client import DropboxClient
#from picamera.array import PiRGBArray
#from picamera import PiCamera
import argparse
import warnings
import datetime
import imutils
import json
import time
import cv2

#construct the argument parser and parse arguments
ap = argparse.ArgumentParser()
ap.add_argument('-c', '--conf', required=True,
                help="path to the JSON configuration file")
args = vars(ap.parse_args())

#filter warnings, load config and initialzie db
warnings.filterwarnings("ignore")
conf = json.load(open(args["conf"]))
client = None

if conf["use_dropbox"]:
    #connect to dropbox and start the session auth process
    flow = DropboxOAuth2FlowNoRedirect(conf["dropbox_key"], conf["dropbox_secret"])
    print "[INFO] Authorize this application: {}".format(flow.start())
    authCode = raw_input("Enter auth code here: ").strip()

    #finish auth and grab dropbox client
    (accessToken, userID) = flow.finish(authCode)
    client = DropboxClient(accessToken)
    print "[SUCCESS] dropbox account linked"
    
#webcam yo, 0= use first cam detected 1=second cam detected
cam = cv2.VideoCapture(0)
time.sleep(0.25)

#initialize first frame, assuming contains no motion and just background
firstFrame= None

#loop over frames of video
while True:
    #grab current frame and set occupied or unoccupied
    (grabbed, frame) = cam.read()
    text = 'Unnoccupied'

    #if the frame could not be grabbed, then vid end
    if not grabbed:
        break
    #resize frame, grayscale and blurrrr!
    frame = imutils.resize(frame, width=500)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21,21), 0)

    if firstFrame is None:
        firstFrame = gray
        continue
    #compute absolute difference between current and first frame
    frameDelta = cv2.absdiff(firstFrame, gray)
    thresh = cv2.threshold(frameDelta, 25, 255, cv2.THRESH_BINARY)[1]

    #dilate the thresholded image to fill holes, then find contours on it
    thresh = cv2.dilate(thresh, None, iterations=2)
    (cnts, _) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
                                 cv2.CHAIN_APPROX_SIMPLE)
    #loop over the contours and ignore small ones
    for c in cnts:
        if cv2.contourArea(c) < args['min_area']:
            continue
        #compute the bounding box for the countour and draw it on frame
        (x,y,w,h) = cv2.boundingRect(c)
        cv2.rectangle(frame, (x,y), (x + w, y + h), (0, 255,0),2)
        text = 'Occupied'
        #draw text and timestamp
        cv2.putText(frame, 'Room status:{}'.format(text),(10,20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255),2)
        cv2.putText(frame, datetime.datetime.now().strftime('%A %d %B %Y %I:%M:%S%p'),
                    (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0,0,255),1)

        #show the frame and record if the user presses a key
        cv2.imshow('Security feed', frame)
        cv2.imshow('Thersh', thresh)
        cv2.imshow('Frame Delta', frameDelta)
        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break
        
        
        
        
camera.release()
cv2.destroyAllWindows()
