import os

from jira import JIRA

from src.bot_types import State


def pull_problem_details(state: State):
    jira = JIRA(
        server=os.getenv("JIRA_URL"),
        basic_auth=(
            os.getenv("ATLASSIAN_USERNAME"),
            os.getenv("ATLASSIAN_API_TOKEN"),
        ),
    )
    issue = jira.issue(state.id)
    state.title = issue.fields.summary
    state.comments = [comment.body for comment in issue.fields.comment.comments]
    state.description = issue.fields.description
    return state
