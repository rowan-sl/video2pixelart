import argparse
import sys
import pathlib

parser = argparse.ArgumentParser()
parser.add_argument(
    "-s",
    "--source",
    dest="source",
    type=pathlib.Path,
    help="mp4 file to load.",
    required=False,
)
parser.add_argument(
    "-L",
    "--live",
    dest="live",
    action="store_const",
    const=True,
    default=False,
    help="livestream video from camera.",
    required=False,
)
parser.add_argument(
    "-l",
    "--load",
    dest="load",
    type=pathlib.Path,
    help="cpav file to load.",
    required=False,
)
parser.add_argument(
    "-S",
    "--save",
    dest="save",
    action="store_const",
    const=True,
    default=False,
    help="save output to a file. (special format)",
    required=False,
)
parser.add_argument(
    "-n",
    "--no-multiprocessing",
    dest="multi",
    action="store_const",
    const=False,
    default=True,
    help="do not use multiprocessing. multiprocessing will not be used anyway if the number of frames is less than double the number of availible cpus",
    required=False,
)
parser.add_argument(
    "-N",
    "--no-display",
    dest="display",
    action="store_const",
    const=False,
    default=True,
    required=False,
    help="do not actualy play the converted video. usefull for benchmarking",
)
args = parser.parse_args()
if ((args.source is not None) and (args.load is not None)):
    print("can only load a video, stream, OR load cpav file, not multiple at the same time!")
    sys.exit(1)
if (((args.source is not None) or (args.load is not None)) and (args.live)):
    print("can only load a video, stream, OR load cpav file, not multiple at the same time!")
    sys.exit(1)
if (((args.source is None) and (args.load is None)) and (not args.live)):
    print("at least one of -s, -l, or -L must be provided!")
    sys.exit(1)