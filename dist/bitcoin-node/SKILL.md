---
name: bitcoin-node
description: Use when the user asks about Bitcoin chain state, a block, a transaction, the mempool, fees or peers -- for example "how synced is my node", "what block is this tx in", "is this UTXO spent", "what fee for 3 blocks", "is my node connected" -- reading a Bitcoin Core node through the read-only bitcoin-node-mcp server.
---

# Bitcoin node

Answer Bitcoin questions from a real node instead of an explorer, using the
`bitcoin-node-mcp` server: 13 read-only tools over Bitcoin Core's JSON-RPC.
No keys, no wallet, no chain writes. If a tool you expected is missing, that is
deliberate -- the server exposes reads only.

Setup is the user's job: the server runs next to their node and their client is
configured to talk to it. Once it is, the tools appear as normal MCP tools.

## Always start here

`get_blockchain_info` -- chain, height, headers, sync progress, difficulty,
`pruned`, and `pruneheight` when pruned.

Read three fields before answering anything about "the tip":

| Field | Meaning |
| --- | --- |
| `blocks` vs `headers` | `blocks < headers` means the node is still catching up |
| `initialblockdownload` | `true` means its view is not trustworthy yet |
| `verificationprogress` | below ~0.999 is the same warning in another shape |

If the node is behind, say so and give the height it is actually at. Do not
present a stale height as current, and do not silently fall back to guessing.

## Looking up a transaction

`get_raw_transaction txid=<id>` first, always.

- It resolves -> read `blockhash`, `blockheight`, `confirmations` from the reply.
  Done; this is the normal path on a node with `txindex`.
- It answers `-5` ("No such mempool transaction") -> one of two things:
  the transaction is confirmed but the node's `txindex` is off or still
  backfilling, or the txid does not exist.
- `-5` on a mempool transaction means it is not there: dropped, replaced, or
  never relayed to this node.

**The fallback needs a block hash, and finding it is the expensive part.**

1. `get_block_hash height=<h>` turns a height into a hash.
2. `get_block blockhash=<hash> verbosity=2` returns every transaction in the
   block -- in full.

Step 2 is the trap. A busy block holds thousands of transactions and the reply
runs to megabytes, which lands in the conversation and can blow the context
budget. Ask for `verbosity=1` first to see how big the block is, and only take
`verbosity=2` when the user has a real need. If the height is unknown, say so
and ask for it (or for the block hash); scanning blocks height by height is not
a lookup strategy.

## Fees

`estimate_smart_fee conf_target=<blocks>` with `conf_target` 1..1008 and `mode`
`conservative` (default), `economical`, or `unset`.

The reply is a **feerate in BTC/kvB**. Convert before quoting: divide by 1000
for BTC/vB, then multiply by 1e8 for sat/vB. `1e-5` BTC/kvB is 1 sat/vB.

When the node has no estimate it returns an `errors` array and no `feerate`.
Report that honestly ("the node has no fee estimate for 3 blocks right now");
never substitute a number from memory.

## Mempool

- `get_mempool_info` -- size, count, memory usage. Cheap, always fine.
- `get_raw_mempool verbose=false` -- one txid per line, and on a busy node that
  is tens of thousands of lines (megabytes). Use `verbose=true` only when the
  user wants details on a handful of transactions, never to "look around".

## Is this output spent?

`get_tx_out txid=<id> n=<vout>` reads the UTXO set, not the transaction index,
so it works on any node.

`null` means the output is not in the UTXO set: already spent, never existed, or
still in the mempool while `include_mempool=false`. An unspent output comes back
with `value`, `scriptPubKey`, `confirmations`. Do not turn `null` into
"that address is invalid" -- it says nothing about the address.

## Network and peers

- `get_network_info` -- version, subversion, protocol, connection counts, relay
  fee, whether the node is network-active.
- `get_peer_info` -- one entry per peer: address, version, ping, sync state.

"Not synced" and "no peers" are different diagnoses: check connections before
blaming the chain, and check `networkactive` before blaming the network.

## Reporting results

- Amounts are BTC in JSON; convert to sats when talking to a human.
- Timestamps are Unix seconds; convert to a date before quoting.
- Hashes are hex without a prefix; keep them whole or truncate symmetrically
  (`00000000000000000001...cd91eb`), never invent characters.
- Summarise: the user wants the answer and the evidence, not a raw JSON dump.

## What this node cannot answer

- **Address history.** Bitcoin Core has no address index, so "which transactions
  touched this address" or "what is this address's balance" is not answerable
  here. Say so and point to an Electrum-style server or a block explorer; do not
  approximate it from `get_tx_out` calls.
- **Broadcasting, signing, wallet operations.** Not exposed, by design.
- **Merkle proofs of inclusion.** Not exposed.

## Common questions

| Question | Call |
| --- | --- |
| Is the node synced, and on which chain? | `get_blockchain_info` |
| What is the tip height and hash? | `get_blockchain_info` -> `blocks`, `bestblockhash` |
| What block is this tx in? | `get_raw_transaction txid=<id>` |
| What fee for 3 blocks? | `estimate_smart_fee conf_target=3` |
| Is this UTXO still unspent? | `get_tx_out txid=<id> n=<vout>` |
| How busy is the mempool? | `get_mempool_info` |
| Who are we connected to? | `get_peer_info`, `get_network_info` |
| How big is the chain on disk? | `get_blockchain_info` -> `size_on_disk` |

Per-tool arguments, return shapes and gotchas: [references/tools.md](references/tools.md).
