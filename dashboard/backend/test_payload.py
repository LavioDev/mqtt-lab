import base64
import unittest

from app import MAX_PAYLOAD_BYTES, Monitor


class PayloadDisplayTests(unittest.TestCase):
    def test_json_payload_is_kept_as_text(self):
        result = Monitor._decode_payload(b'{"value":42}')
        self.assertEqual(result, {"kind": "json", "value": '{"value":42}', "truncated": False})

    def test_plain_text_is_not_treated_as_html(self):
        result = Monitor._decode_payload(b"<script>alert(1)</script>")
        self.assertEqual(result["kind"], "text")
        self.assertEqual(result["value"], "<script>alert(1)</script>")

    def test_binary_payload_is_base64(self):
        original = b"\x00\xff\x10"
        result = Monitor._decode_payload(original)
        self.assertEqual(result["kind"], "base64")
        self.assertEqual(base64.b64decode(result["value"]), original)

    def test_large_payload_is_bounded_and_marked(self):
        result = Monitor._decode_payload(b"a" * (MAX_PAYLOAD_BYTES + 100))
        self.assertTrue(result["truncated"])
        self.assertEqual(len(result["value"].encode("utf-8")), MAX_PAYLOAD_BYTES)


if __name__ == "__main__":
    unittest.main()
