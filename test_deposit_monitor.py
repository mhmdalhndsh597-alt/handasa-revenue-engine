import unittest
from decimal import Decimal
from unittest.mock import patch

from deposit_monitor import discover_deposits, padded_address


class DepositMonitorTests(unittest.TestCase):
    def test_address_is_padded_for_topic_filter(self):
        value = padded_address("0x" + "1" * 40)
        self.assertEqual(len(value), 66)
        self.assertTrue(value.endswith("1" * 40))

    @patch("deposit_monitor.rpc_call")
    def test_transfer_log_is_decoded_without_submission(self, rpc_call):
        rpc_call.return_value = [{"transactionHash": "0xtx", "blockNumber": "0x10", "data": hex(1_500_000)}]
        deposits = discover_deposits("https://rpc.example", "0x" + "2" * 40, "0x" + "1" * 40, 16, 16)
        self.assertEqual(deposits[0]["amount_usdt"], str(Decimal("1.5")))
        self.assertEqual(rpc_call.call_args.args[1], "eth_getLogs")

    def test_source_has_no_transaction_submission_method(self):
        with open("deposit_monitor.py", encoding="utf-8") as handle:
            source = handle.read()
        self.assertNotIn("eth_sendRawTransaction", source)
        self.assertNotIn("private_key", source.lower())


if __name__ == "__main__":
    unittest.main()
