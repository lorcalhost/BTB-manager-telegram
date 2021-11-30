import logging
import sched
import threading
import time

(
    MENU,
    EDIT_COIN_LIST,
    EDIT_USER_CONFIG,
    DELETE_DB,
    UPDATE_TG,
    UPDATE_BTB,
    PANIC_BUTTON,
    CUSTOM_SCRIPT,
    GRAPH_MENU,
    CREATE_GRAPH,
) = range(10)

BOUGHT, BUYING, SOLD, SELLING = range(4)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("btb_manager_telegram_logger")

scheduler = sched.scheduler(time.time, time.sleep)


class SchedulerRunner(threading.Thread):
    def __init__(self, scheduler):
        super().__init__()
        self.running = True
        self.scheduler = scheduler

    def run(self):
        while self.running:
            self.scheduler.run(blocking=False)
            time.sleep(1)

    def stop(self):
        for event in self.scheduler.queue:
            self.scheduler.cancel(event)
        self.running = False


scheduler_thread = SchedulerRunner(scheduler)
