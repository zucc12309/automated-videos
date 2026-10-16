# How MCP connects agents to your tools

MCP gives an agent a standard way to reach tools and data: host, client, server, JSON-RPC.

## Step by step

1. **One client per server** — The host app, like Claude Code, creates one MCP client for every server it connects to.
2. **Tools, resources, prompts** — Each server exposes three things: tools to call, resources to read, and prompts to reuse.
3. **It's just JSON-RPC** — Under the hood, every request is a JSON-RPC message: a method, parameters, and an ID.
4. **Two transports** — Local servers usually talk over standard input and output. Remote servers use streamable HTTP.
5. **Only trust servers you'd run** — One rule: only connect servers you trust, because their tools act with your permissions.

## Sources

1. **Model Context Protocol: architecture overview** — https://modelcontextprotocol.io/docs/learn/architecture

_Prepared from the video's verified source data. Review before sending._
