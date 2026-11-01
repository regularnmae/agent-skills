---
name: crypto-stack
description: Answer questions about this crypto stack as a whole -- health, sync heights, fee sanity, and verifying a payment across Bitcoin, Lightning and Monero -- using the bitcoin-node, fulcrum, lightning, monero-node and monero-wallet tools or the agent-mcp CLI. Use when a question spans more than one server, or when a number from one needs checking against another.
---

# The stack as a whole

Five servers, one per layer: `bitcoin-node`, `fulcrum` (Bitcoin's address
index), `lightning`, `monero-node`, `monero-wallet`. Each has its own skill for
its tools; this one holds the playbooks that span them.

Every command is `agent-mcp <server> <tool>`; when this harness has the native
MCP tools, call the same tool name directly. Nothing here moves funds.

## Is the stack healthy?

```sh
agent-mcp bitcoin-node get_blockchain_info
agent-mcp fulcrum get_chain_tip
agent-mcp lightning getinfo
agent-mcp monero-node get_info
agent-mcp monero-wallet get_height
```

Read them together, not one at a time:

| Signal | Healthy | Sick |
| --- | --- | --- |
| `bitcoin-node` `initialblockdownload` | `false` | `true`: heights are provisional |
| `bitcoin-node` `verificationprogress` | ~1.0 | below 0.999: still validating |
| `fulcrum` `get_chain_tip` height | within a few blocks of bitcoin `blocks` | far behind: the index is still catching up |
| `lightning` `blockheight` | within a few blocks of bitcoin `blocks` | far behind: CLN is not following the tip |
| `monero-node` `height` vs `target_height` | equal | below it: the daemon is catching up |
| `monero-node` `synchronized` | `true` | `false`: answers are provisional |
| `monero-wallet` `get_height` | at or just under the monero height | far under: the wallet is still scanning |

Two different clocks: Bitcoin and Monero heights are unrelated, so only compare
a height with its own server's target. Lightning is the exception -- it sits on
Bitcoin, so its blockheight *does* belong next to the Bitcoin tip.

## Did a payment land?

Work down the layer it was supposed to arrive on; do not infer one layer from
another.

**Lightning**

```sh
agent-mcp lightning decode bolt11=<invoice>
agent-mcp lightning listpays bolt11=<invoice>
```

`decode` is local and never pays. It gives the payee node id, `amount_msat`,
expiry and description -- check the payee is the node you meant before trusting
anything else. `listpays` then reports `status`: `complete` means a preimage
was settled, `pending` means in flight, `failed` means it will not settle.
A completed payment still needs `listchannels` to show the channel
`CHANNELD_NORMAL` before the funds are really spendable.

**Bitcoin on-chain**

```sh
agent-mcp bitcoin-node get_raw_transaction txid=<64 hex>
agent-mcp bitcoin-node get_tx_out txid=<64 hex> n=<vout>
```

`confirmations` is the answer to "did it land"; `get_tx_out` is the answer to
"is that output still unspent". A txid in the mempool has zero confirmations
and is not final.

For an **address** rather than a txid, `bitcoind` has no index; use Fulcrum:

```sh
agent-mcp fulcrum get_address_history address=<addr>
agent-mcp fulcrum get_address_utxos address=<addr>
agent-mcp fulcrum get_address_balance address=<addr>
```

`get_chain_tip` is the height that history is complete to. If it lags
`bitcoin-node`'s `blocks`, a "no history" answer for a recent payment means
"not indexed yet", not "not sent".

**Monero**

```sh
agent-mcp monero-wallet get_transfer_by_txid txid=<id>
agent-mcp monero-wallet get_payments payment_id=<hex>
```

`get_transfer_by_txid` only knows transfers **this wallet** took part in; it is
not a public explorer. `get_payments` is how an invoice's `payment_id` is tied
to what actually arrived.

## Fee sanity

```sh
agent-mcp bitcoin-node estimate_smart_fee conf_target=3
agent-mcp monero-node get_fee_estimate grace_blocks=3
```

Never compare the two numbers directly. Bitcoin answers in BTC per kvB (and
`mode` says whether it is `ECONOMICAL`, `CONSERVATIVE` or `UNSET`); Monero
answers in atomic units per kB. Convert to a per-byte rate for each chain before
saying one is "cheaper". A Bitcoin estimate with no `feerate` means the node
could not estimate -- it is not a zero fee.

## Units, before you quote a number

| Server | Amounts arrive as |
| --- | --- |
| `bitcoin-node` | BTC (8 decimals); fees as BTC/kvB |
| `lightning` | `msat` in JSON (`amount_msat`), 1 sat = 1000 msat |
| `monero-node` | atomic units (piconero), 1 XMR = 10^12 |
| `monero-wallet` | atomic units, sometimes with a display value beside it |

Converting wrongly is the most common way these skills produce a confident
wrong answer. Read the field name before dividing.

## When the numbers disagree

1. Check sync first (`get_blockchain_info`, `get_info`, `get_height`) -- a
   lagging server is not contradicting the others, it is behind them.
2. Check units second.
3. Only then treat it as a real disagreement, and say which servers you asked
   and what each returned.
