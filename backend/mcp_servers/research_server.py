import json
from mcp.server.mcpserver import MCPServer
from services.research_service import ResearchService

research_mcp = MCPServer("TerraPulse Research Server")
_research_service = ResearchService()


@research_mcp.tool()
def search_scientific_publications(query: str, limit: int = 5) -> str:
    """
    Search real peer-reviewed scientific publications and authoritative scholarly metadata via Crossref.
    Returns real DOIs, titles, authors, journals, and publication years.
    Never fabricates papers or citations.
    """
    try:
        results = _research_service.search_publications(query=query, limit=limit)
        return json.dumps(results.model_dump(), default=str)
    except Exception as e:
        return json.dumps({"error": f"Failed to search publications: {str(e)}"})


@research_mcp.tool()
def verify_doi_metadata(doi: str) -> str:
    """
    Verify whether a DOI exists in authoritative scholarly databases and retrieve its verified metadata.
    Returns null/error if the DOI does not genuinely exist.
    """
    try:
        paper = _research_service.verify_doi(doi)
        if not paper:
            return json.dumps({"verified": False, "message": f"DOI '{doi}' could not be verified in Crossref registry."})
        return json.dumps({"verified": True, "paper": paper.model_dump()}, default=str)
    except Exception as e:
        return json.dumps({"error": f"Failed to verify DOI: {str(e)}"})


@research_mcp.tool()
def search_wikipedia(query: str, limit: int = 3) -> str:
    """
    Search authentic environmental and geographical encyclopedia articles on Wikipedia.
    Returns article titles, real summaries, and source URLs.
    """
    try:
        articles = _research_service.search_wikipedia(query=query, limit=limit)
        return json.dumps(articles, default=str)
    except Exception as e:
        return json.dumps({"error": f"Failed to search Wikipedia: {str(e)}"})


@research_mcp.tool()
def get_wikipedia_summary(title: str) -> str:
    """
    Retrieve authentic article summary, overview extract, and URL from Wikipedia REST API.
    """
    try:
        summary = _research_service.get_wikipedia_summary(title=title)
        if not summary:
            return json.dumps({"found": False, "message": f"Article '{title}' not found on Wikipedia."})
        return json.dumps({"found": True, "article": summary}, default=str)
    except Exception as e:
        return json.dumps({"error": f"Failed to retrieve Wikipedia article: {str(e)}"})


if __name__ == "__main__":
    research_mcp.run()

