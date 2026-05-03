import os
from tavily import TavilyClient
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm


def search_web(query: str) -> dict:
    """Search the web for information about a topic.

    Args:
        query: The search query string.

    Returns:
        A dict with a 'results' list, each item containing 'title', 'url', and 'content'.
    """
    client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    response = client.search(query=query, max_results=5)
    return {
        "results": [
            {"title": r["title"], "url": r["url"], "content": r["content"]}
            for r in response["results"]
        ]
    }


def get_page_content(url: str) -> dict:
    """Fetch the full text content of a web page.

    Args:
        url: The URL of the page to fetch.

    Returns:
        A dict with 'content' (the page text) or 'error' (if fetching failed).
    """
    client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    response = client.extract(urls=[url])
    if response["results"]:
        return {"content": response["results"][0]["raw_content"]}
    return {"error": f"Could not fetch content from {url}"}


root_agent = LlmAgent(
    name="research_agent",
    model=LiteLlm(model="openai/gpt-4o"),
    instruction="""You are a thorough research assistant. When given a topic:

1. Use search_web to find information. Search 2-3 times with different queries to get broad coverage.
2. Use get_page_content on 1-2 of the most relevant URLs if you need more detail.
3. Synthesize everything into a structured response.

You MUST return your final response as a JSON object with exactly this structure:
{
  "topic": "the topic you researched",
  "summary": "2-3 sentence overview of the topic",
  "key_points": ["point 1", "point 2", "point 3", "point 4"],
  "sources": ["https://...", "https://..."]
}

Return only the JSON object — no markdown, no extra text.""",
    tools=[search_web, get_page_content],
)
