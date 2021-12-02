import picharsso
from picharsso.utils import clear_screen, terminal_size
import cv2
import pathlib
import tqdm
from PIL import Image
import multiprocessing as mp
import threading, queue
from time import sleep
import signal
import time

from encoding import CPAV, Video
from args import get_args
from utils import get_useable_threads

THREAD_COUNT = get_useable_threads(max_threads=16)

BLOCK = "█"

start = time.time()

framebuffer = queue.Queue(maxsize=10)


def print_buffer(buf: queue.Queue, clear_screen_on_finish: bool = True):
    while True:
        frame = buf.get()
        buf.task_done()
        if frame is None:
            break
        time.sleep(0.01)
        print(frame)
    if clear_screen_on_finish:
        # to prevent tearing, dont do it for each frame, but at the end
        clear_screen()
    while True:
        # empty the buffer so join works (just in case)
        try:
            _ = buf.get_nowait()
            buf.task_done()
        except:
            break


converter: picharsso.draw.BrailleDrawer = picharsso.new_drawer(
    "braille", height=terminal_size()[0], colorize=True, threshold=0
)
# & hacky hack to turn the BrailleDrawer into only drawing boxes (this and threshold=0)
converter.charset_array[-1] = BLOCK


def convert_frame(frame):
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(frame)
    txtimg = converter(image)
    return txtimg


if __name__ == "__main__":
    result = []
    # args
    args = get_args()
    
    if args.source is not None:
        video: cv2.VideoCapture = cv2.VideoCapture(str(args.source))

        FRAMECOUNT = video.get(cv2.CAP_PROP_FRAME_COUNT)
        FRAMERATE = video.get(cv2.CAP_PROP_FPS)
        VIDEOLENGTH = FRAMECOUNT / FRAMERATE

        result = []
        if not args.multi:
            # convert the image, the normal way with no multiprocessing
            for i in tqdm.tqdm(
                range(int(FRAMECOUNT)),
                desc="converting",
                unit=" frames"
            ):
                read_sucseded, frame = video.read()
                if not read_sucseded:
                    break
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = Image.fromarray(frame)
                result.append(converter(image))
        else:
            with mp.Pool(THREAD_COUNT) as pool:
                all_frames = []
                for i in tqdm.tqdm(
                    range(int(FRAMECOUNT)),
                    desc="loading frames",
                    unit=" frames"
                ):
                    read_sucseded, frame = video.read()
                    if not read_sucseded:
                        break
                    all_frames.append(frame)
                result = list(
                    tqdm.tqdm(
                        pool.imap(convert_frame, all_frames),
                        desc="    converting",
                        unit=" frames",
                        total=FRAMECOUNT,
                    )
                )

    if args.load is not None:
        vfile = CPAV.decode_from_file(args.load)
        result = vfile.frames
        FRAMERATE = vfile.framerate
        FRAMECOUNT = vfile.framecount
        VIDEOLENGTH = vfile.videolength
    end = time.time()

    if args.live:
        cam = cv2.VideoCapture(0)
        FRAMERATE = cam.get(cv2.CAP_PROP_FPS)

        printer_thread = threading.Thread(
            target=print_buffer,
            args=[
                framebuffer,
            ],
        )
        printer_thread.start()
        original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
        pool = mp.Pool(THREAD_COUNT)
        signal.signal(signal.SIGINT, original_sigint_handler)

        def add_frame(frame):
            try:
                framebuffer.put_nowait(frame)
            except queue.Full:
                pass

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

    if (args.source is not None) and (args.save) and (not args.live):
        CPAV.encode_to_file(
            args.source.name.split(".")[0],# only the start of the filename, with (theoreticaly) no extensions
            result,
            VIDEOLENGTH,
            FRAMERATE,
            FRAMECOUNT,
        )
        print("saved!")

    if not args.live:
        print(f"video length (seconds) {VIDEOLENGTH}")
        print(f"# of frames: {FRAMECOUNT}")
        print(f"framerate: {FRAMERATE}")
        print(f"took {end-start} seconds to convert")
