# import the necessary packages
import sys
import time
import threading
import queue
import cv2
import numpy
#import imutils

import logging

def timelapse(shutdown, conf, inqueue):
    logging.debug(f"{threading.currentThread().getName()} started")
    time.sleep(10)
    outqueue = queue.Queue()
    logging.info(f"timelapse_task started. ")
    running = True
    today = "None"
    recording = False
    while not shutdown.is_set() and running:
        #logging.debug(f'timelapse_task waiting {inqueue.qsize()} ')
        running, tnow, frame = inqueue.get()
        #logging.debug(f'timelapse_task processing {tnow} {running} {outqueue.qsize()}')
        if  running and int(tnow % 60) == 0:
            brightness = imagebrightness(frame)
            ts = time.strftime("%A %d %B %Y %H:%M", time.localtime(tnow))
            br = f'{brightness}'
            logging.debug(f'timelapse_task image {ts} {tnow} {outqueue.qsize()} {brightness}')
            cv2.putText(frame, ts, (40, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 3)
            cv2.putText(frame, br, (100, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 3)
            if not recording and brightness > 85:
                outqueue.put((tnow, frame))
                recording = True
            elif recording and brightness < 75:
                recording = False
            else:
                outqueue.put((tnow, frame))
            if not today == time.strftime("%d", time.localtime(tnow)) and outqueue.qsize() > 60:
                today = time.strftime("%d", time.localtime(tnow))
                writequeuetofile(conf, outqueue)
        inqueue.task_done()
    if outqueue.qsize() > 0:
        logging.debug(f'timelapse_task ending {inqueue.qsize()} {outqueue.qsize()}')
        writequeuetofile(conf, outqueue)
    else:
        logging.debug(f'timelapse_task ended {inqueue.qsize()} {outqueue.qsize()}')

    logging.info(f"{threading.currentThread().getName()} ended")

def imagebrightness(image):
    rows, cols = (int(image.shape[1]), int(image.shape[0]))
    pixels = rows * cols
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    brightness = numpy.sum(gray) / (pixels)
    return int(brightness)

def writequeuetofile(conf, queue):
    tnow, frame = queue.get()
    size = (int(frame.shape[1]), int(frame.shape[0]))
    filename = time.strftime("TL%Y%m%d-%H:%M:%S.avi", time.localtime(tnow))
    logging.info(f" writing file {filename} Image size {size}")
    out = cv2.VideoWriter('./' + filename, cv2.VideoWriter_fourcc(*'DIVX'), conf["framerate"], size)
    # out = cv2.VideoWriter('./video'+str(i).zfill(4)+'.avi',cv2.VideoWriter_fourcc(*'DIVX'), 15, size)
    while queue.qsize() > 0:
        tnow, frame = queue.get()
        out.write(frame)
        queue.task_done()
        del frame
    out.release()
    logging.info(f" finished writing file {filename} {queue.qsize()}")

