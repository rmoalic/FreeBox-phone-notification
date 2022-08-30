import sys
import time
import asyncio
from FreeBox import FreeBox
from FreeBoxWatcher import FreeBoxWatcher, FreeBoxEvent
from CallInfo import CallInfoService
from Notification import Notification, NoNotificationServiceException


def wait_for_freebox_ready(fb: FreeBox) -> bool:
    try_attempts = 0
    while not fb.is_ready():
        time.sleep(2)
        if try_attempts > 150:  # 150 * 2 sec is 5 minutes
            return False
        try_attempts = try_attempts + 1
    return True


def main():
    loop = asyncio.new_event_loop()

    fb = FreeBox(app_id="fr.polms.phone_notification",
                 app_name="Phone notification",
                 app_version="0.0.1")
    if not wait_for_freebox_ready(fb):
        print("Freebox is not ready after 5 minutes.")
        sys.exit(1)
    fb.easy_login()

    from CallInfo import CallInfoProviderDummy
    cip = CallInfoService(CallInfoProviderDummy())

    try:
        notif = Notification(config_file="notify_config.yml", cip=cip)
    except NoNotificationServiceException:
        print("No notification service loaded, edit apprise `notify_config.yml`")
        sys.exit(1)

    fbw = FreeBoxWatcher(fb, loop)
    fbw.register(FreeBoxEvent.NEW_CALL, notif.new_call_notify)

    print("Starting monitoring calls")

    try:
        loop.run_forever()
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        pending = asyncio.all_tasks(loop=loop)
        for task in pending:
            task.cancel()
            try:
                loop.run_until_complete(task)
            except asyncio.exceptions.CancelledError:
                pass
        loop.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
