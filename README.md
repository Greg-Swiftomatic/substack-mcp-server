# Substack MCP Server

A Model Context Protocol (MCP) server that enables Claude and other AI assistants to interact with Substack newsletters, posts, and user profiles.

## Overview

This project converts the [Substack API library](https://github.com/NHagar/substack_api) into an Anthropic MCP server, allowing Claude to:

- Retrieve newsletter posts, podcasts, and recommendations
- Get user profile information and subscriptions
- Fetch post content and metadata
- Search for posts within newsletters

## Installation

### Prerequisites

- Python 3.10 or higher
- [Claude for Desktop](https://claude.ai/download) (for testing with Claude)

### Installation Steps

```bash
# Clone the repository
git clone https://github.com/Greg-Swiftomatic/substack-mcp-server.git
cd substack-mcp-server

# Set up virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

Alternatively, you can use `uv`:

```bash
# Using uv for faster installation
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

## Usage

### Running the Server

```bash
python substack_mcp.py
```

### Connecting to Claude for Desktop

1. Open your Claude for Desktop configuration file:
   - MacOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`

2. Add the server configuration:

```json
{
    "mcpServers": {
        "substack": {
            "command": "python",
            "args": [
                "/ABSOLUTE/PATH/TO/substack-mcp-server/substack_mcp.py"
            ]
        }
    }
}
```

3. Restart Claude for Desktop

### Using with Claude

Once configured, you can ask Claude questions like:

- "Show me recent posts from https://stratechery.com/"
- "What's the content of this post: https://stratechery.com/2023/the-ai-unbundling/"
- "Search for 'AI' on https://stratechery.com/"
- "Who are the authors of https://stratechery.com/?"

## Available Tools

This MCP server provides the following tools:

| Tool | Description |
|------|-------------|
| `get_newsletter_posts` | Retrieves recent posts from a Substack newsletter |
| `get_post_content` | Gets the full content of a specific Substack post |
| `search_newsletter` | Searches for posts within a newsletter |
| `get_author_info` | Retrieves information about a Substack author |
| `get_newsletter_recommendations` | Gets recommended newsletters for a publication |
| `get_newsletter_authors` | Lists authors of a Substack newsletter |

## Development

### Project Structure

```
substack-mcp-server/
├── README.md
├── LICENSE
├── requirements.txt
├── substack_mcp.py
└── examples/
    └── example_queries.md
```

### Adding New Tools

To add new tools to the MCP server, add a new function to `substack_mcp.py` with the `@mcp.tool()` decorator:

```python
@mcp.tool()
async def my_new_tool(param1: str, param2: int = 5) -> str:
    """
    Description of what the tool does.
    
    Args:
        param1: Description of param1
        param2: Description of param2 (default: 5)
    """
    # Tool implementation
    return "Result"
```

## Troubleshooting

If you encounter issues:

1. Check Claude's logs:
   ```bash
   # MacOS
   tail -n 20 -f ~/Library/Logs/Claude/mcp*.log
   
   # Windows
   type %APPDATA%\Claude\Logs\mcp*.log
   ```

2. Ensure your server runs without errors:
   ```bash
   python substack_mcp.py
   ```

3. Verify the configuration file paths in Claude for Desktop.

## Contributing

Contributions are welcome! Please feel free to submit a pull request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [NHagar/substack_api](https://github.com/NHagar/substack_api) - The original Substack API library
- [Model Context Protocol](https://modelcontextprotocol.io/) - Anthropic's MCP specification
