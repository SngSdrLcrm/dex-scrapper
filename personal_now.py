'''
    Personal scrapper to view his holdings on the DEX (till current block)
    Python3 script.py [address] [node_url]
'''
import sys
import json
from typing import List
from datetime import datetime
from thor_requests.connect import Connect
from thor_requests.contract import Contract

# Inputs
target_person = sys.argv[1].lower()
print(target_person)
assert target_person.startswith('0x')
assert len(target_person) == 42

node_url = sys.argv[2].lower()
print(node_url)

# Prepare
TARGET_PERSON = target_person
NODE = node_url
POOLS = './zumo_info/pools.json'
PAIR_CONTRACT_DEFINITION = './zumo_abis/UniswapV2Pair.json'
TOKENS_DEFINITION = './vechain_info/main.json'
KEY_CONTRACTS_INPUT = './zumo_info/key-contracts.json'

TARGET_CONTRACTS = []

with open(POOLS, 'r') as f:
    pools = json.load(f)
    for pool in pools:
        TARGET_CONTRACTS.append(pool['address'].lower())

with open(KEY_CONTRACTS_INPUT, 'r') as f:
    contracts = json.load(f)
    for contract in contracts:
        TARGET_CONTRACTS.append(contract['address'].lower())

def get_reserves_of_pools(caller:str, addrs: List[str], pool_contract: Contract) -> List[dict]:
    ''' Get reserves of a list of pools (current block) '''
    clauses = [connector.clause(pool_contract, 'getReserves', [], addr) for addr in addrs]
    results = connector.call_multi(caller, clauses)
    assert len(results) == len(clauses)
    return [
        {
            'token0': int(x['decoded']['0']),
            'token1': int(x['decoded']['1']),
            'timestamp': int(x['decoded']['2'])
        } 
        for x in results
    ]

def get_total_lps_of_pools(caller:str, addrs: List[str], pool_contract: Contract) -> List[int]:
    ''' Get total supply of a list of pools (current block) '''
    clauses = [connector.clause(pool_contract, 'totalSupply', [], addr) for addr in addrs]
    results = connector.call_multi(caller, clauses)
    assert len(results) == len(clauses)
    return [int(x['decoded']['0']) for x in results]

def get_lp_balances_of_user_of_pools(user_addr:str, addrs: List[str], pool_contract: Contract) -> List[int]:
    ''' Get lp token amount of a user of a list of pools (current block)'''
    clauses = [connector.clause(pool_contract, 'balanceOf', [user_addr], addr) for addr in addrs]
    results = connector.call_multi(user_addr, clauses)
    assert len(results) == len(clauses)
    return [int(x['decoded']['0']) for x in results]

### Begin Script ###
pools = []
with open(POOLS, 'r') as f:
    pools = json.load(f)

pools_addresses = [x['address'] for x in pools]

connector = Connect(NODE)

pool_contract = Contract.fromFile(PAIR_CONTRACT_DEFINITION)

print('get user lps...')
user_lps = get_lp_balances_of_user_of_pools(TARGET_PERSON, pools_addresses, pool_contract)
print('get total lps...')
total_lps = get_total_lps_of_pools(TARGET_PERSON, pools_addresses, pool_contract)
print('get pool reserves ...')
pools_reserves = get_reserves_of_pools(TARGET_PERSON, pools_addresses, pool_contract)

user_percentages = [x/y for x, y in zip(user_lps, total_lps)]
user_holdings = [
    {
        'token0': reserve['token0'] * percentage,
        'token1': reserve['token1'] * percentage,
        'timestamp': reserve['timestamp']
    }
    for percentage, reserve in zip(user_percentages, pools_reserves)
]

assert len(user_holdings) == len(pools)

for holding, pool in zip(user_holdings, pools):
    holding['token0Address'] = pool['token0Address']
    holding['token1Address'] = pool['token1Address']
    holding['token0Symbol'] = pool['token0Symbol']
    holding['token1Symbol'] = pool['token1Symbol']

# Ok, merge user holdings into a single object.
def summarize(user_holdings:List[dict], include_token_address = False) -> dict:
    symbols = dict()
    for holding in user_holdings:
        symbols.setdefault(holding['token0Symbol'], 0)
        symbols.setdefault(holding['token1Symbol'], 0)
        if include_token_address:
            symbols.setdefault(holding['token0Address'], 0)
            symbols.setdefault(holding['token1Address'], 0)
    
    for holding in user_holdings:
        symbols[holding['token0Symbol']] += int(holding['token0'])
        symbols[holding['token1Symbol']] += int(holding['token1'])
        if include_token_address:
            symbols[holding['token0Address']] += int(holding['token0'])
            symbols[holding['token1Address']] += int(holding['token1'])
    
    return symbols

user_summarize = summarize(user_holdings)

token_definitions = json.load(open(TOKENS_DEFINITION, 'r'))

def find_decimals_by_token_name(tokens:List, name:str):
    for token in tokens:
        if token['symbol'].lower() == name.lower():
            return int(token['decimals'])
    return -1

decimals_dict = {token_name: find_decimals_by_token_name(token_definitions, token_name) for token_name in user_summarize.keys()}
user_summarize_human = {}
for token_name in user_summarize.keys():
    if decimals_dict[token_name] > 0:
        user_summarize_human[token_name] = int(user_summarize[token_name]/(10**decimals_dict[token_name]))

timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
with open(f'./zumo_results/Report_{TARGET_PERSON}_{timestamp}.json', 'w') as f:
    json.dump({
        'person': TARGET_PERSON,
        'holdings': user_summarize_human,
        'holdings_in_wei': user_summarize,
    }, f, indent=2)