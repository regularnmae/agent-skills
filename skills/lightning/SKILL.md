---
name: lightning
description: Read a Core Lightning node -- channels, peers, funds, invoices, payments -- and decode BOLT11 invoices, through the read-only lightning MCP server or the agent-mcp CLI. Use for node and channel state, payment history, and what a BOLT11 invoice commits to before anyone pays it.
---

# Lightning

```sh
agent-mcp lightning getinfo
agent-mcp lightning listfunds
agent-mcp lightning listchannels
agent-mcp lightning decode bolt11=<invoice>
agent-mcp lightning --list
```

**Read tools only here**: no `pay`, `invoice`, `keysend`, `withdraw` or
`close` on this deployment. `decode` is local and safe -- it never pays.

**Native `lightning` tools are the fastest path when this harness has them.**
`agent-mcp` is the same server for harnesses without MCP; the notes below apply
either way.

## Using it

- `getinfo` first: node id, alias, network, block height, peer count. A block
  height well behind `bitcoin-node` means a node that is not following the tip.
- `listfunds` is on-chain outputs and channel balances; `listchannels` is the
  per-channel state. A channel that is not `CHANNELD_NORMAL` is not payable.
- `listinvoices label=<label>` and `listpays bolt11=<invoice>` narrow by
  label or invoice; with no argument you get the full history, which is large.
- `decode bolt11=<invoice>` before anyone pays: amount, expiry, description,
  payee node id. Check the payee matches the node you mean to pay.

## Tools

<!-- tools:start -->
| Tool | Arguments | Does |
| --- | --- | --- |
| `getinfo` | — | Return node information: id, alias, network, block height, peers. |
| `listfunds` | — | Return on-chain outputs and channel funds. |
| `listchannels` | — | Return the node's channels. |
| `listpeers` | — | Return the node's peers. |
| `listinvoices` | `label?` | Return invoices; optionally only one by label. |
| `listpays` | `bolt11?` | Return outgoing payments; optionally only one by bolt11. |
| `decode` | `bolt11` | Decode a BOLT11 invoice without paying it. |
<!-- tools:end -->
