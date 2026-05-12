from crewai import Agent, Task


def search_task(agent: Agent, keyword: str) -> Task:
    return Task(
        description=f'Use the Google Search tool to search for: "{keyword}". Return the full raw JSON results.',
        expected_output="A raw JSON string containing the list of organic search results from SerpAPI.",
        agent=agent,
    )


def extract_task(agent: Agent, prior: Task) -> Task:
    return Task(
        description=(
            "Parse the raw SerpAPI JSON from the previous task. "
            "Extract each result into a clean record with these fields: "
            "position (int), title (str), url (str), snippet (str). "
            "Return a valid JSON array of these records."
        ),
        expected_output=(
            'A JSON array of objects, e.g. [{"position": 1, "title": "...", "url": "...", "snippet": "..."}, ...]'
        ),
        agent=agent,
        context=[prior],
    )


def summarize_task(agent: Agent, keyword: str, prior: Task) -> Task:
    return Task(
        description=(
            f'The keyword was: "{keyword}". '
            "Using the structured results from the previous task, do two things:\n"
            "1. Write a markdown summary: include a # heading with the keyword, "
            "then a numbered list where each item shows the title, URL, and a one-sentence snippet.\n"
            "2. Call the Save Results tool with: keyword, the JSON array (as a string), "
            "and the markdown summary."
        ),
        expected_output=(
            "Confirmation message showing the two file paths that were saved (JSON and markdown)."
        ),
        agent=agent,
        context=[prior],
    )
