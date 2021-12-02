import os

def get_useable_threads(max_threads: int = 16) -> int:
    AVAIL_MAX_THREADS = len(os.sched_getaffinity(0))
    if AVAIL_MAX_THREADS < max_threads:
        THREAD_COUNT = AVAIL_MAX_THREADS
    else:
        THREAD_COUNT = max_threads
    return THREAD_COUNT