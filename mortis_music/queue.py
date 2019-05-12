import time
import multiprocessing.queues as mpq
from multiprocessing import get_context
from typing import Optional
from queue import Empty, Full

DEFAULT_POLLING_TIMEOUT = 0.02


class EventMessage:
    RESET_SXM_EVENT = "RESET_SXM"
    SXM_RUNNING_EVENT = "SXM_RUNNING"
    SXM_STOPPED_EVENT = "SXM_STOPPED"
    UPDATE_CHANNELS_EVENT = "CHANNELS"
    UPDATE_METADATA_EVENT = "METADATA"
    HLS_STREAM_STARTED = "HLS_STREAM"
    HLS_STDERROR_LINES = "HLS_STDERR"
    TRIGGER_HLS_STREAM = "TRIGGER_HLS"
    KILL_HLS_STREAM = "KILL_HLS_STREAM"
    START_DEBUG_PLAYER = "DEBUG_START_PLAYER"
    STOP_DEBUG_PLAYER = "DEBUG_STOP_PLAYER"

    def __init__(self, msg_src, msg_type, msg):
        self.id = time.time()
        self.msg_src = msg_src
        self.msg_type = msg_type
        self.msg = msg

    def __str__(self):
        return f"{self.msg_src} - {self.msg_type}: {self.msg}"


class Queue(mpq.Queue):
    # -- See StackOverflow Article :
    #   https://stackoverflow.com/questions/39496554/cannot-subclass-multiprocessing-queue-in-python-3-5
    #
    # -- tldr; mp.Queue is a _method_ that returns an mpq.Queue object.  That
    # object requires a context for proper operation, so this __init__ does
    # that work as well.
    def __init__(self, *args, **kwargs):
        ctx = get_context()
        super().__init__(*args, **kwargs, ctx=ctx)

    def safe_get(
        self, timeout: float = DEFAULT_POLLING_TIMEOUT
    ) -> Optional[EventMessage]:
        try:
            if timeout is None:
                return self.get(block=False)
            else:
                return self.get(block=True, timeout=timeout)
        except Empty:
            return None

    def safe_put(
        self, item: EventMessage, timeout: float = DEFAULT_POLLING_TIMEOUT
    ) -> bool:
        try:
            self.put(item, block=False, timeout=timeout)
            return True
        except Full:
            return False

    def drain(self):
        item = self.safe_get()
        while item:
            yield item
            item = self.safe_get()

    def safe_close(self) -> int:
        num_left = sum(1 for __ in self.drain())
        self.close()
        self.join_thread()
        return num_left