## Folders
```bash
/zumo_abis     # abi extracted from zumo repo
/zumo_pools    # runtime extracted zumo pools contracts
/zumo_info     # runtime extracted zumo key contracts
/zumo_results  # txs, receipts, blocks + analysis
```

## Scripts

```bash
python3 scrapper.py [node_url] [start_block]  # Extract from blockchain, blocks, txs, receipts info
python3 post_process.py                       # Enrich the receipts, inject decoded events
python3 analyze.py                            # Analyze the current exchange status (pools, etc)
python3 personal_now.py [addr] [node_url]     # Summarize a person's lp holdings on the DEX
python3 personal_history.py [addr]            # Person's trading history on DEX
python3 calculate_apy.py [node_url]           # Calculate pools APY (no token reward included)
```