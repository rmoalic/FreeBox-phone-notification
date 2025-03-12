from FreeBox import FreeBox
import asyncio
import enum
import abc


class AbstractWatcher(abc.ABC):

    def __init__(self, event_loop=None):
        self.loop = event_loop if event_loop is not None else asyncio.get_event_loop()
        self.running_poll_task = None
        self.watchers = set()


    def register(self, fun):
        if self.running_poll_task is None:
            self.running_poll_task = self.loop.create_task(self._poll())
        self.watchers.add(fun)


    def unregister(self, fun):
        self.watchers.remove(fun)
        if len(self.watchers) == 0:
            self.running_poll_task.cancel()
            self.running_poll_task = None

    def _notify(self, *args, **kwds):
        for w in self.watchers:
            w(*args, **kwds)

    @abc.abstractmethod
    async def _poll(self):
        pass


class FreeBoxWatcher(AbstractWatcher):

    def __init__(self, fb: FreeBox, event_loop=None):
        super().__init__(event_loop)
        self.fb = fb


class FreeBoxWatcher_Call(FreeBoxWatcher):
    CALLS_POLL_INTERVAL = 1

    @staticmethod
    def call_is_ringing(call):
        return call["type"] == "missed" and call["duration"] == 0

    async def _poll(self):
        try:
            calls = self.fb.get_calls()
        except Exception as e:
            print(f"Exception while fetching calls {e}")
            return None
        last_call = None if len(calls) == 0 else calls[0]
        next_call_id = 0
        while True:
            if last_call is not None:
                next_call_id = last_call["id"] + 1
                if self.call_is_ringing(last_call):
                    self._notify(last_call)
            await asyncio.sleep(self.CALLS_POLL_INTERVAL)
            try:
                last_call = self.fb.get_call(next_call_id)
            except Exception as e:
                print(f"Exception while fetching new calls {e}")


class FreeBoxWatcher_VoiceMail(FreeBoxWatcher):
    VOICEMAILS_POLL_INTERVAL = 30

    async def _poll(self):
        voicemails = []
        last_voicemail_date = 0
        while True:
            try:
                voicemails = self.fb.get_voicemails()
            except Exception as e:
                print(f"Exception while fetching voicemails {e}")
                return None
            for vm in reversed(voicemails):
                if vm["read"] == True:
                    continue
                if vm["date"] > last_voicemail_date:
                    last_voicemail_date = vm["date"]
                    path = self.fb.download_voicemail(vm["id"])
                    vm["path"] = path
                    self._notify(vm)
            await asyncio.sleep(self.VOICEMAILS_POLL_INTERVAL)
