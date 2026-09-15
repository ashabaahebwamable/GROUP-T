import json
import unittest
from urllib import error
from unittest.mock import patch

from src.model_client import _parse_gemini_payload, call_model


class ModelClientTests(unittest.TestCase):
    def test_parse_gemini_payload(self):
        payload = {
            "candidates": [{
                "content": {
                    "parts": [{"text": '{"supplier_name": "Demo Supplier", "currency": "UGX"}'}]
                }
            }]
        }
        self.assertEqual(_parse_gemini_payload(payload), {"supplier_name": "Demo Supplier", "currency": "UGX"})

    @patch("src.model_client.request.urlopen")
    def test_call_model_success(self, mocked_urlopen):
        class MockResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                return False

            def read(self):
                return json.dumps({
                    "candidates": [{
                        "content": {
                            "parts": [{"text": '{"quotation_id": "Q-77", "currency": "UGX"}'}]
                        }
                    }]
                }).encode("utf-8")

        mocked_urlopen.return_value = MockResponse()
        result = call_model("Supplier: Demo Trading; Currency: UGX", api_key="test-key")
        self.assertEqual(result["quotation_id"], "Q-77")
        self.assertEqual(result["currency"], "UGX")

    @patch("src.model_client.request.urlopen")
    def test_call_model_retries_on_transient_503(self, mocked_urlopen):
        class MockSuccessResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                return False

            def read(self):
                return json.dumps({
                    "candidates": [{
                        "content": {
                            "parts": [{"text": '{"quotation_id": "Q-101", "currency": "UGX"}'}]
                        }
                    }]
                }).encode("utf-8")

        def fake_urlopen(req, timeout=60):
            if not hasattr(fake_urlopen, "calls"):
                fake_urlopen.calls = 0
            fake_urlopen.calls += 1
            if fake_urlopen.calls == 1:
                raise error.HTTPError(
                    url=req.full_url,
                    code=503,
                    msg="Service Unavailable",
                    hdrs=None,
                    fp=io.BytesIO(b'{"error":{"code":503,"message":"high demand","status":"UNAVAILABLE"}}')
                )
            return MockSuccessResponse()

        import io
        mocked_urlopen.side_effect = fake_urlopen
        result = call_model("Supplier: Demo Trading; Currency: UGX", api_key="test-key")
        self.assertEqual(result["quotation_id"], "Q-101")
        self.assertEqual(result["currency"], "UGX")
        self.assertEqual(mocked_urlopen.call_count, 2)


if __name__ == "__main__":
    unittest.main()
