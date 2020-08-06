# import the necessary packages
import sys
import argparse
import warnings
import datetime
import time
import asyncio
import threading
import queue
import json
import cv2
#import dropbox
import imutils

import logging

def clubline(shutdown, conf, inqueue, outqueue):
    logging.debug(f"{threading.currentThread().getName()} started")
    asyncio.run(clubline_main(shutdown, conf, inqueue, outqueue))
    logging.debug(f"{threading.currentThread().getName()} ended")


async def clubline_main(shutdown, conf, inqueue, outqueue):
    #logging.debug(f"consumer_main called")
    await asyncio.sleep(5)
    await asyncio.create_task(line_task(shutdown, conf, inqueue, outqueue))
    logging.debug(f"consumer_main ---- done consuming {inqueue.qsize()} {outqueue.qsize()}")

async def line_task(shutdown, conf, inqueue, outqueue):
    logging.info(f"line_task started. {inqueue.qsize()} {outqueue.qsize()}")
    running, tnow, frame = inqueue.get()
    size = (int(frame.shape[1]), int(frame.shape[0]))
    logging.debug(f'line_task consumed {tnow} {size} {inqueue.qsize()}')
    height = frame.shape[0] * conf["line_height"]
    width = frame.shape[1] * conf["line_width"]
    ymin = int((frame.shape[0] - height) / 2)
    ymax = int((frame.shape[0] + height) / 2)
    xmin = int((frame.shape[1] - width) / 2)
    xmax = int((frame.shape[1] + width) / 2)
    logging.debug(f"{ymin}, {ymax}, {xmin}, {xmax}, {height * width}")

    avg = None
    occupied = False
    last_tnow = 0

    while not shutdown.is_set():
        #logging.debug(f'line_task wating {inqueue.qsize()} {outqueue.qsize()}')
        running, tnow, frame = inqueue.get()
        #logging.debug(f'line_task consumed {running} {tnow} {occupied} {inqueue.qsize()} {outqueue.qsize()}')

        cropped = frame[ymin:ymax, xmin:xmax]
        # draw block outline line on video frame
        cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), (128, 128, 0), 2)

        gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        # if the average frame is None, initialize it
        if avg is None:
            logging.info("[INFO] starting background model...")
            avg = gray.copy().astype("float")
            # rawCapture.truncate(0)
            continue
        # accumulate the weighted average between the current frame and
        # previous frames, then compute the difference between the current
        # frame and running average
        if occupied:
            factor = 0.1
        else:
            factor = 0.5
        cv2.accumulateWeighted(gray, avg, factor)

        frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))

        # threshold the delta image, dilate the thresholded image to fill
        # in holes, then find contours on thresholded image
        thresh = cv2.threshold(frameDelta, conf["delta_thresh"],
                               255, cv2.THRESH_BINARY)[1]
        # cv2.imshow("Thresh Frame 1", thresh)
        thresh = cv2.dilate(thresh, None, iterations=2)
        # cv2.imshow("Thresh Frame 2", thresh)
        cnts = cv2.findContours(thresh.copy(),
                                cv2.RETR_EXTERNAL,
                                cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)

        # loop over the contours
        occupied = False
        for c in cnts:
            # if the contour is too small, ignore it
            if cv2.contourArea(c) < conf["min_area"]:
                continue

            # compute the bounding box for the contour, draw it on the frame,
            # and update the text
            (x, y, w, h) = cv2.boundingRect(c)
            y = y + ymin
            x = x + xmin
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            occupied = True

        if occupied:
            text = "Occupied"
        else:
            text = ""

        # draw the text and timestamp on the frame
        #ts = time.strftime("%A %d %B %Y %I:%M:%S%p", time.localtime(tnow))
        ts1 = time.strftime("%I:%M:%S%p", time.localtime(tnow))
        ts2 = time.strftime("%A %d %B %Y", time.localtime(tnow))
        cv2.putText(frame, "Club line: {}".format(text), (xmin - 10, ymin - 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (128, 128, 0), 2)
        cv2.putText(frame, ts1, (xmin - 50, ymax + 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
        cv2.putText(frame, ts2, (xmin - 200, ymax + 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
        cv2.imshow("Camera", (frame))
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            logging.debug(f'Key pressed')
            shutdown.set()
            running = False

        inqueue.task_done()
        outqueue.put((running, tnow, occupied, frame))
        #logging.debug(f'line_task put  {tnow} {inqueue.qsize()} {outqueue.qsize()}')
    logging.info(f"line_task ended {inqueue.qsize()} {outqueue.qsize()}")


