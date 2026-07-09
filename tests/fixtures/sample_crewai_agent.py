"""Sample CrewAI agent for scanner testing."""
from crewai import Agent, Crew, Process, Task
from crewai_tools import SerperDevTool

search_tool = SerperDevTool()

researcher = Agent(
    role="Research Analyst",
    goal="Find accurate information on any topic",
    backstory="Expert researcher with access to web search tools.",
    tools=[search_tool],
    verbose=True,
)

writer = Agent(
    role="Content Writer",
    goal="Write clear and engaging content",
    backstory="Professional writer specializing in technical topics.",
    verbose=True,
)

research_task = Task(
    description="Research the given topic thoroughly.",
    expected_output="A comprehensive research summary.",
    agent=researcher,
)

write_task = Task(
    description="Write a report based on the research.",
    expected_output="A well-structured report.",
    agent=writer,
)

crew = Crew(
    agents=[researcher, writer],
    tasks=[research_task, write_task],
    process=Process.sequential,
    verbose=True,
)
