from hallcam.tempimage import TempImage
from dropbox.client import DropboxOAuth2FlowNoRedirect
from dropbox.client import DropboxClient
from picamera.array import PiRGBArray
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


"""
if conf["use_dropbox"]:
    #connect to dropbox and start the session auth process
    flow = DropboxOAuth2FlowNoRedirect(conf["dropbox_key"], conf["dropbox_secret"])
    print "[INFO] Authorize this application: {}".format(flow.start())
    authCode = raw_input("Enter auth code here: ").strip()

    #finish auth and grab dropbox client
    (accessToken, userID) = flow.finish(authCode)
    client = DropboxClient(accessToken)
    print "[SUCCESS] dropbox account linked"
"""
    
#grab cam, set height width and fps
cam = cv2.VideoCapture(0)
cam.set(3,640)
cam.set(4,480)
cam.set(5,16)#frames
rawCapture = PiRGBArray(cam, size=tuple(conf["resolution"]))

                        

#cam warm up, then initialize average frame, timestamp and and frame motion cntr
time.sleep(conf["camera_warmup_time"])
avg = None
lastUploaded = datetime.datetime.now()
motionCounter = 0
 
#capture frames from the camera
while True:
    (grabbed, frame) = cam.read()   
    #grab the raw numpy array representing image and initialize it    
    timestamp = datetime.datetime.now()
    text = "Unnoccupied"

    #resize frame, grayscale and blurrrr!
    frame = imutils.resize(frame, width=500)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21,21), 0)

    #if the average frame is None, initialize it
    if avg is None:
        print "[INFO] starting background model.."
        avg = gray.copy().astype("float")
        rawCapture.truncate(0)
        continue

    #accumuulate the weighted average between the current and previous frame
    #then compute differene between current frame and running average    
    cv2.accumulateWeighted(gray, avg, 0.5)
    frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))

    #threshold the delta image, dilate the thresholded img to fill holes
    #then find contours on thresholded img
    thresh = cv2.threshold(frameDelta, conf["delta_thresh"],255,
                           cv2.THRESH_BINARY)[1]
    thresh = cv2.dilate(thresh, None, iterations=2)
    (cnts, _) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
                                 cv2.CHAIN_APPROX_SIMPLE)
    #loop over the contours
    for c in cnts:        
        #if the contour is too small, ignore it
        if cv2.contourArea(c) < conf["min_area"]:
            continue
        #compute the bounding box for contour and draw it, along with text.
        (x, y, w, h) = cv2.boundingRect(c)
        cv2.rectangle(frame, (x,y),(x + w, y + h), (0,255,0),2)
        text = "Occupied"

        #draw the text and timestamp on the frame
        ts = timestamp.strftime('%A %d %B %Y %I:%M:%S%p')
        cv2.putText(frame, "Room Status: {}".format(text),(10,20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255),2)
        cv2.putText(frame, ts,(10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX,
                    0.35,(0,0,255),1)

        #check to see if occupied
        if text == "Occupied":
            #check to see if enough time has past between uploads
            if (timestamp - lastUploaded).seconds >= conf["min_upload_seconds"]:
                motionCounter += 1

                #check to see if the number of frames with consistent motion is high enough
                if motionCounter >= conf["min_motion_frames"]:
                    if conf["use_dropbox"]:
                        t = TempImage()
                        cv2.imwrite(t.path, frame)

                        #upload image to dropbox and cleanup temp image
                        print "[UPLOAD] {}".format(ts)
                        path = "{base_path}/{timestamp}.jpg".format(
                            base_path=conf["drop_box_path"], timestamp=ts)
                        clinet.put_file(path, open(t.path, "rb"))
                        t.cleanup()
                    #update the last uploaded timestamp and reset motion counter
                        lastUploaded = timestamp
                        motionCounter = 0
        #otherwise room not occupied
        else:
            motionCounter = 0
        if conf["show_video"]:
            #display the security feed
            cv2.imshow('Security Feed', frame)
            key = cv2.waitKey(1) & 0xFF

            # if the q is pressed, break
            if key == ord('q'):
                break
        #clear teh stream in preparation for the next frame
        rawCapture.truncate(0)
    


camera.release()
cv2.destroyAllWindows()

