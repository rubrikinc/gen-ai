# Annapurna MCP server

This is a simple MCP server exposing a tool querying Annapurna.
Before running, you first need to register OAuth2 application from RSC
where you can get the client ID and client secret.

It requires to set the following environment variables:
- `ANNAPURNA_ENDPOINT`: RSC host
- `ANNAPURNA_CLIENT_ID`: the client ID
- `ANNAPURNA_CLIENT_SECRET`: the client secret
- `ANNAPURNA_RETRIEVER_ID`: the Annapurna retriever ID

with this, you can run it like
```
uv run annapurna --port [portnumber]
```