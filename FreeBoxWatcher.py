from FreeBox import FreeBox
import asyncio
import enum


def call_is_ringing(call):
    return call["type"] == "missed" and call["duration"] == 0


CALLS_POLL_INTERVAL = 1


class FreeBoxEvent(enum.Enum):
    NEW_CALL = 0


class FreeBoxWatcher:

    def __init__(self, fb: FreeBox, event_loop=None):
        self.fb = fb
        self.loop = event_loop if event_loop is not None else asyncio.get_event_loop()
        self.running_poll_new_calls_task = None
        self.watcher = {
            FreeBoxEvent.NEW_CALL: set()
        }

    def register(self, event: FreeBoxEvent, fun):
        if event == FreeBoxEvent.NEW_CALL:
            if self.running_poll_new_calls_task is None:
                self.running_poll_new_calls_task = self.loop.create_task(self._poll_new_calls())
            self.watcher[event].add(fun)
        else:
            raise NotImplementedError()

    def unregister(self, event: FreeBoxEvent, fun):
        self.watcher[event].remove(fun)
        if event == FreeBoxEvent.NEW_CALL and len(self.watcher[event]) == 0:
            self.running_poll_new_calls_task.cancel()
            self.running_poll_new_calls_task = None

    def _notify(self, event: FreeBoxEvent, *args, **kwds):
        for w in self.watcher[event]:
            w(*args, **kwds)

    async def _poll_new_calls(self):
        calls = self.fb.get_calls()
        last_call = None if len(calls) == 0 else calls[0]
        next_call_id = 0
        while True:
            if last_call is not None:
                next_call_id = last_call["id"] + 1
                if call_is_ringing(last_call):
                    self._notify(FreeBoxEvent.NEW_CALL, last_call)
            await asyncio.sleep(CALLS_POLL_INTERVAL)
            last_call = self.fb.get_call(next_call_id)
