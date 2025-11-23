"""
index.py
Core agent setup and tools for the AI Agent Chat application.

This module defines the conversational agent, its system prompt (instructions),
and a small set of utility tools exposed to the agent. It also includes a helper
to fetch documentation from a Context7 MCP server.

Notes:
- Keep the `system_prompt` instructions strict about the CARD_ACTION tag format
    because the UI parses agent output for those tags to update product cards.
- Tool functions are registered with the `@agent.tool_plain` decorator and
    should be side-effect free when possible.
"""

from pydantic_ai import Agent
import asyncio
import logfire
from dotenv import load_dotenv
import time
import os
import requests
import json

load_dotenv(override=True)
logfire.configure()
logfire.instrument_pydantic_ai()

model = "google-gla:gemini-2.5-flash"

# System prompt: Primary instructions for the conversational agent.
# This prompt guides the agent's behavior and enforces the exact CARD_ACTION
# tag format that the UI expects when adding/removing product cards.
system_prompt = """You are a helpful AI assistant with product card management capabilities. 

## Product Card Management
You can help users manage product cards. Product cards have a title, a color, and a quantity.

### CRITICAL: When users want to add, increase, or manage cards, respond with this exact format:

**For adding or increasing cards:**
[CARD_ACTION:ADD|TITLE:product_name|QUANTITY:number]
I've added/increased the [Product Name] card!

**For removing or decreasing cards:**
[CARD_ACTION:REMOVE|TITLE:product_name|QUANTITY:number]
I've removed/decreased the [Product Name] card!

**For removing ALL cards of a type:**
[CARD_ACTION:REMOVE|TITLE:product_name|QUANTITY:ALL]
I've removed all [Product Name] cards!

### Examples:
- User: "add banana" → Response: "[CARD_ACTION:ADD|TITLE:Banana|QUANTITY:1]\nI've added the Banana card!"
- User: "add 5 apples" → Response: "[CARD_ACTION:ADD|TITLE:Apple|QUANTITY:5]\nI've added 5 Apple cards!"
- User: "increase mango by 3" → Response: "[CARD_ACTION:ADD|TITLE:Mango|QUANTITY:3]\nI've increased the Mango card quantity by 3!"
- User: "remove banana" → Response: "[CARD_ACTION:REMOVE|TITLE:Banana|QUANTITY:1]\nI've removed 1 Banana card!"
- User: "delete 2 oranges" → Response: "[CARD_ACTION:REMOVE|TITLE:Orange|QUANTITY:2]\nI've removed 2 Orange cards!"
- User: "remove all bananas" → Response: "[CARD_ACTION:REMOVE|TITLE:Banana|QUANTITY:ALL]\nI've removed all Banana cards!"
- User: "clear all apples from cart" → Response: "[CARD_ACTION:REMOVE|TITLE:Apple|QUANTITY:ALL]\nI've removed all Apple cards!"

### Important:
- Always include the [CARD_ACTION:...] tag on the first line
- Extract the product name intelligently from natural language
- Default QUANTITY to 1 if not specified
- Use Title Case for product names (e.g., "Banana", "Apple Pie", "Green Tea")
- Be friendly and conversational after the tag

### For non-card questions:
- Answer normally using your knowledge or available tools
- Be helpful, concise, and professional
- If you need information, use the search tools available to you
"""

# Instantiate the agent with the model and system prompt. Additional tools
# will be registered via the `@agent.tool_plain` decorator below.
agent = Agent(model, system_prompt=system_prompt, tools=[])

@agent.tool_plain
def multiply(a: int, b: int) -> int:
    """Multiply two integers."""
    return a * b

time.sleep(1)

@agent.tool_plain
def time(timezone: str) -> str:
    """
    Get the current time in a given timezone.
    
    Args:
        timezone: The timezone name (e.g., 'America/New_York', 'Europe/London', 'Asia/Kolkata').
                 For Indian cities, use 'Asia/Kolkata' (covers all of India including Hyderabad, Mumbai, Delhi, etc.)
    
    Returns:
        Current time in the specified timezone, or an error message with suggestions.
    """
    import pytz
    from datetime import datetime
    
    # Common timezone mappings for cities
    timezone_mappings = {
        'hyderabad': 'Asia/Kolkata',
        'mumbai': 'Asia/Kolkata',
        'delhi': 'Asia/Kolkata',
        'bangalore': 'Asia/Kolkata',
        'chennai': 'Asia/Kolkata',
        'kolkata': 'Asia/Kolkata',
        'india': 'Asia/Kolkata',
        'new york': 'America/New_York',
        'los angeles': 'America/Los_Angeles',
        'london': 'Europe/London',
        'paris': 'Europe/Paris',
        'tokyo': 'Asia/Tokyo',
        'sydney': 'Australia/Sydney',
        'dubai': 'Asia/Dubai',
        'singapore': 'Asia/Singapore',
        'hong kong': 'Asia/Hong_Kong',
    }
    
    # Normalize input
    tz_lower = timezone.lower().strip()
    
    # Check if we have a mapping
    if tz_lower in timezone_mappings:
        timezone = timezone_mappings[tz_lower]
    
    try:
        tz = pytz.timezone(timezone)
        current_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S %Z")
        return f"Current time in {timezone}: {current_time}"
    except pytz.exceptions.UnknownTimeZoneError:
        # Provide helpful suggestions
        common_timezones = [
            "America/New_York",
            "America/Los_Angeles",
            "America/Chicago",
            "Europe/London",
            "Europe/Paris",
            "Asia/Kolkata (India)",
            "Asia/Tokyo",
            "Asia/Dubai",
            "Asia/Singapore",
            "Australia/Sydney"
        ]
        return f"Unknown timezone '{timezone}'. Common timezones include: {', '.join(common_timezones)}. For Indian cities, use 'Asia/Kolkata'."

@agent.tool_plain
def list_directory(path: str) -> str:
    """List files in a directory."""
    import os
    try:
        items =  os.listdir(path)
        return "/n".join(sorted(items))
    except Exception as e:
        return str(e)

@agent.tool_plain
def read_file(file_path: str) -> str:
    """Read the contents of a file."""
    try:
        with open(file_path, 'r') as file:
            return file.read()
    except Exception as e:
        return str(e)
    
@agent.tool_plain
def write_file(file_path: str, content: str) -> str:
    """Write content to a file."""
    try:
        with open(file_path, 'w') as file:
            file.write(content)
        return f"Content written to {file_path}"
    except Exception as e:
        return str(e)
    
@agent.tool_plain
def replace_in_file(file_path: str, old_string: str, new_string: str) -> str:
    """Replace a string in a file with a new string."""
    try:
        with open(file_path, 'r') as file:
            content = file.read()
        updated_content = content.replace(old_string, new_string)
        with open(file_path, 'w') as file:
            file.write(updated_content)
        return f"Replaced '{old_string}' with '{new_string}' in {file_path}"
    except Exception as e:
        return str(e)

@agent.tool_plain
def search_wikipedia(query: str) -> str:
    """
    Search Wikipedia for information about a topic.
    Use this tool when you need factual information about people, places, concepts, or events.
    
    Args:
        query: The topic or term to search for on Wikipedia.
    
    Returns:
        A summary of the Wikipedia article or an error message.
    """
    try:
        # Wikipedia API endpoint
        url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + requests.utils.quote(query)
        
        headers = {
            "User-Agent": "AI-Agent/1.0 (Educational Purpose)"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("type") == "standard":
            title = data.get("title", "")
            extract = data.get("extract", "")
            url_link = data.get("content_urls", {}).get("desktop", {}).get("page", "")
            
            result = f"**{title}**\n\n{extract}\n\nRead more: {url_link}"
            return result
        else:
            return f"No Wikipedia article found for '{query}'. Try rephrasing your search."
            
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return f"No Wikipedia article found for '{query}'. The topic might not exist or is spelled differently."
        return f"Error accessing Wikipedia: {str(e)}"
    except Exception as e:
        return f"Error searching Wikipedia: {str(e)}"

@agent.tool_plain
def search_web(query: str) -> str:
    """
    Search the web using DuckDuckGo Instant Answer API for quick facts and information.
    Use this tool when you need current information, facts, or when Wikipedia doesn't have the answer.
    
    Args:
        query: The search query or question.
    
    Returns:
        Search results or relevant information.
    """
    try:
        # DuckDuckGo Instant Answer API (no API key required)
        url = "https://api.duckduckgo.com/"
        
        params = {
            "q": query,
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1
        }
        
        headers = {
            "User-Agent": "AI-Agent/1.0 (Educational Purpose)"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Try to extract relevant information
        result_parts = []
        
        # Abstract (main answer)
        if data.get("Abstract"):
            result_parts.append(f"**Answer:**\n{data['Abstract']}")
            if data.get("AbstractURL"):
                result_parts.append(f"Source: {data['AbstractURL']}")
        
        # Definition
        elif data.get("Definition"):
            result_parts.append(f"**Definition:**\n{data['Definition']}")
            if data.get("DefinitionURL"):
                result_parts.append(f"Source: {data['DefinitionURL']}")
        
        # Related topics
        elif data.get("RelatedTopics") and len(data["RelatedTopics"]) > 0:
            result_parts.append("**Related Information:**")
            for i, topic in enumerate(data["RelatedTopics"][:3], 1):
                if isinstance(topic, dict) and topic.get("Text"):
                    result_parts.append(f"{i}. {topic['Text']}")
                    if topic.get("FirstURL"):
                        result_parts.append(f"   {topic['FirstURL']}")
        
        if result_parts:
            return "\n\n".join(result_parts)
        else:
            return f"No direct answer found for '{query}'. You may need to search more specifically or try Wikipedia."
            
    except Exception as e:
        return f"Error searching the web: {str(e)}"

@agent.tool_plain
def context7_fetch_docs(query: str, doc_type: str = "general") -> str:
    """
    Fetch documentation from the Context7 MCP server using Model Context Protocol.
    
    Context7 is an MCP (Model Context Protocol) server that provides
    structured documentation and knowledge retrieval capabilities.
    
    Args:
        query: The search query or document identifier to fetch.
        doc_type: Type of documentation to fetch (general, api, tutorial, reference).
    
    Returns:
        Documentation content or error message.
    """
    # Read configuration from environment variables:
    # - CONTEXT7_API_KEY: optional Bearer token for the MCP server
    # - CONTEXT7_MCP_URL: base URL of the MCP server (defaults to localhost for local dev)
    api_key = os.getenv("CONTEXT7_API_KEY")

    # MCP server endpoint for Context7 (default to local development server)
    mcp_server_url = os.getenv("CONTEXT7_MCP_URL", "http://localhost:3000")
    
    # MCP protocol: tools/call request
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "fetch_documentation",
            "arguments": {
                "query": query,
                "doc_type": doc_type,
                "format": "markdown"
            }
        }
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    try:
        # Send MCP request to Context7 server
        response = requests.post(
            f"{mcp_server_url}/mcp/v1",
            json=mcp_request,
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Parse MCP response
        if "result" in data:
            result = data["result"]
            if isinstance(result, dict):
                content = result.get("content", [])
                if isinstance(content, list) and len(content) > 0:
                    # Extract text from MCP content blocks
                    return "\n".join([
                        block.get("text", str(block)) 
                        for block in content 
                        if isinstance(block, dict)
                    ])
                elif "text" in result:
                    return result["text"]
                else:
                    return json.dumps(result, indent=2)
            else:
                return str(result)
        elif "error" in data:
            error = data["error"]
            return f"MCP Error: {error.get('message', str(error))}"
        else:
            return f"Unexpected MCP response: {json.dumps(data, indent=2)}"
            
    except requests.exceptions.RequestException as e:
        return f"Error connecting to Context7 MCP server: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"
    

async def main():
    message_history = []  # Initialize empty message history

    while True:
        message = input("You: ")
        if message.lower() in ["exit", "quit", "bye"]:
            break

        # Pass the message history to maintain context
        response = await agent.run(message, message_history=message_history)
        print("Agent: ", response.output)

        # Update message history with new messages from this run
        message_history = response.all_messages()


if __name__ == "__main__":
    asyncio.run(main())