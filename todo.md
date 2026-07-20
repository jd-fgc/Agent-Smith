Flux avec le docker

Agent loop (host)
    ↓ envoie le code
Sandbox (host) → exec(code, namespace)
    ↓ le code appelle read_file("/testbed/...")
MCP Client (dans le namespace)
    ↓ appelle le MCP server via stdio
MCP Server swebench (host)
    ↓ fait docker exec <container_id> cat /testbed/...
    ↑ retourne le résultat
Sandbox
    ↑ retourne l'output au LLM