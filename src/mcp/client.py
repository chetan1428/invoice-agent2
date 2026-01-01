"""
MCP (Model Context Protocol) Client for routing abilities to COMMON/ATLAS servers
"""
import os
import logging
from typing import Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass
import httpx

logger = logging.getLogger(__name__)


class MCPServer(str, Enum):
    COMMON = "COMMON"  # Internal abilities, no external data needed
    ATLAS = "ATLAS"    # External system interactions (ERP, enrichment)


@dataclass
class MCPResponse:
    success: bool
    data: Dict[str, Any]
    server: MCPServer
    ability: str
    error: Optional[str] = None


class MCPClient:
    """
    MCP Client orchestrates ability execution across COMMON and ATLAS servers
    
    COMMON Server: Handles internal processing (validation, matching, normalization)
    ATLAS Server: Handles external integrations (ERP, enrichment services, notifications)
    """
    
    def __init__(self):
        self.common_url = os.getenv("COMMON_SERVER_URL", "http://localhost:8000/mcp/common")
        self.atlas_url = os.getenv("ATLAS_SERVER_URL", "http://localhost:8000/mcp/atlas")
        self.execution_log: list = []
    
    def _get_server_url(self, server: MCPServer) -> str:
        return self.common_url if server == MCPServer.COMMON else self.atlas_url
    
    async def execute_ability(
        self,
        server: MCPServer,
        ability: str,
        params: Dict[str, Any]
    ) -> MCPResponse:
        """
        Execute an ability on the specified MCP server
        
        For demo purposes, this simulates the MCP call locally.
        In production, this would make HTTP calls to actual MCP servers.
        """
        log_entry = {
            "server": server.value,
            "ability": ability,
            "params_keys": list(params.keys())
        }
        
        try:
            # Simulate MCP execution (in production, use httpx to call actual servers)
            result = await self._simulate_ability(server, ability, params)
            
            log_entry["success"] = True
            log_entry["result_keys"] = list(result.keys()) if result else []
            self.execution_log.append(log_entry)
            
            logger.info(f"MCP [{server.value}] executed '{ability}' successfully")
            
            return MCPResponse(
                success=True,
                data=result,
                server=server,
                ability=ability
            )
            
        except Exception as e:
            log_entry["success"] = False
            log_entry["error"] = str(e)
            self.execution_log.append(log_entry)
            
            logger.error(f"MCP [{server.value}] failed '{ability}': {e}")
            
            return MCPResponse(
                success=False,
                data={},
                server=server,
                ability=ability,
                error=str(e)
            )
    
    async def _simulate_ability(
        self, 
        server: MCPServer, 
        ability: str, 
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Simulate MCP ability execution for demo
        In production, replace with actual HTTP calls
        """
        from .abilities import CommonAbilities, AtlasAbilities
        
        if server == MCPServer.COMMON:
            return await CommonAbilities.execute(ability, params)
        else:
            return await AtlasAbilities.execute(ability, params)
    
    def get_execution_log(self) -> list:
        return self.execution_log
    
    def clear_log(self):
        self.execution_log = []


# Global instance
_mcp_client = None


def get_mcp_client() -> MCPClient:
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client
