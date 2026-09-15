import json
import unittest
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


if __name__ == "__main__":
    unittest.main()
