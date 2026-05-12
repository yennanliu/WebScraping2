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
    load_dotenv()

    args = sys.argv[1:]
    if args and args[-1].isdigit():
        num_results = int(args[-1])
        keyword = " ".join(args[:-1]) or "python web scraping"
    else:
        num_results = 10
        keyword = " ".join(args) or "python web scraping"

    print(f"\n=== Google Search Crew | keyword: {keyword!r} | records: {num_results} ===\n")
    result = build_crew(keyword, num_results).kickoff()
    print("\n=== Done ===\n")
    print(result)
