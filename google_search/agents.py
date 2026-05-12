from crewai import Agent
from tools import enrich_results_tool, google_search_tool, save_results_tool


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


def enricher_agent(llm) -> Agent:
    return Agent(
        role="Results Enricher",
        goal="Call the Enrich Results tool with the full JSON from the previous task and return its output",
        backstory=(
            "You are a pipeline operator. You pass data to tools exactly as received "
            "and return their output without modification."
        ),
        tools=[enrich_results_tool],
        llm=llm,
        verbose=True,
    )


def persister_agent(llm) -> Agent:
    return Agent(
        role="Results Persister",
        goal="Save the enriched search results to disk using the Save Results tool",
        backstory=(
            "You are responsible for persisting finalized data. You take the JSON array "
            "from the previous step and call the Save Results tool to write it to disk."
        ),
        tools=[save_results_tool],
        llm=llm,
        verbose=True,
    )
