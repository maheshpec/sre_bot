import os
from typing import Literal
from uuid import uuid4

import chromadb
from atlassian import Confluence
from bs4 import BeautifulSoup
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langgraph.constants import START, END
from langgraph.graph import StateGraph

from src.bot_types import IndexerState

confluence = Confluence(
    url=os.getenv("CONFLUENCE_URL"),
    username=os.getenv("ATLASSIAN_USERNAME"),
    password=os.getenv("ATLASSIAN_API_TOKEN"),
    cloud=True,
)

embeddings = OllamaEmbeddings(model="nomic-embed-text")
persistent_client = chromadb.PersistentClient(path="./chroma_langchain_db")
collection = persistent_client.get_or_create_collection("runbooks")
vector_store = Chroma(
    collection_name="runbooks",
    embedding_function=embeddings,
    client=persistent_client,
)


def fetch_docs(state: IndexerState):
    """Fetch documents from the source."""
    page_id = confluence.get_page_id(os.getenv("CONFLUENCE_SPACE_KEY"), os.getenv("RUNBOOK_PARENT_PAGE"))
    pages = confluence.get_child_id_list(page_id=page_id)
    state.docs = pages
    return state


def doc_loading_router(
    state: IndexerState,
) -> Literal["fetch_and_load_runbook_doc", END]:
    """Route to the appropriate document loading function."""
    if not state.docs:
        return END

    if state.loaded_docs and len(state.docs) == len(state.loaded_docs):
        return END
    else:
        return "fetch_and_load_runbook_doc"


def fetch_and_load_runbook_doc(state: IndexerState):
    page_to_fetch = len(state.loaded_docs) if state.loaded_docs else 0
    if page_to_fetch >= len(state.docs):
        return state

    page = confluence.get_page_by_id(
        state.docs[page_to_fetch], "body.view, version", status=None, version=None
    )
    content = page["body"]["view"]["value"]
    text = BeautifulSoup(content, "lxml").get_text(" ", strip=True)
    metadata = {
        "title": page["title"],
        "url": page["_links"]["self"],
    }
    document = Document(
        page_content=text,
        metadata=metadata,
    )

    vector_store.add_documents(documents=[document], ids=[str(uuid4())])
    if not state.loaded_docs:
        state.loaded_docs = [state.docs[page_to_fetch]]
    else:
        state.loaded_docs.append(state.docs[page_to_fetch])
    return state


indexer_builder = StateGraph(IndexerState)
indexer_builder.add_node("fetch_docs", fetch_docs)
indexer_builder.add_node("fetch_and_load_runbook_doc", fetch_and_load_runbook_doc)

indexer_builder.add_edge(START, "fetch_docs")
indexer_builder.add_edge("fetch_docs", "fetch_and_load_runbook_doc")
indexer_builder.add_conditional_edges("fetch_and_load_runbook_doc", doc_loading_router)
indexer = indexer_builder.compile()
