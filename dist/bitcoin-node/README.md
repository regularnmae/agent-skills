# bitcoin-node

A skill for agents that already have a Bitcoin Core node and the
[bitcoin-node-mcp](https://github.com/regularnmae/bitcoin-node-mcp) server
configured. It teaches the agent when to reach for the node, how to read what
comes back, and which three mistakes waste time or context.

## What it gives you

- **Chain questions answered from your node**, not an explorer: height, sync
  progress, difficulty, disk usage, peers, mempool volume, fee estimates.
- **A transaction lookup that does not derail.** The `-5` reply, the `txindex`
  fallback, and why `verbosity=2` on a busy block is a multi-megabyte answer.
- **Honest limits.** No address history, no broadcasting, no wallet. The skill
  says so instead of approximating with the wrong call.

## Requirements

1. Bitcoin Core, synced (the skill will tell the agent when it is not).
2. The `bitcoin-node-mcp` server running beside it, read-only.
3. That server configured in your client, so its tools are available.

The skill adds no network access, no credentials and no scripts. It is
instructions only.

## Install

Copy the `bitcoin-node/` folder into your agent's skills directory:

| Agent | Directory |
| --- | --- |
| Claude Code | `~/.claude/skills/` |
| Codex CLI | `~/.codex/skills/` |
| OpenCode | `~/.config/opencode/skills/` |

Or install it through the marketplace. If `SKILL.md` is found, it works.

## Verify it loaded

Ask: *"How synced is my node, and what is the tip hash?"*

A working install calls `get_blockchain_info` and reports `blocks`, `headers`,
sync progress and `bestblockhash`. If it answers from memory instead, the skill
is not loaded, or the MCP server is not configured.

## When it activates

Chain state, blocks, transactions, mempool, fees, peers -- and specifically
questions where the right call depends on the node's configuration: "what block
is this tx in", "is this UTXO spent", "what fee should I pay", "is my node
connected".

It will not activate for wallet balances, address history, or anything that
needs signing -- the node cannot answer those.

## Notes

- Works on a full node or a pruned one; the skill handles both.
- Works with `txindex` on or off; the skill explains the difference.
- Amounts arrive in BTC and fees in BTC/kvB -- the skill tells the agent to
  convert before quoting.
