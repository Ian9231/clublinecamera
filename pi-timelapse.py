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

import imagesource
import clubline
import videoclip
import timelapse

import logging
from logging.handlers import TimedRotatingFileHandler
FORMATTER = logging.Formatter("%(asctime)s — %(name)s — %(levelname)s — %(message)s")
LOG_FILE = "my_app.log"

def get_console_handler():
   console_handler = logging.StreamHandler(sys.stdout)
   console_handler.setFormatter(FORMATTER)
   return console_handler
def get_file_handler():
   file_handler = TimedRotatingFileHandler(LOG_FILE, when='midnight')
   file_handler.setFormatter(FORMATTER)
   return file_handler
def get_logger(logger_name):
   logger = logging.getLogger(logger_name)
   logger.setLevel(logging.DEBUG) # better to have too much log than not enough
   logger.addHandler(get_console_handler())
   logger.addHandler(get_file_handler())
   # with this pattern, it's rarely necessary to propagate the error up to parent
   logger.propagate = False
   return logger
#my_logger = get_logger("my module name")
#my_logger.debug("a debug message")


async def line_main(picqueue, clipqueue, tlqueue, conf, shutdown):
    logging.debug(f"line_main called")
    await asyncio.sleep(5)
    await asyncio.create_task(line_task(picqueue, clipqueue, tlqueue, conf, shutdown))
    logging.debug(f"line_main ---- done consuming {picqueue.qsize()}  {clipqueue.qsize()} {tlqueue.qsize()}")


async def line_task(picqueue, clipqueue, tlqueue, conf, shutdown):
    logging.info(f"line_task started. Thread")
    last_tnow = 0
    while not shutdown.is_set():
        #logging.debug(f'line_task waiting')
        while (True):
            try:
                running, tnow, frame = picqueue.get(timeout=5)
                break
            except queue.Empty as error:
                logging.debug(f'line_task input timeout {tnow} {running} {picqueue.qsize()} {shutdown.is_set()}')
                running = False
                if shutdown.is_set():
                    break
        #logging.debug(f'line_task processing {tnow} {running} {picqueue.qsize()} {shutdown.is_set()}')

        if running:
            if not int(tnow) == last_tnow:
                last_tnow = int(tnow)
                tlframe = cv2.copyMakeBorder(frame, 0, 0, 0, 0, cv2.BORDER_REPLICATE)
                tlqueue.put((running, tnow, tlframe))
        else:
            tlqueue.put((running, tnow, frame))
        clipqueue.put((running, tnow, frame ))
        if shutdown.is_set():
            break
        picqueue.task_done()
        #logging.debug(f'line_task consumed {ts}')

def emptyqueue(queue):
    logging.debug(f"empting queue {queue.qsize()}")
    while not queue.empty():
        temp = queue.get()
        queue.task_done()


if __name__ == "__main__":

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(relativeCreated)6d %(threadName)s %(message)s"
    )

    shutdown = threading.Event()

    # construct the argument parser and parse the arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("-c", "--conf", required=True,
                    help="path to the JSON configuration file")
    ap.add_argument("-v", "--video", required=False,
                    help="optional video input file")
    ap.add_argument("-s", "--size", type=int, required=False,
                    help="optional number of frames in video")
    ap.add_argument("-i", "--interval", type=int, required=False,
                    help="optional time lapse interval")
    ap.add_argument("-f", "--framerate", type=int, required=False,
                    help="optional frame rate to capture")

    logging.debug(f"Number of arguments {len(sys.argv)}")
    if len(sys.argv) == 1:
        logging.debug("no args")
        args = vars(ap.parse_args(['-c', 'pi_surveillance_conf.json']))
        # args = vars(ap.parse_args(['-v', 'MOVI3158.avi',
        #                           '-s', '64',
        #                           '-i', '1']))
        #args = vars(ap.parse_args(['-s', '240',
        #                           '-i', '2']))
    else:
        args = vars(ap.parse_args())

    logging.debug(f"Number of arguments {args}")

    conf = json.load(open(args["conf"]))
    if conf.get("framerate", None) is None:
        conf["framerate"] = 2
    #conf["video"] = "MOVI3158.avi"
    logging.debug(f"Configuration {conf}")

    picqueue = queue.Queue()
    linequeue = queue.Queue()
    tlqueue = queue.Queue()
    clipqueue = queue.Queue()

    threadId_cam = threading.Thread(target=imagesource.imagesource, args=(conf, shutdown, picqueue), daemon=True, name="imagesource")
    threadId_cam.setDaemon(True)
    threadId_cam.start()

    threadId_con = threading.Thread(target=clubline.clubline, args=(shutdown, conf, linequeue, clipqueue), daemon=True, name="clubline")
    threadId_con.start()

    threadId_cp = threading.Thread(target=videoclip.videoclip, args=(shutdown, conf, clipqueue), daemon=True, name="videoclip")
    threadId_cp.start()

    threadId_tl = threading.Thread(target=timelapse.timelapse, args=(shutdown, conf, tlqueue), daemon=True, name="timelapse")
    threadId_tl.start()

    asyncio.run(line_main(picqueue, linequeue, tlqueue, conf, shutdown))

    while threadId_cam.is_alive() or threadId_con.is_alive() or threadId_cp.is_alive() or threadId_tl.is_alive():
        logging.debug(f'waiting for threads to end {threadId_cam.is_alive()} {threadId_con.is_alive()}'
                      f' {threadId_cp.is_alive()} {threadId_tl.is_alive()} {threading.active_count()}')
        if threadId_cam.is_alive():
            threadId_cam.join(1)
        elif threadId_con.is_alive():
            threadId_cam.join(1)
        elif threadId_cp.is_alive():
            threadId_cp.join(1)
        elif threadId_tl.is_alive():
            threadId_tl.join(1)
        time.sleep(1)
    logging.debug(f"----threads done")

    emptyqueue(tlqueue)
    emptyqueue(clipqueue)
    emptyqueue(linequeue)
    emptyqueue(picqueue)

    logging.debug(f"---- done ended ----")
    cv2.destroyAllWindows()

