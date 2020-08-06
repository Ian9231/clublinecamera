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

def imagesource(conf, shutdown, queue):
    logging.debug(f"{threading.currentThread().getName()} started")
    asyncio.run(imagesource_main(conf, shutdown, queue))
    logging.debug(f"{threading.currentThread().getName()} ended")


async def imagesource_main(conf, shutdown, queue):
    #logging.debug(f"camera_main called {conf}")

    # if the video argument is None, then we are reading rom webcam
    if conf.get("video", None) is None:
        await asyncio.create_task(camera_task(conf, shutdown, queue))
     # otherwise, we are reading from a video file
    else:
        logging.debug(f"Using video file {conf['video']}")
        await asyncio.create_task(video_task(conf, shutdown, queue))
    #logging.debug(f"camera_main ---- done producing {queue.qsize()}")

async def camera_task(conf, shutdown, queue):
    logging.debug(f"camera_task started. Thread {threading.currentThread().getName()}")
    framerate = conf["framerate"]

    vs = cv2.VideoCapture(0)
    await asyncio.sleep(2)
    if not vs.isOpened():
        logging.debug(f"Error opening video stream {vs}")
    else:
        ret, frame = vs.read()
        if ret:
            size = (int(frame.shape[1]), int(frame.shape[0]))
            logging.debug(f"Image size is {size} pixels ")

        while not shutdown.is_set():
            tnow = time.time()
            ret, frame = vs.read()
            if ret:
                queue.put((True, tnow, frame))
                #logging.debug(f'camera_task piclure {tnow} {queue.qsize()}')
                if queue.qsize() > 10:
                    logging.debug(f'camera_task stopped {tnow} {queue.qsize()}')
                    break
            await asyncio.sleep(((1 + int(framerate*tnow))/framerate) - time.time())
        tnow = time.time()
        queue.put((False, tnow, frame))
        logging.debug(f'camera_task finished {tnow} {queue.qsize()}')

async def video_task(conf, shutdown, queue):
    logging.debug(f"video_task started. Thread {threading.currentThread().getName()}")
    framerate = conf["framerate"]

    vs = cv2.VideoCapture(conf["video"])
    if not vs.isOpened():
        logging.debug(f"Error opening video stream {vs}")
    else:
        fps = vs.get(cv2.CAP_PROP_FPS)
        amount_of_frames = vs.get(7)
        logging.debug(f"The number of frames in this video = {amount_of_frames} FPS is {fps}")

        ret, frame = vs.read()
        if ret:
            size = (int(frame.shape[1]), int(frame.shape[0]))
            logging.debug(f"Image size is {size} pixels ")

        tnow = int(time.time())
        count = 0

        while ret:
            ret, frame = vs.read()
            if ret and count <= 0:
                count += fps/framerate
                queue.put((True, tnow, frame))
                logging.debug(f'video_task picture {tnow} {queue.qsize()}')
            count -= 1
            tnow += 1/fps
    queue.put((False, tnow, frame))
    await asyncio.sleep(1)
    logging.debug(f"video_task ended. Thread {threading.currentThread().getName()}")
