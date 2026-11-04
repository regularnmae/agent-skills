---
name: crowdsec
description: Read which decisions this host's CrowdSec engine is enforcing, whether one address is blocked right now, and whether detection is still alive -- through the read-only crowdsec-mcp server or the agent-mcp CLI. Use for "why is this client blocked", "what is being blocked", and "is the IDS doing anything"; it cannot ban or unban.
---

# CrowdSec

Read-only view of the engine's *decisions* -- the blocks `stack-bouncer` turns
into nftables entries -- plus the engine's own health counters. Nothing here
writes, deletes or changes anything, and the credential behind it could not: it
is a bouncer key.

```sh
agent-mcp crowdsec list_decisions
agent-mcp crowdsec list_decisions scenario=stack/http-probing limit=10
agent-mcp crowdsec check_ip ip=203.0.113.9
agent-mcp crowdsec get_engine_health
agent-mcp crowdsec --list
```

`agent-mcp` is on `PATH` after `install.sh`; otherwise it is
`~/.local/bin/agent-mcp`. A tool returns pretty-printed JSON.

**Native `crowdsec` tools are the fastest path when this harness has them.**
`agent-mcp` is the same server for harnesses without MCP; the notes below apply
either way.

<!-- tools:start -->
| Tool | Arguments | Does |
| --- | --- | --- |
| `list_decisions` | `ip?`, `scenario?`, `type?`, `scope?`, `origin?`, `limit?` | List the decisions CrowdSec is enforcing right now, newest first. |
| `check_ip` | `ip` | Answer whether one address is blocked right now, and why. |
| `get_engine_health` | — | Report what the engine is doing and whether it is still fed. |
<!-- tools:end -->

## What you are reading

A decision is one block:

```json
{
  "id": 61,
  "value": "203.0.113.9",
  "scope": "Ip",
  "type": "ban",
  "scenario": "stack/http-probing",
  "origin": "crowdsec",
  "duration": "1h57m13s"
}
```

The scenarios on this host are the stack's own (`deploy/crowdsec/scenarios/`):
`stack/http-probing` (a 404/403 sweep), `stack/http-authfail` (repeated failed
logins to the proxy hosts, BTCPay's login included) and `stack/http-flood`
(request rate). `origin: crowdsec` means this host's own logs; `cscli` means an
operator block added by hand.

## Reading the answers

- **Only active decisions exist here.** `duration` is what is left of the TTL,
  so the same decision shrinks between calls, and an expired ban is gone. Nothing
  here answers "why was that address blocked this morning" -- that is the
  engine's alert store (`podman exec crowdsec cscli alerts list` on the host) or
  the log store, not this server.
- **`check_ip`'s `enforceable` is the interesting field.** The host's bouncer
  refuses private space and every address the host itself holds, so a decision
  on `10.89.0.5` exists and is never applied. `enforceable: false` means "do not
  expect this to drop anything". It also refuses the operator's **own public
  address** (`STACK_WAN_IP` in the stack) -- every check that leaves that host
  comes back through the router with it as the source, so a ban there would cut
  the operator's own monitoring and agent traffic -- but this server cannot see
  that declaration: `enforceable` is computed from the address alone
  (`ipaddress.is_global`), so for that one address it answers `true` while the
  bouncer declines. Read it as "the address is routable", not "the host will
  enforce it".
- **`get_engine_health` is a snapshot, not a rate.** Counters are cumulative
  since the engine started; ask twice to see movement. `machines[*].heartbeat_age_seconds`
  is the one freshness signal: if it grows, the log processor has stopped even
  though the API answers.
- **`detection.parser_hits.ko` above zero** means access-log lines the parser
  could not read -- how a silent nginx log-format change shows up. Compare it
  against `ok`, not against zero alone.
- **`buckets_in_flight` is pre-decision.** A scenario that has counted hits but
  not crossed its threshold yet appears there, not in `list_decisions`.
- **Failures are tool errors.** An unreachable LAPI or a rejected key comes back
  as `isError: true` with the reason. A successful empty list means "nothing is
  blocked", and is not the same thing.

## What it cannot do

- **No alerts, no history.** Alerts need a machine credential, which may also
  create and delete decisions -- ban and unban -- so this server deliberately
  does not hold one. Use `cscli alerts list` on the host, or the log store, for
  "what happened".
- **No ban, no unban.** Enforcement is `stack-bouncer`'s job, and it refuses
  private space and the host's own addresses on purpose. If something needs
  blocking, that is an operator action on the host.
- **No bouncer list.** The LAPI has no such endpoint; enforcement freshness is
  `$DATA_DIR/audit/bouncer.status` (which the monitor pages on). Two fields there
  are worth knowing: `banned=` is what actually went into the nftables set, and
  `skipped=` is how many decisions enforcement declined because they name an
  address the host holds or its own public address — so `banned=0 skipped=1` is
  "a decision exists and is deliberately not applied", not a broken applier.

## Common questions

| Question | Call |
| --- | --- |
| What is blocked right now? | `list_decisions` |
| Is this client blocked? | `check_ip ip=<addr>` |
| Is anything hitting the auth endpoints? | `list_decisions scenario=stack/http-authfail` |
| Is detection still running? | `get_engine_health` (check `machines` age) |
| Is the parser still reading nginx? | `get_engine_health` (`detection.parser_hits.ko`) |
| Is this ban actually enforced? | `check_ip` → `enforceable` |
| Is anything about to tip over? | `get_engine_health` → `detection.buckets_in_flight` |
