import sys
from dotenv import load_dotenv
from crewai import Crew, Process, LLM

from agents import search_agent, extractor_agent, summarizer_agent
from tasks import search_task, extract_task, summarize_task


def build_crew(keyword: str) -> Crew:
    llm = LLM(model="openai/gpt-4o-mini")

    s_agent = search_agent(llm)
    e_agent = extractor_agent(llm)
    r_agent = summarizer_agent(llm)

    t1 = search_task(s_agent, keyword)
    t2 = extract_task(e_agent, t1)
    t3 = summarize_task(r_agent, keyword, t2)

    return Crew(
        agents=[s_agent, e_agent, r_agent],
        tasks=[t1, t2, t3],
        process=Process.sequential,
        verbose=True,
    )


if __name__ == "__main__":
    load_dotenv()
    keyword = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "python web scraping"
    print(f"\n=== Google Search Crew starting: {keyword!r} ===\n")
    result = build_crew(keyword).kickoff()
    print("\n=== Done ===\n")
    print(result)
