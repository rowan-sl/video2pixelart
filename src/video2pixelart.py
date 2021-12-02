import picharsso
from picharsso.utils import clear_screen, terminal_size
import cv2
import pathlib
import tqdm
from PIL import Image
import msgpack
import gzip
import sys, os
import multiprocessing as mp
import threading, queue
from time import sleep
import signal
import time

BRAILE = "⣿"
BLOCK = "█"

start = time.time()
MAX_THREADS = 16
AVAIL_MAX_THREADS = len(os.sched_getaffinity(0))
if AVAIL_MAX_THREADS < MAX_THREADS:
    THREAD_COUNT = AVAIL_MAX_THREADS
else:
    THREAD_COUNT = MAX_THREADS

framebuffer = queue.Queue(maxsize=10)

stop = False

def add_frame(frame):
    try:
        framebuffer.put_nowait(frame)
    except queue.Full:
        pass

converter = picharsso.new_drawer("braille", height=terminal_size()[0], colorize=True, threshold=0)

def convert_frame(frame):
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(frame)
    txtimg = converter(image).replace(BRAILE, BLOCK)
    return txtimg

if __name__ == "__main__":
    result = []
    #args
    from args import args
    
    def printer(buf: queue.Queue):
        while True:
            frame = framebuffer.get()
            framebuffer.task_done()
            if frame is None:
                break
            time.sleep(0.01)
            clear_screen()
            print(frame)

    if args.source is not None:
        video: cv2.VideoCapture = cv2.VideoCapture(str(args.source))

        FRAMECOUNT = video.get(cv2.CAP_PROP_FRAME_COUNT)
        FRAMERATE = video.get(cv2.CAP_PROP_FPS)
        VIDEOLENGTH = FRAMECOUNT/FRAMERATE

        result = []
        if not args.multi:
            # convert the image, the normal way with no multiprocessing
            for i in tqdm.tqdm(range(int(FRAMECOUNT)), desc="converting", unit=" frames"):
                read_sucseded, frame = video.read()
                if not read_sucseded:
                    break
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = Image.fromarray(frame)
                result.append(converter(image))
        else:
            with mp.Pool(THREAD_COUNT) as pool:
                all_frames = []
                for i in tqdm.tqdm(range(int(FRAMECOUNT)), desc="loading frames", unit=" frames"):
                    read_sucseded, frame = video.read()
                    if not read_sucseded:
                        break
                    all_frames.append(frame)
                result = list(tqdm.tqdm(pool.imap(convert_frame, all_frames), desc="    converting", unit=" frames", total=FRAMECOUNT))

    if args.load is not None:
        source_file: pathlib.Path = args.load
        print("loading...")
        with source_file.open("rb") as f:
            datacb = f.read()
        print("decompressing...")
        datab = gzip.decompress(datacb)
        print("deserializing...")
        data = msgpack.loads(datab)
        print("ready!")
        FRAMERATE = data["framerate"]
        FRAMECOUNT = data["framecount"]
        VIDEOLENGTH = data["length"]
        result = data["frames"]
    end = time.time()

    if args.live:
        cam = cv2.VideoCapture(0)
        FRAMERATE = cam.get(cv2.CAP_PROP_FPS)

        converter = picharsso.new_drawer("braille", height=terminal_size()[0], colorize=True, threshold=0)
        printer_thread = threading.Thread(target=printer, args=[framebuffer,])
        printer_thread.start()
        original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
        pool =  mp.Pool(THREAD_COUNT)
        signal.signal(signal.SIGINT, original_sigint_handler)
        try:
            while True:
                sucseeded, frame = cam.read()
                if not sucseeded:
                    continue
                else:
                    pool.apply_async(convert_frame, (frame,), callback=add_frame)
        except KeyboardInterrupt:
            pass
        finally:
            pool.terminate()
            pool.join()
        cam.release()
        framebuffer.put(None)
        printer_thread.join()
        framebuffer.join()
        clear_screen()
    
    if args.display:
        for frames in result:
            print(frames)
            sleep(1 / FRAMERATE)
        clear_screen()

    if ((args.source is not None) and (args.save) and (not args.live)):
        source_path: pathlib.Path = args.source
        save_path = pathlib.Path(str(source_path.name).split(".")[0]+".cpav")
        if save_path is not None:
            if save_path.exists():
                print("output file already exists!")
                sys.exit(1)
            converted_frames = []
            for frames in result:
                converted_frames.append(frames)
            data = {
                "frames": converted_frames,
                "length": VIDEOLENGTH,
                "framerate": FRAMERATE,
                "framecount": FRAMECOUNT,
            }
            print("serializing...")
            bdata = msgpack.dumps(data)
            print("compressing...")
            cbdata = gzip.compress(bdata, 9)
            print("saving...")
            with save_path.open("wb") as f:
                f.write(cbdata)
            print("saved!")

    if not args.live:
        print(f"video length (seconds) {VIDEOLENGTH}")
        print(f"# of frames: {FRAMECOUNT}")
        print(f"framerate: {FRAMERATE}")
        print(f"took {end-start} seconds to convert")