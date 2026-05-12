import sys
from dotenv import load_dotenv
from crewai import Crew, Process, LLM

from agents import cleaner_agent, enricher_agent, persister_agent, search_agent
from tasks import clean_task, enrich_task, save_task, search_task


def build_crew(keyword: str, num_results: int) -> Crew:
    llm = LLM(model="openai/gpt-4o-mini")

    s_agent = search_agent(llm)
    c_agent = cleaner_agent(llm)
    e_agent = enricher_agent(llm)
    p_agent = persister_agent(llm)

    t1 = search_task(s_agent, keyword, num_results)
    t2 = clean_task(c_agent, t1)
    t3 = enrich_task(e_agent, t2)
    t4 = save_task(p_agent, keyword, t3)

    return Crew(
        agents=[s_agent, c_agent, e_agent, p_agent],
        tasks=[t1, t2, t3, t4],
        process=Process.sequential,
        verbose=True,
    )


if __name__ == "__main__":
    import argparse

    load_dotenv()

    parser = argparse.ArgumentParser(description="Google Search multi-agent scraper")
    parser.add_argument("keyword", help='Search keyword, e.g. "蝦皮賣家外掛"')
    parser.add_argument("num_results", nargs="?", type=int, default=10, help="Max records to collect (default: 10)")
    parser.add_argument("--site", default="", help='Restrict results to a domain, e.g. --site threads.net')
    parsed = parser.parse_args()

    query = f"{parsed.keyword} site:{parsed.site}" if parsed.site else parsed.keyword

    print(f"\n=== Google Search Crew | query: {query!r} | records: {parsed.num_results} ===\n")
    result = build_crew(query, parsed.num_results).kickoff()
    print("\n=== Done ===\n")
    print(result)
