import apprise
from CallInfo import CallInfoService, CallInfoProviderDummy

class NoNotificationServiceException(Exception):
    pass

class Notification:

    def __init__(self, cip: CallInfoService = CallInfoService(CallInfoProviderDummy), config_file="notify_config.yml"):
        self.cip = cip

        self.apobj = apprise.Apprise()
        apconfig = apprise.AppriseConfig()
        apconfig.add(config_file)
        self.apobj.add(apconfig)
        if len(self.apobj) == 0:
            raise NoNotificationServiceException()

    def format_notification_body(self, call):
        if call["contact_id"] != 0:
            return f"{call['name']} ({call['number']})"
        try:
            call_info = self.cip.reverse_search(call['number'])
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

    def new_call_notify(self, call: dict):
        print(f"new call received: {call}")
        self.apobj.notify(title="Nouvel appel sur la ligne fixe",
                          body=self.format_notification_body(call))

