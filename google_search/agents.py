from crewai import Agent
from tools import google_search_tool, save_results_tool


def search_agent(llm) -> Agent:
    return Agent(
        role="Google Search Specialist",
        goal="Fetch raw Google search results for a given keyword using SerpAPI",
        backstory=(
            "You are an expert at querying search engines and retrieving comprehensive "
            "result sets. You always use the Google Search tool with both keyword and "
            "num_results, and return the full raw output."
        ),
        tools=[google_search_tool],
        llm=llm,
        verbose=True,
    )


def extractor_agent(llm) -> Agent:
    return Agent(
        role="Data Extractor",
        goal=(
            "Parse raw SerpAPI JSON and produce clean records with url, "
            "original_abstract, and a concise ai_summary for each result"
        ),
        backstory=(
            "You are a precise data engineer who transforms raw search results into "
            "structured records. For each result you extract the URL and snippet, "
            "then write a crisp one-sentence AI summary of what the page covers."
        ),
        llm=llm,
        verbose=True,
    )


def summarizer_agent(llm) -> Agent:
    return Agent(
        role="Results Persister",
        goal="Save the structured search results to disk using the Save Results tool",
        backstory=(
            "You are responsible for persisting finalized data. You take the JSON array "
            "from the previous step and call the Save Results tool to write it to disk."
        ),
        tools=[save_results_tool],
        llm=llm,
        verbose=True,
    )
