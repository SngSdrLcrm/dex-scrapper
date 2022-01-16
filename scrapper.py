import sys
import time
import json
import traceback
from thor_requests.connect import Connect

# User inputs
user_node = sys.argv[1].lower() # 'http://localhost:8669' if you are using a local node
start_block = int(sys.argv[2]) # 10973311 ZumoSwap earlies activity dates back to this block

# Constants Setup
NODE = user_node
START_BLOCK = start_block
BLOCK_OUTPUT = './zumo_results/blocks.json'
TX_OUTPUT = './zumo_results/txs.json'
TX_RECEIPT_OUTPUT = './zumo_results/tx_receipts.json'
POOLS_INPUT = './zumo_info/pools.json'
KEY_CONTRACTS_INPUT = './zumo_info/key-contracts.json'

# Interesting contracts we look at
TARGET_CONTRACTS = []

with open(POOLS_INPUT, 'r') as f:
    pools = json.load(f)
    for pool in pools:
        TARGET_CONTRACTS.append(pool['address'])

with open(KEY_CONTRACTS_INPUT, 'r') as f:
    contracts = json.load(f)
    for contract in contracts:
        TARGET_CONTRACTS.append(contract['address'])

print('Target contracts:', TARGET_CONTRACTS)


def tx_contains_targets(tx, monitored_addrs) -> bool:
    ''' If transaction is targeted towards monitored contracts '''
    MONITORED_ADDRESSES = [x.lower() for x in monitored_addrs]
    clauses = tx.get('clauses', None)
    if not clauses:
        return False
    if len(clauses) == 0:
        return False
    for clause in clauses:
        if str(clause['to']).lower() in MONITORED_ADDRESSES:
            return True
    return False

def tx_receipt_contains_targets(tx_receipt, monitored_addrs) -> bool:
    ''' If transaction receipt has events emitted by monitored contracts '''
    MONITORED_ADDRESSES = [x.lower() for x in monitored_addrs]
    outputs = tx_receipt.get('outputs')
    if not outputs:
        return False

    for output in outputs:
        for event in output['events']:
            if event['address'].lower() in MONITORED_ADDRESSES:
                return True

    return False

def tx_reverted(tx_receipt) -> bool:
    return tx_receipt['reverted']


connector = Connect(NODE)
b = connector.get_block()
END_BLOCK = int(b['number'])
print('END_BLOCK', END_BLOCK)

block_bag = []
tx_bag = []
tx_receipt_bag = []

try:
    with open(BLOCK_OUTPUT, 'r') as f1:
        block_bag = json.load(f1)

    with open(TX_OUTPUT, 'r') as f2:
        tx_bag = json.load(f2)

    with open(TX_RECEIPT_OUTPUT, 'r') as f3:
        tx_receipt_bag = json.load(f3)
except Exception as e:
    print(e)
    print(traceback.format_exc())
    block_bag = []
    tx_bag = []
    tx_receipt_bag = []

if len(block_bag) > 0:
    last_query_block = int(block_bag[-1]['number']) + 1
else:
    last_query_block = START_BLOCK

if START_BLOCK < last_query_block:
    current_block_n = last_query_block
else:
    current_block_n = START_BLOCK

while current_block_n <= END_BLOCK:
    print('block number:', current_block_n)
    block = connector.get_block(str(current_block_n))
    tx_ids = block.get('transactions', None)
    if tx_ids:
        for tx_id in tx_ids:
            tx = connector.get_tx(tx_id)
            tx_receipt = connector.get_tx_receipt(tx_id)

            if tx_contains_targets(tx, TARGET_CONTRACTS) or tx_receipt_contains_targets(tx_receipt, TARGET_CONTRACTS):
                block_bag.append(block)
                tx_bag.append(tx)
                tx_receipt_bag.append(tx_receipt)
                print('bingo tx_id:', tx_id)

    current_block_n += 1

with open(BLOCK_OUTPUT, 'w') as f1:
    json.dump(block_bag, f1, indent=2)

with open(TX_OUTPUT, 'w') as f2:
    json.dump(tx_bag, f2, indent=2)

with open(TX_RECEIPT_OUTPUT, 'w') as f3:
    json.dump(tx_receipt_bag, f3, indent=2)

print('time to sleep 5mins and exit...')
time.sleep(60 * 5)
