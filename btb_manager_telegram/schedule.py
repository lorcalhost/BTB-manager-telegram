import sched
import sys
import threading
import time
import traceback

from btb_manager_telegram.logging import logger


class TgScheduler(threading.Thread):
    def __init__(self):
        super().__init__()
        self.running = True
        self.scheduler = sched.scheduler(time.time, time.sleep)

    def exec_periodically(self, fun, seconds, priority=1):
        def sched_fun():
            try:
                fun()
            except Exception as e:
                logger.error(
                    f"An exception happened while running scheduled operation. Log error: \n```\n{''.join(traceback.format_exception(*sys.exc_info()))}\n```"
                )
            finally:
                self.scheduler.enter(seconds, priority, sched_fun)

        self.scheduler.enter(1, priority, sched_fun)

    def run(self):
        while self.running:
            self.scheduler.run(blocking=False)
            time.sleep(1)

    def stop(self):
        for event in self.scheduler.queue:
            self.scheduler.cancel(event)
        self.running = False


scheduler = TgScheduler()
