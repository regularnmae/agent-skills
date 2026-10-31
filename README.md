# agent-skills

Agent skills that put the crypto MCP servers of this stack behind a shell
command, so any agent can use them -- not just the harnesses that speak MCP.

Six skills: one per server -- `bitcoin-node`, `monero-node`, `monero-wallet`,
`lightning`, `searxng` -- plus `crypto-stack`, the playbooks that span them
(health, heights, fees, verifying a payment across layers). They are
**read-only by construction**: they call the same servers whose tool sets are
already read-only (and, for the wallet and lightning servers, capped and
`dry_run`-gated), and `refresh.py` refuses to publish a table that says
otherwise.

## Why this exists

The MCP servers stay exactly as they are. They are the safety layer: they hold
the RPC credentials, the read-only allowlist and the spending caps, and they
enforce those no matter which client is talking. This repo adds the thing a
skill is good at -- prose the model loads only when it needs it -- plus a small
stdlib client that speaks MCP over HTTP.

It buys two things:

- **It works in harnesses without MCP** (Codex, scripts, CI, a plain shell).
- **It costs no context when unused.** Five always-resident MCP servers are
  ~45 tool schemas in every request; the six skills are six descriptions until
  one is loaded.

It does **not** remove infrastructure: the servers, their gateway and their
tokens are still in the path. If a server is down, the skill is down.

## Install

```sh
./install.sh --from-opencode
```

Requires Python 3.9 or newer. That links every skill into each harness already
present (`~/.config/opencode`, `~/.codex`, `~/.claude`), puts `agent-mcp` in
`~/.local/bin`, and seeds `~/.config/agent-skills/env` from an existing opencode
config. Without
`--from-opencode` the env file is created empty for you to fill in.
`--from-opencode` resolves opencode's `{env:NAME}` references against the shell
instead of copying the placeholder, so a config that keeps its secrets in the
environment seeds real tokens.

A server resolved in this order: the environment (`AGENT_MCP_*`), then the file
named by its `token_file` in `servers.json`, then `~/.config/agent-skills/env`.
`token_file` outranks the env file on purpose -- it is how the stack's own
`token.env` is read, on every call, with no copy to go stale when a token is
rotated. On such a host `~/.config/agent-skills/env` can stay empty.

`url` is expanded like a shell string: `$VAR`, `${VAR}` and `${VAR:-default}`,
plus `~`. That is what keeps the endpoint list honest -- set one
`AGENT_MCP_BASE_URL` and every server moves with it. Three more optional
overrides: `AGENT_MCP_SERVERS` points at a different registry,
`AGENT_MCP_ENV` at a different token file, and `AGENT_MCP_TIMEOUT` sets the
call timeout in seconds (`--timeout` outranks it). Nothing secret is
committed here. The token env names are all prefixed `AGENT_MCP_` on purpose:
harnesses export the servers' own `*_MCP_TOKEN` variables into the shell, often
with tokens that no longer match the live config, and a skill must not pick
those up instead of its own source.

## Use

```sh
agent-mcp bitcoin-node get_blockchain_info
agent-mcp bitcoin-node get_block_hash height=973000
agent-mcp monero-wallet get_balance
agent-mcp lightning decode bolt11=<invoice>
agent-mcp searxng search_web query="core lightning listpays"
agent-mcp doctor
agent-mcp --servers
agent-mcp --list
```

Arguments are `key=value` and each value is parsed as JSON where it can be, so
`height=973000` is a number and `verbose=false` is a boolean. Quote to force a
string: `label="123"`. For anything awkward, `--json` takes the whole argument
object:

```sh
agent-mcp monero-node get_transactions --json '{"txids":["<id>"]}'
```

Exit status is 0 on success, 1 when the call or the tool failed (with the
server's message on stderr), 2 on a usage error. `doctor` is 1 when any server
it tried failed.

## Diagnosing a broken server

```sh
agent-mcp doctor            # every server
agent-mcp doctor lightning  # just one
```

`doctor` reports the endpoint, which of the three token sources would answer
(`env`, `token_file`, `env_file` or `none`) -- never the token itself -- and a
live `tools/list` with a tool count and latency:

```
bitcoin-node  ok    13 tools  118 ms  token: token_file
monero-node   FAIL  401 from https://mcp.boltmesh.net/monero: the bearer token is missing or wrong  token: none
```

`token: none` with a 401 means no source held a token at all, which is a
different problem from a token that is present and rejected. `--json` gives
the same rows for a script.

## Keeping the tables honest

Each skill's tool table is generated from the live `tools/list`, between the
`<!-- tools:start -->` and `<!-- tools:end -->` markers. After a server changes:

```sh
python3 refresh.py           # rewrite the tables
python3 refresh.py --check   # exit 1 if anything drifted (run it on the host)
```

Hand-editing a table is what makes skills lie six months later; don't.

`refresh.py` also stops -- without writing -- if a server starts advertising a
spending tool (`transfer`, `pay`, `keysend`, `sweep_all`, `withdraw`, `close`,
and friends). The skills say read-only in prose, so that is an operator
decision, not a table to regenerate.

## Tests

```sh
python3 -m unittest discover -s tests -t .
```

Stdlib only, no tokens and no network: `tests/fake_mcp.py` is a small MCP
server the client talks to over a loopback socket. CI runs this on Python 3.9
and 3.13 plus `ruff check`. `refresh.py --check` is not in CI on purpose -- it
needs the live gateway -- so run it on the host after a server change.

## Layout

```
bin/agent-mcp          the CLI the skills tell the model to run
lib/mcp_http.py        MCP streamable-HTTP client, stdlib only
lib/config.py          server registry + token lookup
servers.json           server name -> url, token env var, optional token file
skills/<name>/SKILL.md one per server, plus crypto-stack
refresh.py             regenerate the tool tables from tools/list
install.sh             link skills into harnesses, install the CLI
tests/                 unit tests against a fake MCP server
.github/workflows/     unittest + ruff on 3.9 and 3.13
```

## Distributing

`dist/` holds the same knowledge packaged for someone else: a self-contained
skill for a person who runs `bitcoin-node-mcp` against **their own** node. No
`agent-mcp`, no tokens, no paths or URLs from this stack — nothing that would
401 on a stranger's machine.

```
dist/bitcoin-node/     SKILL.md + references/tools.md + README.md
dist/package.sh        zips a package into <name>.zip
```

```sh
./dist/package.sh              # every package -> dist/<name>.zip
./dist/package.sh bitcoin-node # just one
```

The zip is the upload shape a marketplace expects: one top-level folder with
`SKILL.md` at its root, text files only, no symlinks, no dotfiles. Zips are
gitignored — regenerate them, don't commit them.

Keep the two directories distinct in your head:

| Directory | For | Contains |
| --- | --- | --- |
| `skills/` | this stack | `agent-mcp` calls, token files, our URLs |
| `dist/` | anyone else | their MCP server, their node, no credentials |

## Adding a server

1. Add an entry to `servers.json` with its `url` (expandable), its `token_env`
   name, and -- when the token lives in a file rather than the shell or the env
   file -- `token_file` and the `token_var` to read from it.
2. Add `skills/<same-name>/SKILL.md` with the `tools:start`/`tools:end` markers.
3. Run `python3 refresh.py`, then `./install.sh`.

`refresh.py` only rewrites skills that have a matching registry entry, so
`crypto-stack` (prose, no tool table) is left alone.

## Scope

Read-only. Nothing here moves funds. The wallet and lightning servers may grow
spending tools on the operator's side; if they do, `refresh.py` refuses to
write a table for them and names the tool, so the decision stays explicit. The
guardrail is still the server's caps -- not this repo.
