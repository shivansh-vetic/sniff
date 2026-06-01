from fastmcp.client.transports import NpxStdioTransport

MONGO_NPX_CACHE_DIR = "/tmp/mongodb-mcp-server-npx-cache-v2"


class NonInteractiveNpxStdioTransport(NpxStdioTransport):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.args = ["--yes", *self.args]


def mongo_child_env(mongo_url: str) -> dict[str, str]:
    return {
        "MDB_MCP_CONNECTION_STRING": mongo_url,
        "NPM_CONFIG_CACHE": MONGO_NPX_CACHE_DIR,
        "npm_config_cache": MONGO_NPX_CACHE_DIR,
        "NPM_CONFIG_OMIT": "optional",
        "npm_config_omit": "optional",
        "NPM_CONFIG_OPTIONAL": "false",
        "npm_config_optional": "false",
    }
