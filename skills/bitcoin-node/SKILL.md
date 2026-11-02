---
name: bitcoin-node
description: Query a Bitcoin Core full node -- blocks, transactions, mempool, fee estimates, peers -- through the read-only bitcoin-node MCP server or the agent-mcp CLI. Use for chain-state and transaction questions, and for the txindex and block-verbosity caveats that change how you answer them.
---

# Bitcoin node

Read-only access to a Bitcoin Core full node, through the same MCP server the
`bitcoin-node` client config points at. No keys, no wallet, no chain writes.

```sh
agent-mcp bitcoin-node get_blockchain_info
agent-mcp bitcoin-node get_block_hash height=973000
agent-mcp bitcoin-node get_block blockhash=<hash> verbosity=1
agent-mcp bitcoin-node get_raw_transaction txid=<64 hex>
agent-mcp bitcoin-node --list
```

`agent-mcp` is on `PATH` after `install.sh`; otherwise it is
`~/.local/bin/agent-mcp`. A tool returns text: a scalar bare, an object as
pretty-printed JSON. Pipe it through `jq` when you need a field.

**Native `bitcoin-node` tools are the fastest path when this harness has them.**
`agent-mcp` is the same server for harnesses without MCP; the notes below apply
either way.

## The node

Full node, mainnet, every block on disk, `txindex` enabled.

- **`txindex` backfills.** Turning it on needs no `-reindex`, but Core builds
  the index from blocks already on disk and it takes hours. Until it catches
  up, `get_raw_transaction` answers `-5` for a recent transaction: pass
  `blockhash`. Find it with `get_block_hash(height)`, then
  `get_block(hash, verbosity=2)`.
- **`verbosity=2` is heavy.** A busy block holds thousands of transactions, so
  the full list runs to megabytes. Use verbosity 1 to list txids, and reach for
  2 only when hunting a txid the index cannot resolve.
- **No address index.** bitcoind cannot answer "which transactions touched this
  address". An Electrum server (Fulcrum) runs beside it for that; these tools
  cannot.

## Tools

<!-- tools:start -->
| Tool | Arguments | Does |
| --- | --- | --- |
| `get_blockchain_info` | — | Return the node's chain state. |
| `get_index_info` | `index_name?`, `verbose?` | Return the node's index build state, txindex included. |
| `get_block_hash` | `height` | Return the block hash at a height. |
| `get_block` | `blockhash`, `verbosity?` | Return a block by hash. |
| `get_block_header` | `blockhash`, `verbose?` | Return a block header by block hash. |
| `get_block_stats` | `height` | Return fee and transaction statistics for one block. |
| `get_fee_history` | `blocks?` | Return per-block feerate history for the most recent blocks. |
| `get_raw_transaction` | `txid`, `blockhash?`, `verbose?` | Return a transaction by id. |
| `get_mempool_entry` | `txid` | Return one unconfirmed transaction's mempool entry. |
| `decode_raw_transaction` | `hexstring` | Decode a serialised (hex) transaction into a JSON object. |
| `get_mempool_info` | — | Return statistics about the node's transaction mempool. |
| `get_raw_mempool` | `verbose?` | List the transaction ids currently in the mempool. |
| `get_tx_out` | `txid`, `n`, `include_mempool?` | Return details of an unspent transaction output (the UTXO set). |
| `get_network_info` | — | Return the node's network state: version, connections, relay fee. |
| `get_peer_info` | — | Return one entry per connected peer. |
| `estimate_smart_fee` | `conf_target?`, `mode?` | Estimate the fee rate needed to confirm within a number of blocks. |
| `get_difficulty` | — | Return the proof-of-work difficulty as a multiple of the minimum. |
<!-- tools:end -->

## Common questions

| Question | Call |
| --- | --- |
| Is the node synced, and on which chain? | `get_blockchain_info` |
| What is the tip height and hash? | `get_blockchain_info` -> `blocks`, `bestblockhash` |
| What block is a tx in? | `get_raw_transaction txid=<id>` -> `blockhash`/`blockheight` (txindex) |
| Is this UTXO still unspent? | `get_tx_out txid=<id> n=<vout>` |
| What fee for 3 blocks? | `estimate_smart_fee conf_target=3` |
| Who are we connected to? | `get_peer_info`, `get_network_info` |
