''' Analyze on the blocks, txs, tx receipts, get an over all idea what happened '''
import json
from datetime import datetime
from thor_requests.utils import is_reverted

### CONSTANTS ###
OUTPUT_ADDRESSES = True

BLOCK_INPUT = './zumo_results/blocks.json'
TX_INPUT = './zumo_results/txs.json'
TX_RECEIPT_INPUT = './zumo_results/tx_receipts_decoded.json'  # We work on decoded tx_receipts

POOLS = './zumo_info/pools.json'
KEY_CONTRACTS_INPUT = './zumo_info/key-contracts.json'

### LOAD CONSTANTS ###

TARGET_CONTRACTS = []

with open(POOLS, 'r') as f:
    pools = json.load(f)
    for pool in pools:
        TARGET_CONTRACTS.append(pool['address'].lower())

with open(KEY_CONTRACTS_INPUT, 'r') as f:
    contracts = json.load(f)
    for contract in contracts:
        TARGET_CONTRACTS.append(contract['address'].lower())

blocks = []
with open(BLOCK_INPUT, 'r') as f:
    blocks = json.load(f)

txs = []
with open(TX_INPUT, 'r') as f:
    txs = json.load(f)

receipts = []
with open(TX_RECEIPT_INPUT, 'r') as f:
    receipts = json.load(f)


### DATA STRCUTRURE ###
result = {
    'blocks': 0,
    'txs': 0,
    'receipts': 0,
    'receipts_failed': 0,
    'receipts_success': 0,
    'traders': 0,
    'lps': 0,
    'both_trader_and_lp': 0,
    'swap_times': 0,
    'lp_in_times': 0,
    'lp_out_times': 0,
    'claim_vtho_times': 0,
    'total_claimed_vtho_in_wei': 0,
    'total_claimed_vtho': 0,
    'pools_section': {},
}
### DATA STRCUTRURE ENDS ###

### Classify Events to success and non-success ###
receipts_reverted = [x for x in receipts if is_reverted(x)]
receipts_success = [x for x in receipts if not is_reverted(x)]

### PROCESS ###
pools = set()
traders = set()
lps = set()
both_trader_and_lp = set()
swap_times = 0
lp_in_times = 0
lp_out_times = 0
claim_vtho_times = 0
total_claimed_vtho_in_wei = 0
total_claimed_vtho = 0

for receipt in receipts_success:
    for output in receipt['outputs']:
        for event in output['events']: # study the indivicual event
            if not event.get('name'): # Un-decodable event.
                continue
            if not event['address'].lower() in TARGET_CONTRACTS: # Not event on our contracts
                continue
            if event['name'] in ['Mint', 'Burn', 'Swap']:
                pools.add(event['address'])
            if event['name'] in ['Mint', 'Burn']:
                lps.add(receipt['meta']['txOrigin'])
                if event['name'] == 'Mint':
                    lp_in_times +=1
                if event['name'] == 'Burn':
                    lp_out_times +=1
            if event['name'] in ['Swap']:
                traders.add(receipt['meta']['txOrigin'])
                swap_times += 1
            
            if event['name'] == 'ClaimGeneratedVTHO':
                claim_vtho_times += 1
                total_claimed_vtho_in_wei += int(event['decoded']['amount'])

for trader in traders:
    if trader in lps:
        both_trader_and_lp.add(trader)

pools_section = {}
for pool in pools:
    pools_section[pool] = {
        'pool_name': '',
        'pool_token0': '',
        'pool_token1': '',
        'traders': set(),
        'swap_times': 0,
        'swap_amount0_in': 0,
        'swap_amount1_in': 0,
        'swap_amount0_out': 0,
        'swap_amount1_out': 0,
        'lps': set(),
        'lp_in_times': 0,
        'lp_out_times': 0,
        'lp_amount0_in': 0,
        'lp_amount1_in': 0,
        'lp_amount0_out': 0,
        'lp_amount1_out': 0,
    }

for receipt in receipts_success:
    for output in receipt['outputs']:
        for event in output['events']:
            pool_address = event['address']
            if not event.get('name'):
                continue
            if not event['address'].lower() in TARGET_CONTRACTS: # Not an event emmited on our contracts
                continue
            if event['name'] == 'Mint':
                pools_section[pool_address]['lps'].add(receipt['meta']['txOrigin'])
                pools_section[pool_address]['lp_in_times'] += 1
                pools_section[pool_address]['lp_amount0_in'] += event['decoded']['amount0']
                pools_section[pool_address]['lp_amount1_in'] += event['decoded']['amount1']
            if event['name'] == 'Burn':
                pools_section[pool_address]['lps'].add(receipt['meta']['txOrigin'])
                pools_section[pool_address]['lp_out_times'] += 1
                pools_section[pool_address]['lp_amount0_out'] += event['decoded']['amount0']
                pools_section[pool_address]['lp_amount1_out'] += event['decoded']['amount1']
            if event['name'] == 'Swap':
                pools_section[pool_address]['traders'].add(receipt['meta']['txOrigin'])
                pools_section[pool_address]['swap_times'] += 1
                pools_section[pool_address]['swap_amount0_in'] += event['decoded']['amount0In']
                pools_section[pool_address]['swap_amount1_in'] += event['decoded']['amount1In']
                pools_section[pool_address]['swap_amount0_out'] += event['decoded']['amount0Out']
                pools_section[pool_address]['swap_amount1_out'] += event['decoded']['amount1Out']

### PROCESS ENDS ###

### WRITE TO FILES ###
result['blocks'] = len(blocks)
result['txs'] = len(txs)
result['receipts'] = len(receipts)
result['receipts_failed'] = len(receipts_reverted)
result['receipts_success'] = len(receipts_success)
result['traders'] = len(traders)
result['lps'] = len(lps)
result['both_trader_and_lp'] = len(both_trader_and_lp)
result['swap_times'] = swap_times
result['lp_in_times'] = lp_in_times
result['lp_out_times'] = lp_out_times
result['claim_vtho_times'] = claim_vtho_times
result['total_claimed_vtho_in_wei'] = total_claimed_vtho_in_wei
result['total_claimed_vtho'] = total_claimed_vtho_in_wei / (10 ** 18)

# Post-processing (link pools to exisiting known pools)
for pool_address in pools_section.keys():
    pools_section[pool_address]['lps'] = len(pools_section[pool_address]['lps'])
    pools_section[pool_address]['traders'] = len(pools_section[pool_address]['traders'])

pool_names = json.load(open(POOLS, 'r'))
pool_names_dict = {}
for pool_name in pool_names:
    pool_names_dict[pool_name['address']] = pool_name

for pool_address in pools_section.keys():
    # flash loan users create a tx, that contains us and other dex's pools
    # Or 3rd party created pools we didn't add to the pool_names
    if not pool_names_dict.get(pool_address):
        print(f'Unknown pool:', pool_address)
        continue
    pools_section[pool_address]['pool_name'] = pool_names_dict[pool_address]['name']
    pools_section[pool_address]['pool_token0'] = pool_names_dict[pool_address]['token0Symbol']
    pools_section[pool_address]['pool_token1'] = pool_names_dict[pool_address]['token1Symbol']

result['pools_section'] = pools_section

timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
ANALYZE_OUTPUT = f'./zumo_results/Analyze_{timestamp}.json'
with open(ANALYZE_OUTPUT, 'w') as f:
    json.dump(result, f, indent=2)

if OUTPUT_ADDRESSES:
    TRADERS_OUTPUT = f'./zumo_results/Traders_{timestamp}.json'
    with open(TRADERS_OUTPUT, 'w') as f:
        json.dump({
            'count': len(traders),
            'items': list(traders)
        }, f, indent=2)
    
    LPS_OUTPUT = f'./zumo_results/LPs_{timestamp}.json'
    with open(LPS_OUTPUT, 'w') as f:
        json.dump({
            'count': len(lps),
            'items': list(lps)
        }, f, indent=2)

    BOTH_TRADERS_AND_LPS_OUTPUT = f'./zumo_results/Both_Traders_and_LPs_{timestamp}.json'
    with open(BOTH_TRADERS_AND_LPS_OUTPUT, 'w') as f:
        json.dump({
            'count': len(both_trader_and_lp),
            'items': list(both_trader_and_lp)
        }, f, indent=2)