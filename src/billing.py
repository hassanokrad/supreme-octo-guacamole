import hashlib
import hmac
import json
import time
import urllib.error
import urllib.parse
import urllib.request


class StripeGateway:
    api_base = "https://api.stripe.com/v1"

    def __init__(self, api_key: str, webhook_secret: str) -> None:
        self.api_key = api_key
        self.webhook_secret = webhook_secret

    def _request_form(self, path: str, form: dict[str, str]) -> dict:
        if not self.api_key:
            raise ValueError("Stripe API key is not configured")

        body = urllib.parse.urlencode(form).encode("utf-8")
        req = urllib.request.Request(
            f"{self.api_base}{path}",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Stripe API error ({exc.code}): {detail}") from exc

    def create_customer(self, email: str) -> str:
        payload = self._request_form("/customers", {"email": email})
        return payload["id"]

    def create_checkout_session(
        self,
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
    ) -> tuple[str, str]:
        payload = self._request_form(
            "/checkout/sessions",
            {
                "customer": customer_id,
                "mode": "subscription",
                "line_items[0][price]": price_id,
                "line_items[0][quantity]": "1",
                "success_url": success_url,
                "cancel_url": cancel_url,
            },
        )
        return payload["id"], payload["url"]

    def verify_webhook(self, raw_body: bytes, stripe_signature: str) -> dict:
        if not self.webhook_secret:
            return json.loads(raw_body.decode("utf-8"))

        timestamp = None
        signature = None
        for part in stripe_signature.split(","):
            key, _, value = part.partition("=")
            if key == "t":
                timestamp = value
            if key == "v1":
                signature = value

        if not timestamp or not signature:
            raise ValueError("Invalid Stripe signature header")

        signed_payload = f"{timestamp}.{raw_body.decode('utf-8')}".encode("utf-8")
        expected = hmac.new(
            self.webhook_secret.encode("utf-8"),
            signed_payload,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected, signature):
            raise ValueError("Webhook signature mismatch")

        # 5-minute tolerance as in Stripe recommendations.
        if abs(int(time.time()) - int(timestamp)) > 300:
            raise ValueError("Webhook timestamp outside tolerance")

        return json.loads(raw_body.decode("utf-8"))
