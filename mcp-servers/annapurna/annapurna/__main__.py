import anyio
import base64
import click
import hashlib
import httpx
import os
import secrets
import sys
import uvicorn
from httpx_oauth.oauth2 import OAuth2
from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Mount, Route


ANNAPURNA = 'annapurna'
QUERY = 'query'

RSC_HOST = os.environ.get('ANNAPURNA_ENDPOINT', '')
RETRIEVER_ID = os.environ.get('ANNAPURNA_RETRIEVER_ID', '')
CLIENT_ID = os.environ.get('ANNAPURNA_CLIENT_ID', '')
CLIENT_SECRET = os.environ.get('ANNAPURNA_CLIENT_SECRET', '')
AUTHRORIZE_ENDPOINT = f'{RSC_HOST}/oauth_authorize'
TOKEN_ENDPOINT = f'{RSC_HOST}/api/oauth/token'
SCOPE = ['annapurna', 'offline_access']
REDIRECT_URL = 'http://localhost:3000'
CLIENT_SECRET_POST = "client_secret_post"

def generate_code_verifier(length=128):
    return secrets.token_urlsafe(length)

def generate_code_challenge(verifier):
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip('=')


@click.command()
@click.option('--port', default=8000, help='Port to listen on')
@click.option('--host', default="0.0.0.0", help='IP address to listen on')
def main(port: int, host: str) -> int:
    """
    A simple MCP server exposing a tool querying Annapurna.
    """
    app = Server(ANNAPURNA)
    oauth2_client = OAuth2(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        authorize_endpoint=AUTHRORIZE_ENDPOINT,
        access_token_endpoint=TOKEN_ENDPOINT,
        refresh_token_endpoint=TOKEN_ENDPOINT,
        token_endpoint_auth_method=CLIENT_SECRET_POST,
    )
    verifier = generate_code_verifier()
    challenge = generate_code_challenge(verifier)
    state = secrets.token_urlsafe(16)

    async def get_authz_url():
        return await oauth2_client.get_authorization_url(
            REDIRECT_URL,
            scope=SCOPE,
            code_challenge=challenge,
            code_challenge_method="S256",
            state=state,
        )
    
    authorization_url = anyio.run(get_authz_url)
    print(f'Please visit {authorization_url} to authorize the application.'
          'and get the authorization code.')
    authorization_code = input('Enter the authorization code: ')
    async def get_access_token():
        return await oauth2_client.get_access_token(
            authorization_code,
            code_verifier=verifier,
            redirect_uri=REDIRECT_URL,
        )
    tokenresult = anyio.run(get_access_token)
    access_token = tokenresult['access_token']
    refresh_token = tokenresult['refresh_token']

    @app.call_tool()
    async def retrieve_tool(
        name: str,
        arguments: dict,
    ) -> list[types.TextContent]:
        if name != ANNAPURNA:
            raise ValueError(f'Unknown tool: {name}')
        
        if QUERY not in arguments:
            raise ValueError(f'Argument {QUERY} is required')
        
        query = arguments[QUERY]
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }
        url = f'{RSC_HOST}/api/annapurna/{RETRIEVER_ID}/retrieve'
        async with httpx.AsyncClient(follow_redirects=True, headers=headers) as client:
            response = await client.post(url, json={"query": query})
            # TODO: if response.status_code == 401, refresh the token and retry
            response.raise_for_status()
            return [types.TextContent(type="text", text=response.text)]
        
    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name=ANNAPURNA,
                description="Returns a list of chunks providing more context for a given query",
                inputSchema={
                    "type": "object",
                    "required": [QUERY],
                    "properties": {
                        QUERY: {
                            "type": "string",
                            "description": "query to retrieve context for, pass the whole question",
                        }
                    }
                }
            ),
        ]
    
    sse = SseServerTransport("/messages/")

    async def handle_sse(request):
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await app.run(
                streams[0], streams[1], app.create_initialization_options()
            )

    starlette_app = Starlette(
        debug=True,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )

    uvicorn.run(starlette_app, host=host, port=port)
    return 0


sys.exit(main())
