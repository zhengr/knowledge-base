import asyncio, json
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
            print("RAW content blocks:", len(res.content))
            for i, c in enumerate(res.content):
                if hasattr(c, "text"):
                    print("block[%d] type=%s" % (i, type(c.text)))
                    print("block[%d] raw=%s" % (i, c.text[:500]))

asyncio.run(main())
