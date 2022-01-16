''' Post process:
    1) Tx receipt, add decoded events to it
'''
import time
import json
from thor_requests.utils import is_reverted, inject_decoded_event
from thor_requests.contract import Contract

FACTORY = './zumo_abis/UniswapV2Factory.json'
PAIR = './zumo_abis/UniswapV2Pair.json'
ROUTER02 = './zumo_abis/UniswapV2Router02.json'
factory = Contract.fromFile(FACTORY)
pair = Contract.fromFile(PAIR)
router02 = Contract.fromFile(ROUTER02)


TX_RECEIPT_INPUT = './zumo_results/tx_receipts.json'
TX_RECEIPT_OUTPUT = './zumo_results/tx_receipts_decoded.json'

receipts = []
with open(TX_RECEIPT_INPUT, 'r') as f:
    receipts = json.load(f)

### Inject Decoded Events ###
receipts_reverted = [x for x in receipts if is_reverted(x)]
receipts_success = [x for x in receipts if not is_reverted(x)]

for receipt in receipts_success:
    for output in receipt['outputs']:
        for event in output['events']:
            new_event = inject_decoded_event(event, factory)
            if new_event.get('decoded'):
                assert event['decoded']
                continue
            new_event = inject_decoded_event(event, router02)
            if new_event.get('decoded'):
                assert event['decoded']
                continue
            new_event = inject_decoded_event(event, pair)
            if new_event.get('decoded'):
                assert event['decoded']
                continue


with open(TX_RECEIPT_OUTPUT, 'w') as f:
    json.dump(receipts, f, indent=2)

print('time to sleep 1min and exit...')
time.sleep(60)