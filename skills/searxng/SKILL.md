---
name: searxng
description: Search the web and read what it finds -- pages, PDFs, RSS feeds, archive snapshots, time zones -- through a self-hosted SearXNG MCP server or the agent-mcp CLI. Use to look a fact up and to fetch the source before stating it, or to read a page that changed or vanished.
---

# SearXNG

```sh
agent-mcp searxng search_web query="bitcoin core txindex backfill" max_results=5
agent-mcp searxng webfetch url=https://example.com/page
agent-mcp searxng fetch_pdf url=https://arxiv.org/pdf/2401.00001
agent-mcp searxng --list
```

**Native `searxng` tools are the fastest path when this harness has them.**
`agent-mcp` is the same server for harnesses without MCP; the notes below apply
either way.

## How to use it

- Chain `search_web` -> `webfetch`: a search returns snippets and URLs, and
  `webfetch` reads one of them as markdown. Search snippets alone are not a
  source -- fetch the page before stating a fact.
- Prefer `fetch_pdf` over `webfetch` for a PDF URL; `webfetch` returns raw
  bytes as text.
- `fetch_wayback url=...` finds the closest archived snapshot, for a page that
  is gone or has changed under you.
- `search_web` also takes `categories`, `engines`, `language`, `time_range` and
  `pageno`. Quote multi-word queries; use `--json` when quoting gets awkward:

```sh
agent-mcp searxng search_web --json '{"query":"cln listpays rpc", "max_results":3}'
```

- `get_time tz=...` and `convert_time value=... from_tz=... to_tz=...` for
  anything that hinges on a timestamp.

## Tools

<!-- tools:start -->
| Tool | Arguments | Does |
| --- | --- | --- |
| `search_web` | `query`, `max_results?`, `categories?`, `engines?`, `language?`, `time_range?`, `pageno?` | Search the web using self-hosted SearXNG (no API keys required). |
| `webfetch` | `url`, `max_chars?` | Fetch a web page and return its content as readable text/markdown. |
| `fetch_pdf` | `url`, `max_pages?`, `max_chars?` | Fetch a PDF and extract its text (e.g. an arxiv paper). |
| `fetch_rss` | `url`, `max_items?` | Fetch an RSS/Atom feed and list recent items. |
| `fetch_wayback` | `url` | Look up the closest web-archive snapshot of a URL. |
| `get_time` | `tz?` | Return the current time in a timezone. |
| `convert_time` | `value`, `from_tz?`, `to_tz?` | Convert a datetime string from one timezone to another. |
<!-- tools:end -->
