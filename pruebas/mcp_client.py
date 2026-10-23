"""Cliente MCP mínimo (Streamable HTTP) para probar los servidores MCP de la POC sin Copilot.

Uso:
  python mcp_client.py URL                         -> lista las tools
  python mcp_client.py URL TOOL 'JSON_ARGS'        -> invoca una tool
  python mcp_client.py URL TOOL 'JSON_ARGS' --header=x-correlation-id=mi-id

Ejemplo (adaptador MCP de la aerolínea, igual que lo invocaría Copilot):
  python mcp_client.py http://localhost:8081/aerolinea/mcp buscar_vuelos '{"origen":"Madrid","destino":"Londres","fecha":"2026-11-20","pasajeros":1}' "--header=X-API-Key=<tu API key>"
"""
import json, sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8")
url = sys.argv[1]
extra = {}
args = [a for a in sys.argv[2:]]
for a in list(args):
    if a.startswith('--header='):
        k, v = a[len('--header='):].split('=', 1); extra[k] = v; args.remove(a)
session = None
def rpc(method, params=None, notify=False, _id=[0]):
    global session
    body = {"jsonrpc": "2.0", "method": method}
    if params is not None: body["params"] = params
    if not notify: _id[0] += 1; body["id"] = _id[0]
    h = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream", **extra}
    if session: h["Mcp-Session-Id"] = session
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=h, method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        session = r.headers.get("Mcp-Session-Id") or session
        raw = r.read().decode("utf-8")
        if notify or not raw.strip(): return None
        if "text/event-stream" in (r.headers.get("Content-Type") or ""):
            datas = [l[5:].strip() for l in raw.splitlines() if l.startswith("data:")]
            msgs = [json.loads(d) for d in datas if d]
            return [m for m in msgs if m.get("id") == body.get("id")][-1]
        return json.loads(raw)
init = rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "poc-test", "version": "1"}})
print("SERVER:", json.dumps(init["result"]["serverInfo"]), "session:", session)
rpc("notifications/initialized", notify=True)
if not args:
    tools = rpc("tools/list", {})
    for t in tools["result"]["tools"]: print("TOOL:", t["name"], "-", t["description"][:90])
else:
    res = rpc("tools/call", {"name": args[0], "arguments": json.loads(args[1])})
    for item in res.get("result", {}).get("content", []):
        print("----", item.get("type"), "----")
        print(item.get("text"))
    if res.get("result", {}).get("isError") or "error" in res:
        print("ERROR:", json.dumps(res, ensure_ascii=False)[:2000])
