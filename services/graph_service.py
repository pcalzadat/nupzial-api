import requests
from msal import ConfidentialClientApplication

class GraphService:
    def __init__(self, tenant_id: str, client_id: str, client_secret: str, user_email: str, graph_base: str):
        self.user_email = user_email
        self.graph_base = graph_base
        self.app = ConfidentialClientApplication(client_id=client_id,
                                                 authority=f"https://login.microsoftonline.com/{tenant_id}",
                                                 client_credential=client_secret)
        self.scope = ["https://graph.microsoft.com/.default"]

    def _token(self) -> str:
        result = self.app.acquire_token_silent(self.scope, account=None) or self.app.acquire_token_for_client(scopes=self.scope)
        if "access_token" not in result:
            raise RuntimeError(f"Token error: {result.get('error')} - {result.get('error_description')}")
        return result["access_token"]

    def send_email(self, to_email: str, subject: str, message: str):
        payload = {
            "message": {
                "subject": subject or "Mensaje",
                "body": {"contentType": "Text", "content": message or ""},
                "toRecipients": [{"emailAddress": {"address": to_email}}],
            },
            "saveToSentItems": True,
        }
        resp = requests.post(f"{self.graph_base}/users/{self.user_email}/sendMail",
                             headers={"Authorization": f"Bearer {self._token()}", "Content-Type": "application/json"},
                             json=payload, timeout=30)
        if resp.status_code not in (200, 202):
            raise RuntimeError(f"Graph sendMail falló: {resp.status_code} {resp.text}")
