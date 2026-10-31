# Tool reference

All thirteen tools, what they take, what comes back, and where each one bites.
Every tool returns text: a scalar as itself (a hash, a number) and an object as
pretty-printed JSON.

## Chain state

### `get_blockchain_info`
No arguments.

Returns `chain`, `blocks`, `headers`, `bestblockhash`, `difficulty`, `time`,
`mediantime`, `verificationprogress`, `initialblockdownload`, `chainwork`,
`size_on_disk`, `pruned`, and `pruneheight` (only when pruned).

Gotchas: `blocks` and `headers` diverge while syncing. `pruneheight` is absent
on a full node -- treat it as "no floor" rather than zero.

### `get_block_hash`
`height` (integer, 0 is genesis).

Returns the block hash as a bare string -- the input to `get_block` and
`get_raw_transaction`'s `blockhash`.

Gotcha: it accepts a height the node has not reached and answers with an error;
check `blocks` first.

### `get_block`
`blockhash` (string), `verbosity` (1 or 2, default 1).

Verbosity 1: header fields plus `tx` as a list of txids -- a few hundred KiB on
a full block. Verbosity 2: every transaction decoded -- several MiB.

Gotcha: this is the single most expensive call here. On a pruned node a block
below `pruneheight` is not on disk, and the tool says so instead of leaking the
raw `-1 Block not available (pruned data)`.

### `get_block_header`
`blockhash` (string), `verbose` (default true).

Returns the decoded header, or the 80-byte hex when `verbose=false`. Cheap, and
enough for height/time/previous-block questions without touching a full block.

## Transactions

### `get_raw_transaction`
`txid` (string), `blockhash` (string, optional), `verbose` (default true).

Returns the decoded transaction, or hex when `verbose=false`.

Gotcha: with `txindex` off or still backfilling, a confirmed transaction needs
its `blockhash`, and without one the node answers `-5`. The tool turns that into
an explanation. With `txindex` on, `txid` alone is enough.

### `decode_raw_transaction`
`hexstring` (string).

Decodes a serialised transaction into JSON. Useful for a transaction handed to
you as hex -- no node state needed, and safe on untrusted input since it decodes
rather than submits.

## Mempool

### `get_mempool_info`
No arguments.

`size`, `bytes`, `usage`, `maxmempool`, `mempoolminfee`, `minrelaytxfee`,
`incrementalrelayfee`, `unbroadcastcount`, `loaded`. Cheap.

### `get_raw_mempool`
`verbose` (default false).

False: a list of txids -- potentially tens of thousands of lines. True: a map of
txid to fee, size, time, dependencies -- larger still.

Gotcha: never call this to "see what is happening"; use `get_mempool_info` for
volume and this only for a specific txid hunt.

## UTXO set

### `get_tx_out`
`txid` (string), `n` (integer, 0-based vout), `include_mempool` (default true).

Returns `bestblock`, `confirmations`, `value`, `scriptPubKey`, `coinbase`, or
`null`.

Gotcha: `null` means "not in the UTXO set" -- spent, never existed, or unconfirmed
with `include_mempool=false`. It is not a judgement about an address.

## Network

### `get_network_info`
No arguments.

`version`, `subversion`, `protocolversion`, `localservices`, `localrelay`,
`timeoffset`, `networkactive`, `connections`, `connections_in`, `connections_out`,
`networks`, `relayfee`, `incrementalfee`, `localaddresses`, `warnings`.

### `get_peer_info`
No arguments.

One entry per peer: `addr`, `version`, `subver`, `inbound`, `startingheight`,
`synced_headers`, `synced_blocks`, `pingtime`, `bytessent`, `bytesrecv`,
`inflight`, `relaytxes`.

Gotcha: on a node with many peers this is a large reply. Summarise (count,
inbound vs outbound, worst ping) instead of dumping it.

## Fees and difficulty

### `estimate_smart_fee`
`conf_target` (integer 1..1008, default 6), `mode` (`conservative` default,
`economical`, `unset`).

Returns `feerate` in BTC/kvB and `blocks`, or an `errors` array when the node
has no estimate.

Gotchas: the unit is BTC per 1000 vbytes. There is no `feerate` at all in the
error case -- report the absence, never a remembered number.

### `get_difficulty`
No arguments.

The proof-of-work difficulty as a multiple of the minimum, as a bare number.
Change over time, not a percentage.
