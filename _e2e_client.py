import asyncio
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.session import ClientSession

async def main():
    url = "http://158.101.23.34:8000/mcp"
    async with streamablehttp_client(url) as (r, w, _):
        async with ClientSession(r, w) as sess:
            await sess.initialize()
            tools = await sess.list_tools()
            print("TOOLS:", [t.name for t in tools.tools])
            res = await sess.call_tool("search_kb", {"query": "MCP", "limit": 2})
            for c in res.content:
                if hasattr(c, "text"):
                    import json
                    data = json.loads(c.text)
                    print("search_kb('MCP') -> %d 条" % len(data))
                    for d in data[:2]:
                        print("  -", d["path"], "| score=", d.get("score"))

asyncio.run(main())
