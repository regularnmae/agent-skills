---
name: fulcrum
description: Query a Fulcrum Electrum index -- address history, balances, UTXOs, mempool fees, transaction lookup, merkle proofs, block headers and fee estimates -- through the read-only fulcrum MCP server or the agent-mcp CLI. Use for address questions a Bitcoin node cannot answer, and for the indexer-lag caveat that changes how you read a "no history" answer.
---

# Fulcrum index

Read-only access to a Fulcrum Electrum server, which indexes the chain by
address -- the one question `bitcoind` cannot answer. No keys, no wallet, no
chain writes.

```sh
agent-mcp fulcrum get_chain_tip
agent-mcp fulcrum get_address_balance address=bc1q...
agent-mcp fulcrum get_address_history address=bc1q... limit=100
agent-mcp fulcrum get_address_utxos address=bc1q...
agent-mcp fulcrum get_transaction txid=<64 hex>
agent-mcp fulcrum --list
```

`agent-mcp` is on `PATH` after `install.sh`; otherwise it is
`~/.local/bin/agent-mcp`. A tool returns text: a scalar bare, an object as
pretty-printed JSON. Pipe it through `jq` when you need a field.

**Native `fulcrum` tools are the fastest path when this harness has them.**
`agent-mcp` is the same server for harnesses without MCP; the notes below apply
either way.

## The indexer

Fulcrum subscribes to `bitcoind` and builds its own transaction, output and
address index. Three consequences:

- **Scripthashes, not addresses.** Electrum indexes the SHA-256 of an output
  script, byte-reversed. The address tools decode a normal address for you:
  P2PKH (`1…`), P2SH (`3…`), bech32 (`bc1q…`) and taproot (`bc1p…`), plus
  testnet and regtest prefixes. The address's network is not checked against
  the server's.
- **Fulcrum's tip can lag the node.** `get_chain_tip` is the reference for what
  the index has seen. Compare it with `bitcoin-node get_blockchain_info`
  before trusting a "no history" answer for a recent transaction. Fulcrum
  reports its tip even while it is catching up.
- **`get_transaction` does not need `txindex`.** Fulcrum indexes every
  transaction itself, so a confirmed lookup works even when the node's
  `txindex` is off or backfilling.

## Tools

<!-- tools:start -->
| Tool | Arguments | Does |
| --- | --- | --- |
| `get_address_balance` | `address` | Return an address's balance as Fulcrum sees it, in satoshis. |
| `get_address_history` | `address`, `limit?`, `offset?` | Return the transactions an address has touched, one page at a time. |
| `get_address_utxos` | `address` | Return an address's unspent outputs, in satoshis. |
| `get_address_mempool` | `address` | Return an address's unconfirmed transactions, with the fee each pays. |
| `get_transaction` | `txid`, `verbose?` | Return a transaction by id, from Fulcrum's own index. |
| `get_transaction_merkle` | `txid`, `height` | Return a transaction's merkle branch in the block at `height`. |
| `get_chain_tip` | — | Return the chain tip Fulcrum is serving: height, hash and block time. |
| `get_block_header` | `height` | Return a block's hash, timestamp and raw 80-byte header, by height. |
| `get_fee_estimate` | `blocks?` | Return Fulcrum's fee estimate for confirmation within `blocks`. |
| `get_server_info` | — | Return the server's features: version, genesis hash, protocol range. |
<!-- tools:end -->

## Reading the answers

- **History is paginated.** `get_address_history` returns up to `limit` (default
  1000, max 10000) mined entries from `offset`, oldest first. `confirmed_count`
  is the total, not the page size; when `next_offset` is not null, call again
  with it. The mempool list is always whole. Heights 0 and -1 are unconfirmed
  (the latter with unconfirmed parents).
- **Balances are satoshis.** A negative `unconfirmed` means the address has
  spent coins that are not mined yet.
- **Mempool fees are satoshis.** `get_address_mempool` is the fee-aware view of
  the same unconfirmed transactions history lists.
- **Merkle proofs need a height.** The protocol has no txid-to-height lookup,
  so take `height` from `get_address_history` (or a block you know) before
  calling `get_transaction_merkle`. `pos` is the transaction's position in the
  block; `merkle` is the branch.
- **Fee estimates come in two units.** `btc_per_kvb` is what Electrum returns;
  `sat_per_vb` is the same rate converted. A target with no estimate answers
  nulls plus a note -- do not read that as zero.
- **Failures are tool errors.** An invalid address, a malformed answer from the
  indexer, or an unreachable Fulcrum comes back as `isError: true` with a
  readable message. An empty history is a successful answer, so do not conflate
  the two.

## Common questions

| Question | Call |
| --- | --- |
| What is the indexer's tip? | `get_chain_tip` |
| Which transactions touched this address? | `get_address_history address=<addr>` (page with `next_offset`) |
| What does this address hold? | `get_address_balance address=<addr>`, `get_address_utxos address=<addr>` |
| Is my payment stuck in the mempool? | `get_address_mempool address=<addr>` -> `fee`, `height` |
| Is this transaction confirmed, and in which block? | `get_address_history` for the height, then `get_transaction_merkle txid=<id> height=<h>` |
| When was that block mined? | `get_block_header height=<h>` -> `time` |
| What fee for 6 blocks? | `get_fee_estimate blocks=6` |
| Which network is this indexer on? | `get_server_info` -> `genesis_hash` |
