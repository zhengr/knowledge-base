import requests
try:
    r = requests.get("http://knowledge-mcp:8000/sse",
                     headers={"Accept": "text/event-stream"},
                     timeout=6, stream=True)
    print("SSE status:", r.status_code, "| content-type:", r.headers.get("content-type"))
    # 读一行事件流确认是 SSE
    for i, line in enumerate(r.iter_lines()):
        if line:
            print("SSE line:", line[:120])
            if i >= 1:
                break
except Exception as e:
    print("ERROR:", repr(e))
