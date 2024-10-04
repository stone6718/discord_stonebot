import base64
import requests
import os, sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)
import security

class OAuth:
    def __init__(self, access_token: str | None = None, refresh_token: str | None = None):
        self.access_token = access_token
        self.refresh_token = refresh_token

    def request_tokens(self) -> tuple[str, str] | None:
        req = requests.post(
            security.api_endpoint + "/oauth2/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token
            },
            auth=(
                OAuth.get_client_id(security.token),
                security.client_secret
            )
        )

        if req.status_code == 200:
            res = req.json()
            self.access_token = res.get("access_token")
            self.refresh_token = res.get("refresh_token")
            return self.access_token, self.refresh_token
        elif req.status_code == 400:
            res = req.json()
            if res.get("error") == "invalid_grant":
                return False, res.get("error_description")
            else:
                return False, req.text
        else:
            return False, str(req.status_code)

    def get_tokens(self, code: str) -> tuple[bool, str | dict]:
        req = requests.post(
            security.api_endpoint + "/oauth2/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": security.redirect_uri
            },
            auth=(
                OAuth.get_client_id(security.token),
                security.client_secret
            )
        )

        print("statuscode", req.status_code)
        if req.status_code == 200:
            res = req.json()
            self.access_token = res.get("access_token")
            self.refresh_token = res.get("refresh_token")
            return True, res
        elif req.status_code == 400:
            res = req.json()
            print("json", res)
            if res.get("error") == "invalid_grant":
                return False, res.get("error_description")
            else:
                return False, req.text
        else:
            return False, str(req.status_code)

    def revoke_tokens(self):
        requests.post(
            security.api_endpoint + "/oauth2/token/revoke",
            data={
                "token": self.refresh_token,
                "token_type_hint": "refresh_token"
            },
            auth=(
                OAuth.get_client_id(security.token),
                security.client_secret
            )
        )
        return True

    def get_user(self) -> dict | None:
        req = requests.get(
            security.api_endpoint + "/users/@me",
            headers={
                "authorization": "Bearer " + self.access_token
            }
        )

        if req.status_code == 200:
            res = req.json()
            return res
        else:
            return None

    def get_guilds(self) -> dict | None:
        req = requests.get(
            security.api_endpoint + "/users/@me/guilds",
            headers={
                "authorization": "Bearer " + self.access_token
            }
        )

        if req.status_code == 200:
            res = req.json()
            return res
        else:
            return None

    @staticmethod
    def get_client_id(token: str) -> str:
        token = token.split(".")[0]
        token += "=" * (-len(token) % 4)
        return base64.b64decode(token).decode()