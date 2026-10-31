# agent-skills

Agent skills that put the crypto MCP servers of this stack behind a shell
command, so any agent can use them -- not just the harnesses that speak MCP.

Five skills, one per server: `bitcoin-node`, `monero-node`, `monero-wallet`,
`lightning`, `searxng`. They are **read-only by construction**, because they
call the same servers whose tool sets are already read-only (and, for the
wallet and lightning servers, capped and `dry_run`-gated).

## Why this exists

The MCP servers stay exactly as they are. They are the safety layer: they hold
the RPC credentials, the read-only allowlist and the spending caps, and they
enforce those no matter which client is talking. This repo adds the thing a
skill is good at -- prose the model loads only when it needs it -- plus a
90-line stdlib client that speaks MCP over HTTP.

It buys two things:

- **It works in harnesses without MCP** (Codex, scripts, CI, a plain shell).
- **It costs no context when unused.** Five always-resident MCP servers are
  ~45 tool schemas in every request; five skills are five descriptions until
  one is loaded.

It does **not** remove infrastructure: the servers, their gateway and their
tokens are still in the path. If a server is down, the skill is down.

## Install

```sh
./install.sh --from-opencode
```

That links every skill into each harness already present (`~/.config/opencode`,
`~/.codex`, `~/.claude`), puts `agent-mcp` in `~/.local/bin`, and seeds
`~/.config/agent-skills/env` from an existing opencode config. Without
`--from-opencode` the env file is created empty for you to fill in.

Tokens live in `~/.config/agent-skills/env` (mode 600) or in the environment
under the names in `servers.json`; nothing secret is committed here. Those names
are all prefixed `AGENT_MCP_` on purpose: harnesses export the servers' own
`*_MCP_TOKEN` variables into the shell, often with tokens that no longer match
the live config, and a skill must not pick those up instead of its own file.

## Use

```sh
agent-mcp bitcoin-node get_blockchain_info
agent-mcp bitcoin-node get_block_hash height=973000
agent-mcp monero-wallet get_balance
agent-mcp lightning decode bolt11=<invoice>
agent-mcp searxng search_web query="core lightning listpays"
agent-mcp bitcoin-node --list
```

Arguments are `key=value` and each value is parsed as JSON where it can be, so
`height=973000` is a number and `verbose=false` is a boolean. Quote to force a
string: `label="123"`. For anything awkward, `--json` takes the whole argument
object:

```sh
agent-mcp monero-node get_transactions --json '{"txids":["<id>"]}'
```

Exit status is 0 on success, 1 when the call or the tool failed (with the
server's message on stderr), 2 on a usage error.

## Keeping the tables honest

Each skill's tool table is generated from the live `tools/list`, between the
`<!-- tools:start -->` and `<!-- tools:end -->` markers. After a server changes:

```sh
python3 refresh.py           # rewrite the tables
python3 refresh.py --check   # exit 1 if anything drifted (what CI should run)
```

Hand-editing a table is what makes skills lie six months later; don't.

## Layout

```
bin/agent-mcp          the CLI the skills tell the model to run
lib/mcp_http.py        MCP streamable-HTTP client, stdlib only
lib/config.py          server registry + token lookup
servers.json           server name -> url + token env var (keys match skills/)
skills/<name>/SKILL.md one per server
refresh.py             regenerate the tool tables from tools/list
install.sh             link skills into harnesses, install the CLI
```

## Adding a server

1. Add an entry to `servers.json` with its URL and token env var.
2. Add `skills/<same-name>/SKILL.md` with the `tools:start`/`tools:end` markers.
3. Run `python3 refresh.py`, then `./install.sh`.

## Scope

Read-only. Nothing here moves funds. The wallet and lightning servers may grow
spending tools on the operator's side; if they do, those become reachable
through this CLI too, so the guardrail is the server's caps -- not this repo.
