import tqdm
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig

from src.bot_types import State
from src.indexer import indexer, collection, vector_store


def search_runbook(state: State):
    if collection.count() == 0:
        # TODO: Update this to consider that the version may have been updated
        embed_runbooks(state)

    results = vector_store.similarity_search_with_relevance_scores(
        state.title, k=2, score_threshold=0.8
    )
    state.matched_runbooks = [result[0].metadata["url"] for result in results]
    return state


def embed_runbooks(state):
    # Go fetch the configs and load them up
    config = RunnableConfig(recursion_limit=100)
    progress_bar = None
    for chunk in indexer.stream(
        state, config=config, stream_mode="values", subgraphs=True
    ):
        if isinstance(chunk, BaseMessage):
            chunk.pretty_print()
        elif isinstance(chunk, tuple):
            # Handle the tuple case
            if len(chunk) == 2:
                load_state = chunk[1]
                if not progress_bar:
                    progress_bar = tqdm.tqdm(
                        total=len(load_state["docs"]), desc="Loading documents"
                    )
                progress_bar.update()
            else:
                print(chunk)
        else:
            print(chunk)
