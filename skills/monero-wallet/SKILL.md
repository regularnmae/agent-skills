---
name: monero-wallet
description: Read a Monero wallet's balance, addresses, accounts, transfers and payments through the read-only monero-wallet MCP server or the agent-mcp CLI. Use to confirm what a wallet holds and whether a transfer arrived, and to check sync height before trusting a balance.
---

# Monero wallet

```sh
agent-mcp monero-wallet get_balance
agent-mcp monero-wallet get_accounts
agent-mcp monero-wallet get_transfers incoming=true
agent-mcp monero-wallet --list
```

**This deployment exposes read tools only** -- no transfer, sweep or address
creation. Do not treat this skill as a way to move funds; a spend is an
operator action outside these tools, not something to work around here.

**Native `monero-wallet` tools are the fastest path when this harness has them.**
`agent-mcp` is the same server for harnesses without MCP; the notes below apply
either way.

## Reading the wallet

- `get_balance` and `get_accounts` first; `account_index` defaults to 0 and
  every other call takes it too, so multi-account wallets need it explicitly.
- `get_transfers` reads the wallet's own history. `incoming`, `outgoing`,
  `pending`, `failed` and `pool` are independent flags -- ask for the ones you
  need rather than everything.
- `get_payments payment_id=<hex>` is the way to tie an invoice to what actually
  arrived; `get_transfer_by_txid txid=<id>` is the way to check one transfer.
- A balance is in the wallet's synced state. Compare `get_height` with the node's
  height (`monero-node` skill) before treating the numbers as final.

## Tools

<!-- tools:start -->
| Tool | Arguments | Does |
| --- | --- | --- |
| `get_balance` | `account_index?` | Return the wallet's balance. |
| `get_address` | `account_index?` | Return the primary address of an account. |
| `get_accounts` | — | Return the wallet's accounts (index, label, balance). |
| `get_height` | — | Return the wallet's synced height. |
| `get_transfers` | `incoming?`, `outgoing?`, `pending?`, `failed?`, `pool?`, `account_index?` | Return the wallet's transfers. |
| `get_transfer_by_txid` | `txid` | Return details of a transfer by its transaction id. |
| `get_payments` | `payment_id`, `account_index?` | Return payments received with a given payment id. |
| `incoming_transfers` | `account_index?` | Return the wallet's incoming transfers. |
<!-- tools:end -->
