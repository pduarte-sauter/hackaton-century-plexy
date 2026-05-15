import os
from typing import Optional

def get_api_key(api_key: Optional[str] = None) -> str:
    resolved_key = api_key or os.environ.get("AGENTOPS_API_KEY")
    if not resolved_key:
        raise ValueError(
            "API Key não encontrada. Passe api_key= ou defina a variável AGENTOPS_API_KEY."
        )
    return resolved_key

def get_endpoint(endpoint: Optional[str] = None) -> str:
    return endpoint or os.environ.get("AGENTOPS_ENDPOINT") or "http://localhost:4318"