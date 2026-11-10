import unittest
from decimal import Decimal
from unittest.mock import patch

from revenue_engine import estimate_share, get_latest_block


class RevenueEngineTests(unittest.TestCase):
    def test_estimate_is_deterministic(self):
        self.assertEqual(estimate_share(Decimal("1000"), Decimal("0.005")), Decimal("5.000"))

    @patch("revenue_engine.rpc_call", return_value="0x16")
    def test_block_read_is_hex_decoded(self, rpc_call):
        self.assertEqual(get_latest_block("https://rpc.example"), 22)
        rpc_call.assert_called_once_with("https://rpc.example", "eth_blockNumber", [])

    def test_no_wallet_or_governance_claims_in_configuration(self):
        with open("revenue_engine.py", encoding="utf-8") as handle:
            source = handle.read()
        self.assertNotIn("MY_WALLET", source)
        self.assertIn("not_verified", source)


if __name__ == "__main__":
    unittest.main()
