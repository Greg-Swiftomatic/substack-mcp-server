"""
Substack MCP Server - A Model Context Protocol server for Substack API.

This MCP server enables Claude and other AI assistants to interact with
Substack newsletters, posts, and user profiles through the Model Context Protocol.
"""

from typing import Any, Dict, List, Optional
import asyncio
from mcp.server.fastmcp import FastMCP
from substack_api import Newsletter, Post, User

# Initialize FastMCP server
mcp = FastMCP("substack")

# Helper functions for async operations
async def run_sync(func, *args, **kwargs):
    """Run a synchronous function in a thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

@mcp.tool()
async def get_newsletter_posts(newsletter_url: str, limit: int = 5, sorting: str = "new") -> str:
    """
    Get recent posts from a Substack newsletter.
    
    Args:
        newsletter_url: URL of the Substack newsletter (e.g., https://example.substack.com)
        limit: Maximum number of posts to retrieve (default: 5)
        sorting: How to sort posts, either "new" or "top" (default: "new")
    """
    newsletter = Newsletter(newsletter_url)
    posts = await run_sync(newsletter.get_posts, sorting=sorting, limit=limit)
    
    if not posts:
        return "No posts found for this newsletter."
    
    result = f"Posts from {newsletter_url}:\n\n"
    for i, post in enumerate(posts, 1):
        metadata = await run_sync(post.get_metadata)
        title = metadata.get("title", "Untitled")
        publish_date = metadata.get("publication_date", "Unknown date")
        result += f"{i}. {title} - {publish_date}\n   URL: {post.url}\n\n"
    
    return result

@mcp.tool()
async def get_post_content(post_url: str) -> str:
    """
    Get the content of a Substack post.
    
    Args:
        post_url: URL of the Substack post (e.g., https://example.substack.com/p/post-slug)
    """
    post = Post(post_url)
    metadata = await run_sync(post.get_metadata)
    content = await run_sync(post.get_content)
    
    if not content:
        return f"Could not retrieve content for post: {post_url}"
    
    title = metadata.get("title", "Untitled")
    author = metadata.get("author", {}).get("name", "Unknown author")
    publish_date = metadata.get("publication_date", "Unknown date")
    
    result = f"# {title}\n\n"
    result += f"By: {author}\n"
    result += f"Published: {publish_date}\n\n"
    result += f"{content}"
    
    return result

@mcp.tool()
async def search_newsletter(newsletter_url: str, search_query: str, limit: int = 5) -> str:
    """
    Search for posts within a Substack newsletter.
    
    Args:
        newsletter_url: URL of the Substack newsletter
        search_query: The search term to look for
        limit: Maximum number of results to return (default: 5)
    """
    newsletter = Newsletter(newsletter_url)
    search_results = await run_sync(newsletter.search_posts, search_query, limit=limit)
    
    if not search_results:
        return f"No results found for '{search_query}' in {newsletter_url}"
    
    result = f"Search results for '{search_query}' in {newsletter_url}:\n\n"
    for i, post in enumerate(search_results, 1):
        metadata = await run_sync(post.get_metadata)
        title = metadata.get("title", "Untitled")
        publish_date = metadata.get("publication_date", "Unknown date")
        result += f"{i}. {title} - {publish_date}\n   URL: {post.url}\n\n"
    
    return result

@mcp.tool()
async def get_author_info(author_username: str) -> str:
    """
    Get information about a Substack author.
    
    Args:
        author_username: The username of the Substack author
    """
    user = User(author_username)
    profile_data = await run_sync(user.get_raw_data)
    
    if not profile_data:
        return f"Could not retrieve information for author: {author_username}"
    
    name = profile_data.get("name", "Unknown")
    bio = profile_data.get("bio", "No biography available")
    
    result = f"Author: {name}\n"
    result += f"Username: {author_username}\n"
    result += f"Bio: {bio}\n\n"
    
    # Get subscriptions
    subscriptions = await run_sync(user.get_subscriptions)
    if subscriptions:
        result += "Subscriptions:\n"
        for sub in subscriptions[:10]:  # Limit to 10 subscriptions
            result += f"- {sub.get('name', 'Unknown')}\n"
    
    return result

@mcp.tool()
async def get_newsletter_recommendations(newsletter_url: str) -> str:
    """
    Get recommended newsletters for a Substack publication.
    
    Args:
        newsletter_url: URL of the Substack newsletter
    """
    newsletter = Newsletter(newsletter_url)
    recommendations = await run_sync(newsletter.get_recommendations)
    
    if not recommendations:
        return f"No recommendations found for {newsletter_url}"
    
    result = f"Recommended newsletters for {newsletter_url}:\n\n"
    for i, rec in enumerate(recommendations, 1):
        result += f"{i}. {rec.url}\n"
    
    return result

@mcp.tool()
async def get_newsletter_authors(newsletter_url: str) -> str:
    """
    Get authors of a Substack newsletter.
    
    Args:
        newsletter_url: URL of the Substack newsletter
    """
    newsletter = Newsletter(newsletter_url)
    authors = await run_sync(newsletter.get_authors)
    
    if not authors:
        return f"No authors found for {newsletter_url}"
    
    result = f"Authors of {newsletter_url}:\n\n"
    for i, author in enumerate(authors, 1):
        profile_data = await run_sync(author.get_raw_data)
        name = profile_data.get("name", "Unknown")
        result += f"{i}. {name} (@{author.id})\n"
    
    return result

@mcp.resource("post_content")
async def get_post_content_resource(post_url: str) -> str:
    """
    Get the content of a Substack post as a resource.
    
    Args:
        post_url: URL of the Substack post
    """
    post = Post(post_url)
    content = await run_sync(post.get_content)
    return content or "No content available"

@mcp.prompt("newsletter_summary")
def newsletter_summary_prompt() -> str:
    """Create a summary of a Substack newsletter."""
    return """
    I need to create a summary of the Substack newsletter at {newsletter_url}.
    Please gather the most recent posts, identify main themes, and create a concise summary.
    """

# Add the main execution block to run the server
if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
