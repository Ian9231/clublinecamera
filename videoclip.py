# import the necessary packages
import sys
import time
import threading
import queue
import cv2

import logging

def videoclip(shutdown, conf, inqueue):
    logging.debug(f"{threading.currentThread().getName()} started")
    outqueue = queue.Queue()
    time.sleep(5)
    running = True
    runon = False
    count = 0
    while not shutdown.is_set() and running:
        #logging.debug(f'clip_task_task waiting {inqueue.qsize()} {outqueue.qsize()}')
        running, tnow, occupied, frame = inqueue.get()
        #logging.debug(f'clip_task_task processing {tnow} {running} {occupied} {inqueue.qsize()} {outqueue.qsize()}')
        if running:
            outqueue.put((tnow, occupied, frame))
            if occupied:
                runon = True
                count = 10
                if outqueue.qsize() > 70:
                    writequeuetofile(outqueue, conf)
            elif runon:
                count = count - 1
                if count == 0:
                    runon = False
                    writequeuetofile(outqueue, conf)
            else:
                while outqueue.qsize() > 10:
                    temp = outqueue.get()
                    outqueue.task_done()
                    del temp
        inqueue.task_done()

    logging.debug(f'clip_task ending {inqueue.qsize()} {outqueue.qsize()}')
    if occupied or runon:
        writequeuetofile(outqueue, conf)
    logging.debug(f"{threading.currentThread().getName()} ended")



def writequeuetofile(queue, conf):
    tnow, occupied, frame = queue.get()
    size = (int(frame.shape[1]), int(frame.shape[0]))
    filename = time.strftime("CL%Y%m%d-%H:%M:%S.avi", time.localtime(tnow))
    #filename = time.strftime("CL%Y%B%d-%I:%M:%S.avi")
    logging.info(f" writing file {filename} Image size {size}")
    out = cv2.VideoWriter('./' + filename, cv2.VideoWriter_fourcc(*'DIVX'), conf["framerate"], size)
    # out = cv2.VideoWriter('./video'+str(i).zfill(4)+'.avi',cv2.VideoWriter_fourcc(*'DIVX'), 15, size)
    nframes = 60
    while queue.qsize() > 0 and nframes > 0:
        tnow, occupied, frame = queue.get()
        out.write(frame)
        #logging.debug(f" writing file {filename} {nframes} {queue.qsize()}")
        queue.task_done()
        del frame
        nframes = nframes - 1
    out.release()
    logging.debug(f" finished writing file {filename} {nframes} {queue.qsize()}")
