---
name: monero-node
description: Query a Monero daemon from a shell -- height, blocks, transactions, fee estimates, pool stats -- through the read-only monero-node MCP server. Use when the native monero-node MCP tools are not available in this harness.
---

# Monero node

A node, not a wallet: this surface sees no keys and moves no funds.

```sh
agent-mcp monero-node get_info
agent-mcp monero-node get_block_count
agent-mcp monero-node get_block height=3500000
agent-mcp monero-node --list
```

**If this session already has native `monero-node` MCP tools, prefer them.**
This skill calls the same server.

## What to expect

- The daemon's **restricted** RPC is what the server exposes: public read
  methods only. A method answering that it is unavailable is the restricted
  surface, not a failure worth retrying.
- Start with `get_info`: height, target height, sync state and whether the
  daemon is still catching up. A block height below the target height while
  `synchronized` is false means the answer is provisional.
- `get_block` takes either `height` or `block_hash`, and a block with many
  transactions is large.
- `get_transactions` takes a **list** of txids. Pass it as JSON to dodge shell
  quoting: `agent-mcp monero-node get_transactions --json '{"txids":["<id>"]}'`.

## Tools

<!-- tools:start -->
| Tool | Arguments | Does |
| --- | --- | --- |
| `get_info` | — | Return the node's state. |
| `get_block_count` | — | Return the number of blocks in the longest chain. |
| `get_last_block_header` | — | Return the most recent block's header. |
| `get_block_header_by_height` | `height` | Return a block header by height. |
| `get_block_header_by_hash` | `block_hash` | Return a block header by block hash. |
| `get_block` | `height?`, `block_hash?` | Return a block's header and decoded contents. |
| `get_version` | — | Return the daemon's version. |
| `get_fee_estimate` | `grace_blocks?` | Return a fee estimate for inclusion within a number of blocks. |
| `get_transactions` | `txids`, `decode_as_json?` | Return transactions by id. |
| `get_transaction_pool_stats` | — | Return statistics about the node's transaction pool. |
<!-- tools:end -->
