import json
import requests

from . import _api_key, _endpoint

class Retriever():
    def __init__(self, retriever_id):
        self.retriever_id = retriever_id

    def retrieve(self, query):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + _api_key
        }

        # Use the REST API endpoint
        endpoint = f'/api/annapurna/{self.retriever_id}/retrieve'
        full_url = _endpoint.rstrip('/') + endpoint

        # Prepare the request body
        body = {"query": query}

        response = requests.post(full_url, json=body, headers=headers)
        response.raise_for_status()  # This will raise an exception for HTTP errors
        return response.json()
        
