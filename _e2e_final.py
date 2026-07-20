import asyncio, json
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.session import ClientSession

async def main():
    url = "http://158.101.23.34:8000/mcp"
    async with streamablehttp_client(url) as (r, w, _):
        async with ClientSession(r, w) as sess:
            await sess.initialize()
            tools = await sess.list_tools()
            print("✅ 可用工具:", [t.name for t in tools.tools])
            res = await sess.call_tool("search_kb", {"query": "MCP", "limit": 3})
            results = []
            for c in res.content:
                if hasattr(c, "text"):
                    try: results.append(json.loads(c.text))
                    except: pass
            print("✅ search_kb('MCP') 命中 %d 条:" % len(results))
            for d in results:
                print("   - %s (score=%s, %s)" % (d.get("path"), d.get("score"), d.get("category")))

asyncio.run(main())
