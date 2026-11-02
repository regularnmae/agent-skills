---
name: victoriametrics
description: Query this host's metrics history -- chain sync progress, disk, memory, service health, backup age and the stack_* series -- with PromQL through the read-only victoriametrics MCP server or the agent-mcp CLI. Use to answer how fast, how much or how long, and whether the scrape and textfile collector are still writing.
---

# VictoriaMetrics

Read-only PromQL over the stack's metrics store: node-exporter +
`scripts/metrics.sh` -> `victoriametrics`, 30 days by default. Nothing here
writes, deletes or changes anything.

```sh
agent-mcp victoriametrics get_metrics_health
agent-mcp victoriametrics list_targets
agent-mcp victoriametrics query query='up'
agent-mcp victoriametrics query query='stack_btc_headers - stack_btc_blocks'
agent-mcp victoriametrics query_range query='stack_btc_progress' start=7d step=1h
agent-mcp victoriametrics list_metrics pattern='^stack_'
agent-mcp victoriametrics list_series match='{job="node"}'
agent-mcp victoriametrics list_labels
agent-mcp victoriametrics list_label_values label=job
agent-mcp victoriametrics --list
```

`agent-mcp` is on `PATH` after `install.sh`; otherwise it is
`~/.local/bin/agent-mcp`. A tool returns text: a scalar bare, an object as
pretty-printed JSON. Pipe it through `jq` when you need a field.

**Native `victoriametrics` tools are the fastest path when this harness has
them.** `agent-mcp` is the same server for harnesses without MCP; the notes
below apply either way.

## The store

VictoriaMetrics scrapes two jobs -- `node` (the host, plus every `stack_*`
textfile series) and `victoriametrics` (itself). The labels worth knowing:

| Field | Meaning |
| --- | --- |
| `__name__` | The metric name |
| `job` | `node` or `victoriametrics` |
| `instance` | The scrape address the stack pins |
| `device`, `mode`, `mountpoint`, `fstype`, … | node-exporter's own labels |

The numbers no exporter produces are the stack's own:

```
stack_btc_blocks, stack_btc_headers, stack_btc_progress, stack_btc_ibd
stack_btc_peers, stack_btc_mempool_bytes, stack_btc_mempool_txs
stack_xmr_height, stack_xmr_lag, stack_xmr_synced, stack_xmr_rpc_up
stack_fulcrum_up, stack_fulcrum_electrum_up, stack_fulcrum_lag
stack_cln_peers, stack_cln_channels_offline
stack_backup_age_seconds, stack_backup_snapshots, stack_backup_verify_ok
stack_collector_error{collector="…"}, stack_metrics_timestamp
```

## PromQL

`query` and `query_range` take Prometheus's language unchanged:

```
up                                            every scrape target
stack_btc_progress                            chain sync progress (0..1)
stack_btc_headers - stack_btc_blocks          blocks behind
rate(node_network_receive_bytes_total[5m])    receive rate
avg by (job) (up)                             targets up per job
stack_cln_peers < 1                           CLN with no peers
```

A time argument (`time`, `start`, `end`) takes a duration meaning "that long
ago" (`1h`, `7d`) or an RFC3339 instant (`2026-11-02T10:00:00Z`). `step` takes
a duration (`30s`, `1m`, `1h`) or whole seconds. `query_range` defaults to the
last hour at one-minute resolution.

## Tools

<!-- tools:start -->
| Tool | Arguments | Does |
| --- | --- | --- |
| `query` | `query`, `time?`, `limit?` | Run a PromQL instant query, evaluated at one point in time. |
| `query_range` | `query`, `start?`, `end?`, `step?`, `limit?` | Evaluate a PromQL expression over a time window. |
| `list_metrics` | `pattern?`, `limit?` | List the metric names the store holds, optionally filtered. |
| `list_series` | `match`, `start?`, `end?`, `limit?` | List the label sets that match a series selector. |
| `list_labels` | `match?` | List the label names in the store, case-sorted. |
| `list_label_values` | `label`, `match?`, `limit?` | List the distinct values of a label, sorted. |
| `list_targets` | — | List what VictoriaMetrics is scraping, and whether each target is up. |
| `get_metrics_health` | — | Report whether the store and its collection pipeline are healthy. |
<!-- tools:end -->

## Reading the answers

- **A range query never changes your resolution.** More than 1000 points per
  series is refused with the smallest step that fits. Raise `step` or shorten
  the window; do not expect the server to thin the data for you.
- **Every tool caps its answer.** 100 series by default (50 for a range
  query), 1000 at most, a label value truncated at 2 KiB, and a 512 KiB
  response budget. A response that hits the budget carries
  `"truncated": true` — narrow the query rather than paging.
- **`get_metrics_health` first when a graph has a gap.** `status` is `ok`,
  `degraded` (a target down or a `stack_collector_error`), `stale` (the
  textfile collector's heartbeat is old or missing) or `empty` (no series at
  all). The stack's monitor fails on the same heartbeat, so `ok` here means the
  history is still being written.
- **Retention is finite.** 30 days by default. An empty answer for an old
  window may mean the samples were dropped, not that nothing happened.
- **Names are exact.** `stack_btc_blocks` exists; `btc_blocks` does not, and a
  name that does not exist is an empty result rather than an error.
  `list_metrics pattern=...` is how you check a name.
- **Values are strings.** A sample is `[timestamp, "1"]`; `NaN` and `+Inf` are
  spelled that way. Do not assume a JSON float.
- **Failures are tool errors.** An unreachable store or a PromQL parse error
  comes back as `isError: true` with the store's own message. Nothing matched is
  a successful, empty answer — do not conflate the two.

## Common questions

| Question | Call |
| --- | --- |
| Is the metrics pipeline still writing? | `get_metrics_health` |
| What is being scraped? | `list_targets` |
| How far behind is bitcoind? | `query query='stack_btc_headers - stack_btc_blocks'` |
| How fast did the chain sync? | `query_range query='stack_btc_blocks' start=7d step=1h` |
| Is the disk filling? | `query_range query='node_filesystem_avail_bytes{mountpoint="/"}' start=7d step=1h` |
| Is memory tight? | `query query='node_memory_MemAvailable_bytes'` |
| Which metrics exist? | `list_metrics pattern='^stack_'` |
| Which instances report? | `list_label_values label=instance` |
| Why is the graph empty? | `get_metrics_health`, then `list_targets` |
| When did the node last restart? | `query query='node_boot_time_seconds'` (compare with the uptime series) |
