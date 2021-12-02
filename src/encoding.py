import pathlib
import msgpack
import gzip
from typing import List


class Video:
    framerate: int
    framecount: int
    videolength: int
    frames: List[str]

    def __init__(self, framerate, framecount, length, frames) -> None:
        self.framerate = framerate
        self.framecount = framecount
        self.videolength = length
        self.frames = frames


class CPAV:
    @staticmethod
    def decode_from_file(filepath: pathlib.Path, debug: bool = False):
        if debug:
            print("loading...")

        with filepath.open("rb") as f:
            datacb = f.read()

        if debug:
            print("decompressing...")

        datab = gzip.decompress(datacb)

        if debug:
            print("deserializing...")

        data = msgpack.loads(datab)

        if debug:
            print("loaded!")

        video = Video(
            data["framerate"],
            data["framecount"],
            data["length"],
            data["frames"],
        )
        return video

    @staticmethod
    def encode_to_file(
        file_name: str,
        frames: List[str],
        length,
        framerate,
        framecount,
        overwrite: bool = False,
    ):
        if file_name == "":
            raise ValueError("file_name cannot be a empty string!")
        filepath = pathlib.Path(file_name + ".cpav")
        # check if the file exists (will be overwritten otherwise)
        if (not overwrite) and filepath.exists():
            raise FileExistsError(f"file: {file_name+'.cpav'} already exists!")

        data = {
            "frames": frames,
            "length": length,
            "framerate": framerate,
            "framecount": framecount,
        }

        bdata = msgpack.dumps(data)
        cbdata = gzip.compress(bdata, 9)
        with filepath.open("wb") as f:
            f.write(cbdata)
        return True
