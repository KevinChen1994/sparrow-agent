from __future__ import annotations

from dataclasses import dataclass

from sparrow_agent.tools.registry import ToolRegistry


@dataclass
class MCPServerSpec:
    name: str
    command: str


class MCPAdapter:
    """V1 placeholder for registering MCP-backed tools into the shared registry."""

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry
        self.servers: list[MCPServerSpec] = []

    def register_server(self, server: MCPServerSpec) -> None:
        self.servers.append(server)

    def list_servers(self) -> list[MCPServerSpec]:
        return list(self.servers)
