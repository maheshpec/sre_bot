import os
import re

from langchain.schema import AIMessage
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.constants import START, END
from langgraph.graph import StateGraph

from src.bot_types import State
from src.jira_retriever import pull_problem_details
from src.searcher import search_runbook
from src.updater import jira_updater


def parse(ai_message: AIMessage) -> AIMessage:
    """Parse the AI message."""
    ai_message.content = re.sub(
        r"<think>.*?</think>\n*", "", ai_message.content, flags=re.DOTALL
    )
    return ai_message


DB_URI = os.getenv("CHECKPOINTER_URI")


def main():
    with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
        # checkpointer.setup()

        graph_builder = StateGraph(State)
        graph_builder.add_node("pull_problem_details", pull_problem_details)
        graph_builder.add_node("search_runbook", search_runbook)
        graph_builder.add_node("jira_updater", jira_updater)

        graph_builder.add_edge(START, "pull_problem_details")
        graph_builder.add_edge("pull_problem_details", "search_runbook")
        graph_builder.add_edge("search_runbook", "jira_updater")
        graph_builder.add_edge("jira_updater", END)
        graph = graph_builder.compile(checkpointer=checkpointer)

        config = RunnableConfig(configurable={"thread_id": "1"})

        i = 0
        while i < 1:
            if os.getenv("PROBLEM_TICKET"):
                id = os.getenv("PROBLEM_TICKET")
            else:
                id = input("Enter the ticket number: ")
                
            if id.upper() in ("Q", "QUIT", "EXIT"):
                print("bye!!")
                break

            state = State(id=id)
            # Uncomment to resume from breakpoint
            # state = None
            for chunk in graph.stream(state, config=config, stream_mode="values"):
                if isinstance(chunk, BaseMessage):
                    chunk.pretty_print()
                else:
                    print(chunk)
            i += 1


if __name__ == "__main__":
    main()
