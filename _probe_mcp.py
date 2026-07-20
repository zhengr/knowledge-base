import urllib.request as u, json
body = json.dumps({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"probe","version":"1.0"}}}).encode()
req = u.Request("http://knowledge-mcp:8000/mcp", data=body, headers={"Content-Type":"application/json","Accept":"application/json, text/event-stream"})
try:
    r = u.urlopen(req, timeout=8)
    print("MCP_OK status", r.status, "ct", r.headers.get("content-type"))
    print("resp", r.read().decode()[:300])
except Exception as e:
    print("MCP_ERR", repr(e))
