from crewai import Agent
from tools import clean_results_tool, enrich_results_tool, google_search_tool, save_results_tool


def search_agent(llm) -> Agent:
    return Agent(
        role="Google Search Specialist",
        goal="Fetch raw Google search results for a given keyword using SerpAPI",
        backstory=(
            "You are an expert at querying search engines and retrieving comprehensive "
            "result sets. You always use the Google Search tool with both keyword and "
            "num_results, and return the file path exactly as the tool returns it."
        ),
        tools=[google_search_tool],
        llm=llm,
        verbose=True,
    )


def cleaner_agent(llm) -> Agent:
    return Agent(
        role="Data Cleaner",
        goal="Remove meaningless content from scraped records using the Clean Results tool",
        backstory=(
            "You are a data quality specialist. You pass the file path to the Clean Results "
            "tool and return the new file path exactly as the tool returns it."
        ),
        tools=[clean_results_tool],
        llm=llm,
        verbose=True,
    )


def enricher_agent(llm) -> Agent:
    return Agent(
        role="Results Enricher",
        goal="Generate Traditional Chinese ai_summary for each record using the Enrich Results tool",
        backstory=(
            "You are a pipeline operator. You pass the file path to the Enrich Results "
            "tool and return the new file path exactly as the tool returns it."
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
            "You are responsible for persisting finalized data. You call the Save Results "
            "tool with the keyword and enriched file path, then return the confirmation."
        ),
        tools=[save_results_tool],
        llm=llm,
        verbose=True,
    )
