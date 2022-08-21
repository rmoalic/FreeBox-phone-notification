from __future__ import annotations
import requests
import json
import platform
import time
from hashlib import sha1
import hmac

APP_ID = "fr.polms.phone_notification"
APP_NAME = "Phone notification"
APP_VERSION = "0.0.1"

API_PROTOCOL = "http"
API_HOST = "mafreebox.freebox.fr" # gl4kx4wl.fbxos.fr:47865
API_ENDPOINT = f"{API_PROTOCOL}://{API_HOST}/api"

TOKEN_STORE = "FreeBox.store"

class FreeBoxNoAuthorizationException(Exception):
    pass

class FreeBox:

    def __init__(self):
        self.stored_app_token = None
        try:
            with open(TOKEN_STORE, "r") as f:
                self.stored_app_token = f.read()
        except FileNotFoundError:
            pass
        self.session = requests.Session()
        self.session.hooks['response'].append(self._refresh_token)

    def __del__(self):
        pass
        #self._close_session() # 404 error
    
    def _request_authotize():
        req =  {
            "app_id": APP_ID,
            "app_name": APP_NAME,
            "app_version": APP_VERSION,
            "device_name": platform.node()
        }
        endpoint = f"{API_ENDPOINT}/v4/login/authorize/"
        resp = requests.post(endpoint, data=json.dumps(req))
        if resp.status_code != 200:
            raise Exception("Unexpected response code")

        resp_data = resp.json()
        return (resp_data["result"]["app_token"], resp_data["result"]["track_id"])

    def _wait_for_authorization(track_id: str):
        endpoint = f"{API_ENDPOINT}/v4/login/authorize/{track_id}"
        status = ""
        challenge = ""
        
        while True:
            resp = requests.get(endpoint)
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

    def _open_session(password):
        req = {
            "app_id": APP_ID,
            "password": password
        }
        endpoint = f"{API_ENDPOINT}/v4/login/session/"
        
        resp = requests.post(endpoint, data=json.dumps(req))
        if resp.status_code != 200:
            if resp.status_code == 403:
                raise FreeBoxNoAuthorizationException()
            raise Exception("Unexpected response code")
        
        resp_data = resp.json()
        
        return (resp_data["result"]["session_token"], resp_data["result"]["permissions"])

    def _close_session(self):
        endpoint = f"{API_ENDPOINT}/v4/login/logout/"
        resp = self.session.get(endpoint)
        if resp.status_code != 200:
            raise Exception("Unexpected response code")
        resp_data = resp.json()
        print(resp_data)
        assert resp_data["success"] == True
        
    def _get_challenge():
        endpoint = f"{API_ENDPOINT}/v4/login/"
        resp = requests.get(endpoint)
        
        if resp.status_code != 200:
            raise Exception("Unexpected response code")
        resp_data = resp.json()

        if resp_data["result"]["logged_in"] == True:
            print("get_challenge: Already logged in")
        return resp_data["result"]["challenge"]

    def _get_password(self):
        if self.stored_app_token is None:
            raise FreeBoxNoAuthorizationException()
        
        app_token = self.stored_app_token
        challenge = FreeBox._get_challenge()

        if challenge is None:
            raise FreeBoxNoAuthorizationException()

        password = hmac.new(app_token.encode("utf-8"), challenge.encode("utf-8"), sha1).hexdigest()
        return password

    def login(self):
        password = self._get_password()
        session_token, session_permissions = FreeBox._open_session(password)
        if session_token is None:
            raise FreeBoxNoAuthorizationException()
        self.session.headers.update({"X-Fbx-App-Auth": session_token})
        return session_token
    
    def _refresh_token(self, res, *args, **kwargs):
        if res.status_code == 403:
            self.login()
            res.request.headers.update(self.session.headers)
            return self.session.send(res.request)
    
    def easy_login(self):
        try_count = 0
        while try_count <= 1:
            try:
                session_token = self.login()
                return session_token
            except FreeBoxNoAuthorizationException:
                print("Autorization needed, select YES on the FreeBox front panel")
                app_token, track_id = FreeBox._request_authotize()
                challenge = FreeBox._wait_for_authorization(track_id)
                if challenge is not None:
                    self.stored_app_token = app_token
                    with open(TOKEN_STORE, "w") as f:
                        f.write(app_token)
            try_count = try_count + 1


    def get_calls(self):
        endpoint = f"{API_ENDPOINT}/v4/call/log/"
        resp = self.session.get(endpoint)

        if resp.status_code != 200:
            print(resp.status_code)
            raise Exception("Unexpected response code")
        resp_data = resp.json()

        calls = resp_data["result"]
        return calls

    def get_call(self, id: int):
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

