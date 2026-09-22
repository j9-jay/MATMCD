import os

from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from langgraph.prebuilt import create_react_agent
from config import MODEL, OPENAI_API_KEY, TAVILY_API_KEY

os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
os.environ["TAVILY_API_KEY"] = TAVILY_API_KEY


class ReactClient:
    def __init__(self) -> None:
        model = ChatOpenAI(model=MODEL)
        search = TavilySearchResults(max_results=6)
        tools = [search]
        self.agent_executor = create_react_agent(model, tools)

    def inquire_LLMs(self, prompt: str, system_prompt: str, temperature: float = 0.5):
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=prompt),
        ]
        response = self.agent_executor.invoke({"messages": messages})
        print(response["messages"])
        return response["messages"][-1].content
