from crewai import Agent
from tools import google_search_tool, save_results_tool


def search_agent(llm) -> Agent:
    return Agent(
        role="Google Search Specialist",
        goal="Fetch raw Google search results for a given keyword using SerpAPI",
        backstory=(
            "You are an expert at querying search engines and retrieving comprehensive "
            "result sets. You always use the Google Search tool and return the full raw output."
        ),
        tools=[google_search_tool],
        llm=llm,
        verbose=True,
    )


def extractor_agent(llm) -> Agent:
    return Agent(
        role="Data Extractor",
        goal="Parse raw SerpAPI JSON and produce a clean structured list of search results",
        backstory=(
            "You are a precise data engineer who excels at transforming messy JSON into "
            "clean, structured records with consistent fields: title, url, snippet, position."
        ),
        llm=llm,
        verbose=True,
    )


def summarizer_agent(llm) -> Agent:
    return Agent(
        role="Research Summarizer",
        goal="Write a concise markdown summary of the search results and save output files",
        backstory=(
            "You are a skilled analyst who synthesizes search results into clear, "
            "actionable summaries and persists them for future reference."
        ),
        tools=[save_results_tool],
        llm=llm,
        verbose=True,
    )
