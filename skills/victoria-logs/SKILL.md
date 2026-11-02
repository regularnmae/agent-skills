---
name: victoria-logs
description: Search this host's log history -- every container's stdout and the host scripts' output -- with LogsQL through the read-only victoria-logs MCP server or the agent-mcp CLI. Use to find out why a service failed, who is spamming the journal, or whether the log pipeline is still shipping.
---

# VictoriaLogs

Read-only search over the stack's log store: journald -> `vector` ->
`victoria-logs`, 14 days or 10 GiB by default, whichever comes first. Nothing
here writes, deletes or changes anything.

```sh
agent-mcp victoria-logs get_log_health
agent-mcp victoria-logs tail_logs since=15m limit=50
agent-mcp victoria-logs top_sources since=1h
agent-mcp victoria-logs error_summary since=6h
agent-mcp victoria-logs list_field_values field=container since=24h
agent-mcp victoria-logs search_logs query='container:"lightningd" ~"WARN"' since=2h
agent-mcp victoria-logs get_context at=2026-11-02T03:10:00Z container=bitcoind
agent-mcp victoria-logs --list
```

`agent-mcp` is on `PATH` after `install.sh`; otherwise it is
`~/.local/bin/agent-mcp`. A tool returns text: a scalar bare, an object as
pretty-printed JSON. Pipe it through `jq` when you need a field.

**Native `victoria-logs` tools are the fastest path when this harness has
them.** `agent-mcp` is the same server for harnesses without MCP; the notes
below apply either way.

## The store

`vector` ships journald into VictoriaLogs, so every container's stdout and every
host script's output is in there. The fields these tools return:

| Field | Meaning |
| --- | --- |
| `_time` | RFC3339 UTC timestamp (the store's clock) |
| `_msg` | The log line |
| `container` | The container name, for container output |
| `unit` | The systemd unit, for host-script output |
| `host` | The machine-id-derived host label |
| `priority` | `emerg` … `debug`; BoltMesh's app level overrides journald's |

A host script has a `unit` and no `container`; a container has both `container`
and its own `host`. Suricata's alerts have a `unit` (`suricata.service`) and
extra fields this server does not return — use `scripts/logs.sh --json` on the
host when you need those.

## LogsQL

`search_logs` prepends `since` as `_time:<since>`, so a query cannot scan the
whole retention by accident. Everything after that is the store's language:

```
container:"bitcoind"                          one container
unit:"monitor.service"                        one host script
priority:in(emerg,alert,crit,err)             error and worse
~"timeout|refused"                            a regex over the message
container:"lightningd" | stats count() as n   a pipe
```

`since` takes a duration (`15m`, `2h`, `7d`) or an RFC3339 instant
(`2026-11-02T10:00:00Z`) — the latter for "since that deploy".

## Tools

<!-- tools:start -->
| Tool | Arguments | Does |
| --- | --- | --- |
| `search_logs` | `query`, `since?`, `limit?` | Search the log store with a LogsQL query, newest entries first. |
| `tail_logs` | `since?`, `limit?` | Return the most recent entries from every source, newest first. |
| `top_sources` | `since?`, `limit?` | Count log entries per container in the window, busiest first. |
| `error_summary` | `since?`, `limit?` | Summarise error-and-worse lines as bursts per container and unit. |
| `list_field_values` | `field?`, `since?`, `limit?` | List the distinct values of a field, most frequent first. |
| `get_log_health` | — | Report whether the log pipeline is still shipping. |
| `get_context` | `at?`, `container?`, `before?`, `after?`, `limit?` | Read the entries around one instant, oldest first. |
<!-- tools:end -->

## Reading the answers

- **Every tool caps its answer.** 100 entries by default, 1000 at most, a
  message truncated at 8 KiB, and a 512 KiB response budget. A response that
  hits the budget carries `"truncated": true` — narrow the window or the filter
  rather than paging.
- **`get_log_health` first when a search is empty.** `status` is `ok`, `stale`
  or `empty`. An empty window with a stale newest entry means the pipeline
  stopped (vector, or the store), not that the service was quiet; the stack's
  monitor fails on the same condition.
- **Retention is finite.** 14 days / 10 GiB by default. An empty answer for an
  old window may mean the entries were deleted, not that nothing happened.
- **`error_summary` counts bursts, not lines.** journald writes one entry per
  line, so a traceback is many "errors". Each group reports `minutes` (one-minute
  buckets with at least one error -- the incident-shaped number), `entries` (raw
  line volume) and `peak` (the busiest minute); `window_minutes` is the window's
  length, so `minutes: 360` over `since=6h` means every minute, i.e. background
  noise rather than thirty incidents.
- **Names are exact.** `bitcoind` and `bitcoin-node-mcp` are different sources,
  and a container name that does not exist returns an empty search rather than
  an error. `list_field_values field=container` is how you check a name.
- **Failures are tool errors.** An unreachable store or a LogsQL parse error
  comes back as `isError: true` with the store's own message. Nothing matched is
  a successful, empty answer — do not conflate the two.

## Common questions

| Question | Call |
| --- | --- |
| Is anything still arriving? | `get_log_health` |
| What is happening right now? | `tail_logs since=5m` |
| Who is spamming the journal? | `top_sources since=1h` |
| What is erroring? | `error_summary since=6h` |
| What are the container names? | `list_field_values field=container since=24h` |
| Why did lightningd restart? | `search_logs query='container:"lightningd"' since=6h` |
| What happened around 03:10? | `get_context at=2026-11-02T03:10:00Z` |
| Did the monitor alert on this host? | `search_logs query='unit:"monitor.service"' since=24h` |
| Did a deploy break something? | `get_context at=<deploy time> before=300 after=300` |
