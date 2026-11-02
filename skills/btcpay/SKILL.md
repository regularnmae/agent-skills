---
name: btcpay
description: Read this host's BTCPay Server settlement state -- stores, enabled payment rails, invoices and their per-rail payment status, the Bitcoin on-chain wallet, rates and payment requests -- through the read-only btcpay-mcp server or the agent-mcp CLI. Use for "what came in", "did that invoice settle", "on which rail", "what is the wallet balance". It cannot create or refund an invoice, pay out, generate an address or broadcast.
---

# BTCPay

Read-only view of the settlement engine behind BoltMesh: stores, payment rails,
invoices and their per-rail payments, the Bitcoin on-chain wallet, exchange
rates and payment requests. The credential behind it is a store-scoped key with
four `canview*` permissions, so nothing here can create or refund an invoice,
pay out, generate a receiving address or broadcast a transaction.

```sh
agent-mcp btcpay get_btcpay_health
agent-mcp btcpay list_stores
agent-mcp btcpay list_invoices status=Settled take=10
agent-mcp btcpay list_invoices start_date=1793491200 include_payment_methods=true
agent-mcp btcpay get_invoice invoice_id=AzCB7tdFKukm8dFCAuC8jc
agent-mcp btcpay get_invoice_payment_methods invoice_id=AzCB7tdFKukm8dFCAuC8jc
agent-mcp btcpay get_wallet_balance
agent-mcp btcpay list_wallet_transactions limit=10
agent-mcp btcpay --list
```

`agent-mcp` is on `PATH` after `install.sh`; otherwise it is
`~/.local/bin/agent-mcp`. A tool returns pretty-printed JSON.

**Native `btcpay` tools are the fastest path when this harness has them.**
`agent-mcp` is the same server for harnesses without MCP; the notes below apply
either way.

<!-- tools:start -->
| Tool | Arguments | Does |
| --- | --- | --- |
| `get_btcpay_health` | — | Report whether BTCPay answers and whether this server's key can read it. |
| `list_stores` | `limit?` | List the stores this key can read. |
| `get_store` | `store_id?` | Read one store's settings. |
| `list_payment_methods` | `store_id?`, `limit?` | List the payment rails enabled on a store. |
| `get_store_rates` | `currency_pairs`, `store_id?` | Read the exchange rates BTCPay uses to price invoices. |
| `list_invoices` | `store_id?`, `status?`, `text_search?`, `start_date?`, `end_date?`, `skip?`, `take?`, `include_payment_methods?` | List a store's invoices, newest first, with optional filters. |
| `get_invoice` | `invoice_id` | Read one invoice in full. |
| `get_invoice_payment_methods` | `invoice_id`, `limit?` | Read an invoice's per-rail payment state. |
| `get_wallet_balance` | `store_id?`, `payment_method?` | Read a store's on-chain wallet balance. |
| `list_wallet_transactions` | `store_id?`, `payment_method?`, `skip?`, `limit?` | List a store's on-chain wallet transactions, newest first. |
| `list_wallet_utxos` | `store_id?`, `payment_method?`, `limit?` | List a store's on-chain wallet UTXOs. |
| `list_payment_requests` | `store_id?`, `include_archived?`, `limit?` | List a store's payment requests. |
<!-- tools:end -->

## What you are reading

An **invoice** is one checkout attempt. `status` is one of `New`,
`Processing`, `Expired`, `Invalid` or `Settled`; `amount` is in the invoice's
own `currency` (usually USD), and `paidAmount` is what has been paid so far.
`createdTime`, `expirationTime` and `monitoringExpiration` are **Unix
seconds**; `start_date`/`end_date` take the same form (an RFC3339 instant is
converted, but the native form is the epoch). Amounts, rates and balances are
**decimal strings** -- do not turn them into floats and do not round them.

An invoice's **payment methods** are the rails it offered: `BTC-LN` (Lightning),
`BTC-CHAIN` (on-chain Bitcoin) and `XMR-CHAIN` (Monero, when the plugin's
view-only wallet is imported). Each row has its own `amount`/`due` in that
rail's currency (`BTC`, `XMR`), `paymentMethodPaid`/`totalPaid`, a `destination`
(BOLT11 invoice or address), and the individual `payments`. "Did it settle" is
usually `get_invoice_payment_methods`; `get_invoice` alone returns the invoice
without them on this BTCPay build.

The **wallet tools** read the store's BTCPay-managed on-chain wallet
(`BTC-CHAIN`), not the node's or the Monero plugin's. The Monero plugin does
not implement the Greenfield wallet endpoints, so there is no XMR balance tool;
XMR movement is visible on invoices.

## Reading the answers

- **Settled vs paid.** `Settled` on the invoice is final. A `New` invoice with a
  payment row may still be waiting for confirmations or for the Lightning
  payment to settle; read the rail's `payments` before saying it is done.
- **A full page is not the whole history.** BTCPay's list endpoints return no
  total; a full page sets `"truncated": true`. Page with `skip`/`take`
  (`take` max 100), or narrow by `status`/dates.
- **The preimage is redacted.** The server replaces
  `additionalData.preimage` with `"[redacted]"`; it is a secret that proves
  payment. Do not look for it anywhere else in a tool answer.
- **Internal links are rewritten.** When the stack sets `BTCPAY_PUBLIC_URL`, a
  `checkoutLink` points at the public BTCPay host, not at the internal
  `btcpay:49392` name.
- **A 403 is a permission, not an outage.** Run `get_btcpay_health`; it names
  the key's label and permissions. The key is read-only on purpose -- do not
  try to work around it with a write call, and do not ask for the admin key.
- **`get_btcpay_health` is a report, not an error.** `unconfigured` means no
  key is set, `degraded` means BTCPay refused the key or the store, `down`
  means BTCPay did not answer.
