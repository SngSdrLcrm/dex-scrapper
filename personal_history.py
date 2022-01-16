''' Extract personal swap/deposit history of DEX
    Only depends on reading logs + token info
'''

import sys
import json
from datetime import datetime
from thor_requests.utils import is_reverted

# User Input
target_person = sys.argv[1].lower()
print(target_person)
assert target_person.startswith('0x')
assert len(target_person) == 42

# Constants Setup
TARGET_PERSON = target_person
TX_RECEIPT_INPUT = './zumo_results/tx_receipts_decoded.json'
POOLS = './zumo_info/pools.json'
KEY_CONTRACTS_INPUT = './zumo_info/key-contracts.json'
TARGET_CONTRACTS = [] # The contracts that we are interested in

with open(POOLS, 'r') as f:
    pools = json.load(f)
    for pool in pools:
        TARGET_CONTRACTS.append(pool['address'].lower())

with open(KEY_CONTRACTS_INPUT, 'r') as f:
    contracts = json.load(f)
    for contract in contracts:
        TARGET_CONTRACTS.append(contract['address'].lower())

# Pour receipts in to array
receipts = []
with open(TX_RECEIPT_INPUT, 'r') as f:
    receipts = json.load(f)

# Filter out only successful receipts
receipts_success = [x for x in receipts if not is_reverted(x)]

# Output Structure
output_obj = {
    'address': '',
    'swap_actions': [],
    'lp_actions': [],
}

# Filter out related events (Swap, Mint, Burn)
for receipt in receipts_success:
    for output in receipt['outputs']:
        for event in output['events']: # study the individual event
            # Not our monitored person
            if receipt['meta']['txOrigin'].lower() != TARGET_PERSON.lower():
                continue
            # Un-decodable event.
            if not event.get('name'):
                continue
            # Not an event on our contracts
            if not event['address'].lower() in TARGET_CONTRACTS:
                continue

            block_number = receipt['meta']['blockNumber']
            block_human_time = datetime.fromtimestamp(receipt['meta']['blockTimestamp']).strftime('%Y-%m-%d-%H-%M-%S')
            if event['name'] == 'Mint':
                output_obj['lp_actions'].append({
                    'block_number': block_number,
                    'block_time': block_human_time,
                    'direction': 'in',
                    'pool': event['address'],
                    'lp_amount0_in_wei': event['decoded']['amount0'],
                    'lp_amount1_in_wei': event['decoded']['amount1']
                })
            if event['name'] == 'Burn':
                output_obj['lp_actions'].append({
                    'block_number': block_number,
                    'block_time': block_human_time,
                    'direction': 'out',
                    'pool': event['address'],
                    'lp_amount0_out_wei': event['decoded']['amount0'],
                    'lp_amount1_out_wei': event['decoded']['amount1']
                })
            if event['name'] == 'Swap':
                output_obj['swap_actions'].append({
                    'block_number': block_number,
                    'block_time': block_human_time,
                    'pool': event['address'],
                    'swap_amount0_in_wei': event['decoded']['amount0In'],
                    'swap_amount1_in_wei': event['decoded']['amount1In'],
                    'swap_amount0_out_wei': event['decoded']['amount0Out'],
                    'swap_amount1_out_wei': event['decoded']['amount1Out']
                })

output_obj['address'] = TARGET_PERSON.lower()

timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
with open(f'./zumo_results/History_{target_person.lower()}_{timestamp}.json', 'w') as f:
    json.dump(output_obj, f, indent=2)
