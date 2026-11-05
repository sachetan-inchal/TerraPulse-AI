import re
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import httpx

from schemas.research import ScientificPaper, ResearchSearchResult


class ResearchService:
    CROSSREF_API = "https://api.crossref.org/works"
    SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper/search"
    USER_AGENT = "TerraPulseAIR-ResearchEngine/1.0 (mailto:research@terrapulse.ai)"

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    def search_publications(self, query: str, limit: int = 5) -> ResearchSearchResult:
        """
        Search peer-reviewed scientific publications via Crossref API.
        If no results found or query is for a fictional term, returns empty list honestly.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        headers = {"User-Agent": self.USER_AGENT}
        params = {
            "query": query,
            "rows": limit,
            "sort": "relevance",
            "select": "DOI,title,author,published,container-title,abstract,URL,is-referenced-by-count"
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(self.CROSSREF_API, headers=headers, params=params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as e:
            return ResearchSearchResult(
                query=query,
                total_found=0,
                papers=[],
                search_timestamp=now_iso,
                provider="Crossref",
                message=f"External research API error: {str(e)}"
            )

        items = data.get("message", {}).get("items", [])
        total_found = data.get("message", {}).get("total-results", 0)

        # Crossref sometimes returns loosely matched articles even when query is completely fictitious (e.g. QX-999).
        # We perform a strict relevance verification: if specific code/acronym like QX-999 or XYZ-927 was searched,
        # verify that the title or abstract actually mentions the key tokens or topic!
        papers: List[ScientificPaper] = []
        is_code_pattern = re.compile(r'\b[A-Za-z]{2,4}[-_]?\d{3,4}\b')
        specific_codes = is_code_pattern.findall(query)

        for item in items:
            title_list = item.get("title", [])
            title = title_list[0] if title_list else "Untitled Publication"
            doi = item.get("DOI")

            # Extract year
            pub_date = item.get("published", {}).get("date-parts", [[None]])[0]
            year = pub_date[0] if pub_date and pub_date[0] is not None else None

            # Extract authors
            authors_data = item.get("author", [])
            authors: List[str] = []
            for a in authors_data:
                given = a.get("given", "")
                family = a.get("family", "")
                full = f"{given} {family}".strip() or a.get("name")
                if full:
                    authors.append(full)

            # Container / journal
            containers = item.get("container-title", [])
            journal = containers[0] if containers else None

            # Abstract (strip JATS XML tags if present)
            raw_abstract = item.get("abstract")
            clean_abstract = None
            if raw_abstract:
                clean_abstract = re.sub(r'<[^>]+>', '', raw_abstract).strip()

            url = item.get("URL") or (f"https://doi.org/{doi}" if doi else None)
            citations = item.get("is-referenced-by-count")

            # If the search specifically looked for a code like QX-999 or XYZ-927, check whether it actually matches
            if specific_codes:
                text_corpus = f"{title} {clean_abstract or ''}".upper()
                if not any(code.upper() in text_corpus for code in specific_codes):
                    # Does not actually match the specific fictitious code
                    continue

            papers.append(
                ScientificPaper(
                    doi=doi,
                    title=title,
                    authors=authors,
                    publication_year=year,
                    journal=journal,
                    abstract=clean_abstract,
                    url=url,
                    is_peer_reviewed=True,
                    source_database="Crossref",
                    citation_count=citations
                )
            )

        msg = None
        if not papers:
            if specific_codes:
                msg = f"No scientific literature found matching specific identifier/code '{', '.join(specific_codes)}'."
            else:
                msg = f"No peer-reviewed publications found for query '{query}'."

        return ResearchSearchResult(
            query=query,
            total_found=len(papers),
            papers=papers,
            search_timestamp=now_iso,
            provider="Crossref",
            message=msg
        )

    def verify_doi(self, doi: str) -> Optional[ScientificPaper]:
        """Verify whether a DOI exists in Crossref and return its verified metadata."""
        clean_doi = doi.strip()
        if clean_doi.startswith("https://doi.org/"):
            clean_doi = clean_doi.replace("https://doi.org/", "")
        elif clean_doi.startswith("http://dx.doi.org/"):
            clean_doi = clean_doi.replace("http://dx.doi.org/", "")

        url = f"{self.CROSSREF_API}/{clean_doi}"
        headers = {"User-Agent": self.USER_AGENT}

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code == 404:
                    return None
                resp.raise_for_status()
                data = resp.json()

            item = data.get("message", {})
            title_list = item.get("title", [])
            title = title_list[0] if title_list else "Untitled"

            pub_date = item.get("published", {}).get("date-parts", [[None]])[0]
            year = pub_date[0] if pub_date and pub_date[0] is not None else None

            authors_data = item.get("author", [])
            authors = [
                f"{a.get('given', '')} {a.get('family', '')}".strip() or a.get("name", "")
                for a in authors_data
                if a.get("family") or a.get("name")
            ]

            containers = item.get("container-title", [])
            journal = containers[0] if containers else None

            raw_abstract = item.get("abstract")
            clean_abstract = re.sub(r'<[^>]+>', '', raw_abstract).strip() if raw_abstract else None

            return ScientificPaper(
                doi=clean_doi,
                title=title,
                authors=authors,
                publication_year=year,
                journal=journal,
                abstract=clean_abstract,
                url=f"https://doi.org/{clean_doi}",
                is_peer_reviewed=True,
                source_database="Crossref",
                citation_count=item.get("is-referenced-by-count")
            )
        except Exception:
            return None

    def search_wikipedia(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Search authentic encyclopedia articles from Wikipedia REST API.
        Returns genuine titles, snippets, and page URLs.
        """
        headers = {"User-Agent": "TerraPulseAIR-ResearchEngine/2.0 (contact@terrapulse.ai)"}
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": limit,
            "format": "json"
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get("https://en.wikipedia.org/w/api.php", headers=headers, params=params)
                if resp.status_code != 200:
                    return []
                data = resp.json()

            search_results = data.get("query", {}).get("search", [])
            articles = []
            for item in search_results:
                title = item.get("title", "")
                snippet = re.sub(r'<[^>]+>', '', item.get("snippet", "")).strip()
                articles.append({
                    "title": title,
                    "snippet": snippet,
                    "url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                    "source": "Wikipedia Public Knowledgebase"
                })
            return articles
        except Exception:
            return []

    def get_wikipedia_summary(self, title: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve authentic article summary, description, and extract from Wikipedia.
        """
        headers = {"User-Agent": "TerraPulseAIR-ResearchEngine/2.0 (contact@terrapulse.ai)"}
        safe_title = title.strip().replace(" ", "_")
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{safe_title}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code != 200:
                    return None
                data = resp.json()

            return {
                "title": data.get("title"),
                "description": data.get("description"),
                "extract": data.get("extract"),
                "url": data.get("content_urls", {}).get("desktop", {}).get("page") or f"https://en.wikipedia.org/wiki/{safe_title}",
                "source": "Wikipedia REST API"
            }
        except Exception:
            return None

