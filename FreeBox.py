from __future__ import annotations
import requests
import tempfile
import re
import os
import json
import platform
import time
from hashlib import sha1
import hmac
from pathlib import Path
from dataclasses import dataclass, asdict

API_PROTOCOL = "https"
API_HOST = "mafreebox.freebox.fr"  # gl4kx4wl.fbxos.fr:47865
API_ENDPOINT = f"{API_PROTOCOL}://{API_HOST}/api"
CA_FILE = "freebox_ca.pem"
global_session = requests.Session()
global_session.verify = CA_FILE


class FreeBoxNoAuthorizationException(Exception):
    pass


class FreeBoxMultipleInstancesException(Exception):
    pass


@dataclass(frozen=True)
class FreeBox_app_info:
    app_id: str
    app_name: str
    app_version: str
    device_name: str


class FreeBox:
    instances_info: list[FreeBox_app_info] = []

    def __init__(self, app_id: str, app_name: str, app_version: str):
        self.app_info = FreeBox_app_info(app_id, app_name, app_version, platform.node())
        for instance in FreeBox.instances_info:
            if instance.app_id == app_id:
                # Cannot have two instances with same id, because of the concurrent access to the token_store file
                raise FreeBoxMultipleInstancesException()
        FreeBox.instances_info.append(self.app_info)

        self.stored_app_token = None
        self.token_store = Path(f"FreeBox_{app_id}.store")
        try:
            with open(self.token_store, "r") as f:
                self.stored_app_token = f.read()
        except FileNotFoundError:
            pass
        self.session = requests.Session()
        self.session.verify = CA_FILE
        self.session.hooks['response'].append(self._refresh_token)

    def __del__(self):
        if self.app_info in FreeBox.instances_info:
            FreeBox.instances_info.remove(self.app_info)

    @staticmethod
    def is_ready():
        endpoint = f"{API_PROTOCOL}://{API_HOST}/api_version"
        try:
            global_session.get(endpoint)
            return True
        except Exception:
            return False

    @staticmethod
    def _request_authotize(app_info: FreeBox_app_info) -> tuple[str, str]:
        endpoint = f"{API_ENDPOINT}/v4/login/authorize/"
        resp = global_session.post(endpoint, data=json.dumps(asdict(app_info)))
        if resp.status_code != 200:
            raise Exception("Unexpected response code")

        resp_data = resp.json()
        return (resp_data["result"]["app_token"], resp_data["result"]["track_id"])

    @staticmethod
    def _wait_for_authorization(track_id: str) -> str | None:
        endpoint = f"{API_ENDPOINT}/v4/login/authorize/{track_id}"
        status = ""
        challenge = ""

        while True:
            resp = global_session.get(endpoint)
            if resp.status_code != 200:
                raise Exception("Unexpected response code")
            resp_data = resp.json()
            status = resp_data["result"]["status"]
            challenge = resp_data["result"]["challenge"]
            if status == "pending":
                print(".", end="", flush=True)
                time.sleep(1)
            else:
                print()
                break
        if status == "granted":
            return challenge
        else:
            print(f"autorization not granted: {status}")
            return None

    @staticmethod
    def _open_session(app_id: str, password: str) -> tuple[str, str]:
        req = {
            "app_id": app_id,
            "password": password
        }
        endpoint = f"{API_ENDPOINT}/v4/login/session/"

        resp = global_session.post(endpoint, data=json.dumps(req))
        if resp.status_code != 200:
            if resp.status_code == 403:
                raise FreeBoxNoAuthorizationException()
            raise Exception("Unexpected response code")

        resp_data = resp.json()

        return (resp_data["result"]["session_token"], resp_data["result"]["permissions"])

    def _close_session(self) -> bool:
        endpoint = f"{API_ENDPOINT}/v4/login/logout/"
        resp = self.session.get(endpoint)
        if resp.status_code != 200:
            raise Exception("Unexpected response code")
        resp_data = resp.json()
        print(resp_data)
        assert resp_data["success"]

    @staticmethod
    def _get_challenge() -> str:
        endpoint = f"{API_ENDPOINT}/v4/login/"
        resp = global_session.get(endpoint)

        if resp.status_code != 200:
            raise Exception("Unexpected response code")
        resp_data = resp.json()

        if resp_data["result"]["logged_in"]:
            print("get_challenge: Already logged in")
        return resp_data["result"]["challenge"]

    def _get_password(self) -> str:
        if self.stored_app_token is None:
            raise FreeBoxNoAuthorizationException()

        app_token = self.stored_app_token
        challenge = FreeBox._get_challenge()

        if challenge is None:
            raise FreeBoxNoAuthorizationException()

        password = hmac.new(app_token.encode("utf-8"), challenge.encode("utf-8"), sha1).hexdigest()
        return password

    def login(self) -> str:
        password = self._get_password()
        session_token, session_permissions = FreeBox._open_session(self.app_info.app_id, password)
        if session_token is None:
            raise FreeBoxNoAuthorizationException()
        self.session.headers.update({"X-Fbx-App-Auth": session_token})
        return session_token

    def _refresh_token(self, res, *args, **kwargs):
        if res.status_code == 403:
            self.login()
            res.request.headers.update(self.session.headers)
            return self.session.send(res.request)

    def easy_login(self) -> str | None:
        try_count = 0
        while try_count <= 1:
            try:
                session_token = self.login()
                return session_token
            except FreeBoxNoAuthorizationException:
                print("Autorization needed, select YES on the FreeBox front panel")
                app_token, track_id = FreeBox._request_authotize(self.app_info)
                challenge = FreeBox._wait_for_authorization(track_id)
                if challenge is not None:
                    self.stored_app_token = app_token
                    with open(self.token_store, "w") as f:
                        f.write(app_token)
            try_count = try_count + 1
        return None

    def get_calls(self) -> dict:
        endpoint = f"{API_ENDPOINT}/v4/call/log/"
        resp = self.session.get(endpoint)

        if resp.status_code != 200:
            print(resp.status_code)
            raise Exception("Unexpected response code")
        resp_data = resp.json()

        calls = resp_data["result"]
        return calls

    def get_call(self, id: int) -> dict | None:
        endpoint = f"{API_ENDPOINT}/v4/call/log/{id}"
        resp = self.session.get(endpoint)

        if resp.status_code != 200:
            print(resp.status_code)
            raise Exception("Unexpected response code")
        resp_data = resp.json()

        if resp_data["success"]:
            return resp_data["result"]
        else:
            assert resp_data["error_code"] == "invalid_id"
            return None

    def get_voicemails(self) -> dict:
        endpoint = f"{API_ENDPOINT}/v11/call/voicemail/"
        resp = self.session.get(endpoint)

        if resp.status_code != 200:
            print(resp.status_code)
            raise Exception("Unexpected response code")
        resp_data = resp.json()
        return resp_data["result"]

    def download_voicemail(self, id: str) -> str:
        endpoint = f"{API_ENDPOINT}/v11/call/voicemail/{id}/audio_file"
        resp = self.session.get(endpoint)

        if resp.status_code != 200:
            print(resp.status_code)
            raise Exception("Unexpected response code")

        file_name_re = re.findall('filename=\"(.+)\"', resp.headers.get("Content-Disposition"))
        file_name = "_" + file_name_re[0] if len(file_name_re) > 0 else "__"
        fd, path = tempfile.mkstemp(prefix="fb_voicemail_", suffix=file_name)
        os.write(fd, resp.content)
        os.close(fd)
        return path
