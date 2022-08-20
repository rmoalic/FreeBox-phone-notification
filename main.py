import time
import apprise
import sys
from FreeBox import FreeBox
from CallInfo import CallInfoService

POLLING_TIME = 1

def call_is_ringing(call):
    return call["type"] == "missed" and call["duration"] == 0

def format_notification_body(call, cip: CallInfoService):
    if call["contact_id"] == 0:
        try:
            call_info = cip.reverse_search(call['number'])
        except Exception as e:
            print(f"Call info exception: {e}")
            call_info = None
        if call_info is None:
            return f"{call['number']}"
        else:
            ret = ""
            if call_info.name != "":
                ret += f"{call_info.name} - {call_info.activity} ({call['number']})\n{call_info.address}"
            else:
                ret += f"{call['number']}"

            if call_info.spam_text != "":
                ret += f"\n{call_info.spam_text}"
            return ret
    else: # known number (in FreeBox directory)
        return f"{call['name']} ({call['number']})"

def main():
    fb = FreeBox()
    fb.easy_login()

    from CallInfo import CallInfoProviderDummy
    cip = CallInfoService(CallInfoProviderDummy())
    
    apobj = apprise.Apprise()
    apconfig = apprise.AppriseConfig()
    apconfig.add('notify_config.yml')
    apobj.add(apconfig)

    if len(apobj) == 0:
        print("No notification service loaded, edit apprise `notify_config.yml`")
        sys.exit(1)

    print(f"Starting monitoring calls ({len(apobj)} notifications service)")
    calls = fb.get_calls()
    last_call = None if len(calls) == 0 else calls[0]
    next_call_id = 0
    while True:
        if last_call is not None:
            next_call_id = last_call["id"] + 1
            if call_is_ringing(last_call):
                apobj.notify(title="Nouvel appel sur la ligne fixe",
                             body=format_notification_body(last_call, cip))
        time.sleep(POLLING_TIME)
        last_call = fb.get_call(next_call_id)


if __name__ == "__main__":
    main()
