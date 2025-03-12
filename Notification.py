import apprise
from CallInfo import CallInfoService, CallInfoProviderDummy
import datetime


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

    def format_notification_body_call(self, call):
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

    def format_notification_body_vm(self, vm):
        duration = str(datetime.timedelta(seconds=vm['duration']))
        date = str(datetime.datetime.fromtimestamp(vm['date']))
        return f"+({vm['country_code']}) {vm['phone_number']}\ndurée: {duration}\ndate: {date}"

    def new_call_notify(self, call: dict):
        print(f"new call received: {call}")
        self.apobj.notify(title="Nouvel appel sur la ligne fixe",
                          body=self.format_notification_body_call(call))

    def new_voicemail_notify(self, vm: dict):
        print(f"new voicemail received: {vm}")
        self.apobj.notify(title="Nouveau message sur le répondeur de la ligne fixe",
                          body=self.format_notification_body_vm(vm),
                          attach=vm["path"])

    def _test_notify(self):
        import logging
        with apprise.LogCapture(level=logging.TRACE) as captured:
            self.apobj.notify(title="notification de test", body="test 123")
            print(captured.getvalue())
