"""
Substack MCP Server - A Model Context Protocol server for Substack API.

This MCP server enables Claude and other AI assistants to interact with
Substack newsletters, posts, and user profiles through the Model Context Protocol.
"""

from typing import Any, Dict, List, Optional
import asyncio
import json
import os
import requests
import time
from mcp.server.fastmcp import FastMCP
from substack_api import Newsletter, Post, User

# Initialize FastMCP server
mcp = FastMCP("substack")

# Helper functions for async operations
async def run_sync(func, *args, **kwargs):
    """Run a synchronous function in a thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

# ===== Popular Substack newsletters for cross-search =====
POPULAR_NEWSLETTERS = [
    "https://stratechery.com",
    "https://www.platformer.news",
    "https://www.slowboring.com",
    "https://www.leandrorestrepo.com",
    "https://www.theverge.com",
    "https://tedgioia.substack.com",
    "https://sinocism.com",
    "https://noahpinion.substack.com",
    "https://astralcodexten.substack.com",
    "https://newsletter.pragmaticengineer.com"
]

# Function to load cached newsletters
def load_newsletter_cache():
    cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "newsletter_cache.json")
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r") as f:
                return json.load(f)
        except:
            return []
    return []

# Function to save newsletters to cache
def save_newsletter_cache(newsletters):
    cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "newsletter_cache.json")
    with open(cache_file, "w") as f:
        json.dump(newsletters, f)

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
async def search_across_substacks(search_query: str, newsletters: Optional[List[str]] = None, max_newsletters: int = 5, results_per_newsletter: int = 3, popular_only: bool = False) -> str:
    """
    Search for a topic across multiple Substack newsletters.
    
    Args:
        search_query: The search term to look for
        newsletters: Optional list of newsletter URLs to search (e.g., ["https://stratechery.com", "https://www.platformer.news"])
        max_newsletters: Maximum number of newsletters to search if not specified (default: 5)
        results_per_newsletter: Maximum number of results to return per newsletter (default: 3)
        popular_only: If True, only search popular pre-defined newsletters (default: False)
    """
    # Determine which newsletters to search
    if newsletters:
        search_newsletters = newsletters[:max_newsletters]  # Limit to max_newsletters
    elif popular_only:
        search_newsletters = POPULAR_NEWSLETTERS[:max_newsletters]  # Use popular newsletters
    else:
        # Try to load cached newsletters, fall back to popular ones if none available
        cached_newsletters = load_newsletter_cache()
        if cached_newsletters:
            search_newsletters = cached_newsletters[:max_newsletters]
        else:
            search_newsletters = POPULAR_NEWSLETTERS[:max_newsletters]
    
    results = []
    
    # Search each newsletter concurrently
    tasks = []
    for newsletter_url in search_newsletters:
        tasks.append(search_single_newsletter(newsletter_url, search_query, results_per_newsletter))
    
    # Wait for all searches to complete
    newsletter_results = await asyncio.gather(*tasks)
    
    # Compile the results
    combined_results = []
    for newsletter_url, posts in zip(search_newsletters, newsletter_results):
        if posts:
            combined_results.append((newsletter_url, posts))
    
    if not combined_results:
        return f"No results found for '{search_query}' across the specified Substack newsletters."
    
    # Format the output
    result = f"Search results for '{search_query}' across {len(combined_results)} Substack newsletters:\n\n"
    
    for newsletter_url, posts in combined_results:
        result += f"## {newsletter_url}\n\n"
        for i, (title, publish_date, post_url) in enumerate(posts, 1):
            result += f"{i}. {title} - {publish_date}\n   URL: {post_url}\n\n"
    
    return result

async def search_single_newsletter(newsletter_url: str, search_query: str, limit: int) -> List[tuple]:
    """Helper function to search a single newsletter."""
    try:
        newsletter = Newsletter(newsletter_url)
        search_results = await run_sync(newsletter.search_posts, search_query, limit=limit)
        
        if not search_results:
            return []
        
        results = []
        for post in search_results:
            metadata = await run_sync(post.get_metadata)
            title = metadata.get("title", "Untitled")
            publish_date = metadata.get("publication_date", "Unknown date")
            results.append((title, publish_date, post.url))
        
        return results
    except Exception as e:
        print(f"Error searching {newsletter_url}: {str(e)}")
        return []

@mcp.tool()
async def discover_popular_substacks(category: Optional[str] = None, limit: int = 10) -> str:
    """
    Discover popular Substack newsletters, optionally filtered by category.
    
    Args:
        category: Optional category to filter by (e.g., "technology", "politics", "science")
        limit: Maximum number of newsletters to return (default: 10)
    """
    # This is a simplified version - in a production environment, 
    # you would want to implement a more sophisticated discovery mechanism
    
    # Sample categories and associated newsletters
    categories = {
        "technology": [
            "https://stratechery.com",
            "https://www.platformer.news",
            "https://newsletter.pragmaticengineer.com",
            "https://www.theverge.com",
            "https://simonwillison.net"
        ],
        "politics": [
            "https://www.slowboring.com",
            "https://sinocism.com",
            "https://taibbi.substack.com",
            "https://greenwald.substack.com",
            "https://theweek.com"
        ],
        "science": [
            "https://astralcodexten.substack.com",
            "https://sciencebasedmedicine.substack.com",
            "https://davidrozado.substack.com",
            "https://rootsofprogress.org",
            "https://www.experimental-history.com"
        ],
        "culture": [
            "https://tedgioia.substack.com",
            "https://www.persuasion.community",
            "https://erikhoel.substack.com",
            "https://freddiedeboer.substack.com",
            "https://www.readingsupremacy.com"
        ],
        "economics": [
            "https://noahpinion.substack.com",
            "https://www.leandrorestrepo.com",
            "https://www.fullstackeconomics.com",
            "https://www.theovershoot.co",
            "https://www.readtpa.com"
        ]
    }
    
    if category and category.lower() in categories:
        newsletters = categories[category.lower()][:limit]
        result = f"Popular {category} newsletters on Substack:\n\n"
    else:
        # If no category specified or invalid category, return a mix
        all_newsletters = []
        for cat_newsletters in categories.values():
            all_newsletters.extend(cat_newsletters)
        
        # De-duplicate and limit
        unique_newsletters = list(dict.fromkeys(all_newsletters))
        newsletters = unique_newsletters[:limit]
        
        if category:
            result = f"No newsletters found for category '{category}'. Here are some popular newsletters instead:\n\n"
        else:
            result = "Popular newsletters on Substack:\n\n"
    
    # Update the cache with these newsletters
    save_newsletter_cache(newsletters)
    
    # Format the output
    for i, newsletter_url in enumerate(newsletters, 1):
        result += f"{i}. {newsletter_url}\n"
    
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

@mcp.prompt("cross_substack_research")
def cross_substack_research_prompt() -> str:
    """Research a topic across multiple Substack newsletters."""
    return """
    I need to research {topic} across multiple Substack newsletters.
    Please search for this topic across popular Substacks and summarize the key perspectives and insights.
    """

# Add the main execution block to run the server
if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
