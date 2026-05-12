from crewai import Agent, Task


def search_task(agent: Agent, keyword: str, num_results: int) -> Task:
    return Task(
        description=(
            f'Use the Google Search tool to search for: "{keyword}". '
            f"Pass num_results={num_results}. Return the file path exactly as the tool returns it."
        ),
        expected_output="A file path string like output/.tmp_<keyword>_<timestamp>.json",
        agent=agent,
    )


def clean_task(agent: Agent, prior: Task) -> Task:
    return Task(
        description=(
            "Call the Clean Results tool. Pass the file path from the previous task as tmp_file_path. "
            "Return the new file path exactly as the tool returns it."
        ),
        expected_output="A file path string like output/.cleaned_<keyword>_<timestamp>.json",
        agent=agent,
        context=[prior],
    )


def enrich_task(agent: Agent, prior: Task) -> Task:
    return Task(
        description=(
            "Call the Enrich Results tool. Pass the file path from the previous task as cleaned_file_path. "
            "Return the new file path exactly as the tool returns it."
        ),
        expected_output="A file path string like output/.enriched_<keyword>_<timestamp>.json",
        agent=agent,
        context=[prior],
    )


def save_task(agent: Agent, keyword: str, prior: Task) -> Task:
    return Task(
        description=(
            f'Call the Save Results tool with keyword="{keyword}" and '
            "enriched_file_path set to the file path from the previous task. "
            "Return the confirmation message from the tool."
        ),
        expected_output="A confirmation string like: Saved N records to output/<keyword>_<timestamp>.json",
        agent=agent,
        context=[prior],
    )
