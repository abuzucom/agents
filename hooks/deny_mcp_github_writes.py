#!/usr/bin/env python3
"""Gate MCP write tools that bypass the shell gates and the trusted wrapper.

Review comment and reply tools deny. `add_issue_comment` and
`update_issue_comment` ask for consent at each call. Merges, auto-merge, a
pull request that is not a draft, and any label field deny under Rules 5
and 23. Every other known write asks. A verified read passes only on a
server in `READ_SERVERS`. Every
action outside those lists gets an explicit verdict: a destructive name
denies and anything else asks. `core.decide` turns an ask into a deny in
unattended modes.

The gate applies to every MCP server, because a server's name comes from
user configuration and proves nothing about what the server does.

`--client` selects the payload shape and the native response:
- claude: `mcp__<server>__<tool>` in `tool_name`. Ask through `core.decide`.
- codex: the same name shape. Codex treats an ask as a failed hook and runs
  the tool, so every ask denies.
- gemini: `mcp_<server>_<tool>` in `tool_name`. Gemini has no ask decision,
  so every ask denies. stdout carries one JSON object.
- antigravity: `toolCall.name` is `call_mcp_tool` with `ServerName`,
  `ToolName`, and `Arguments` in `toolCall.args`, or `mcp_<server>_<tool>`
  for an eager tool. Asks use `force_ask`, which a cached "Always Allow"
  cannot skip.

A flat `mcp_<server>_<tool>` name gives no reliable split, because server
and tool names may both hold `_`. The gate tests every split point against
the known actions and treats a name with no match as unknown.

Reasons are fixed constants. No tool name, server name, or argument reaches
the reason text, so a hostile server cannot write into a consent prompt.
"""
import json
import sys

import _gate_core as core

GATE = "deny_mcp_github_writes.py"
CLAUDE = "claude"
CODEX = "codex"
GEMINI = "gemini"
ANTIGRAVITY = "antigravity"
CLIENTS = frozenset({CLAUDE, CODEX, GEMINI, ANTIGRAVITY})
CLIENT_OPTION = "--client"
# Neither client offers a consent prompt a hook can request.
DENY_ONLY_CLIENTS = frozenset({CODEX, GEMINI})
JSON_DECISION_CLIENTS = frozenset({GEMINI, ANTIGRAVITY})
ANTIGRAVITY_ASK = "force_ask"
MCP_PREFIX = "mcp__"
MCP_SEPARATOR = "__"
FLAT_MCP_PREFIX = "mcp_"
FLAT_SEPARATOR = "_"
ANTIGRAVITY_MCP_TOOL = "call_mcp_tool"
ANTIGRAVITY_SERVER_FIELD = "ServerName"
ANTIGRAVITY_TOOL_FIELD = "ToolName"
ANTIGRAVITY_ARGUMENTS_FIELD = "Arguments"
# Gemini truncates sanitized MCP tool names past 63 characters. A longer
# flat name skips the split-point search and counts as unknown.
MAX_FLAT_NAME_LENGTH = 256
LABELS_FIELD = "labels"
DRAFT_FIELD = "draft"
COMMENT_ACTIONS = frozenset({"add_reply_to_pull_request_comment", "pull_request_review_write",
                             "add_comment_to_pending_review"})
CONSENT_COMMENT_ACTIONS = frozenset({"add_issue_comment", "update_issue_comment"})
DENIED_ACTIONS = frozenset({"merge_pull_request", "enable_pr_auto_merge",
                            "create_pull_request_with_copilot"})
ASKED_ACTIONS = frozenset({"push_files", "create_or_update_file", "delete_file",
                           "fork_repository", "create_repository", "create_branch",
                           "issue_write", "sub_issue_write", "resolve_review_thread",
                           "unresolve_review_thread", "request_copilot_review",
                           "assign_copilot_to_issue", "actions_run_trigger",
                           "update_pull_request_branch", "disable_pr_auto_merge"})
# Read tools of the GitHub MCP server. A name prefix proves nothing, since
# the server chooses the name, so only listed reads pass.
READ_ACTIONS = frozenset({
    "actions_get", "actions_list", "get_check_run", "get_commit", "get_copilot_job_status",
    "get_file_contents", "get_job_logs", "get_label", "get_latest_release", "get_me",
    "get_release_by_tag", "get_tag", "get_team_members", "get_teams", "issue_read",
    "list_branches", "list_commits", "list_issue_fields", "list_issue_types", "list_issues",
    "list_pull_requests", "list_releases", "list_repository_collaborators", "list_tags",
    "pull_request_read", "search_code", "search_issues", "search_pull_requests",
    "search_repositories", "search_users",
})
# A read passes only on these server names. The user's MCP configuration
# names each server, so a hostile server cannot pick a name from this list.
# A tool name alone binds nothing, since the server chooses it.
READ_SERVERS = frozenset({"github", "plugin_engineering_github"})
CREATE_PULL_REQUEST = "create_pull_request"
UPDATE_PULL_REQUEST = "update_pull_request"
KNOWN_ACTIONS = (COMMENT_ACTIONS | CONSENT_COMMENT_ACTIONS | DENIED_ACTIONS | ASKED_ACTIONS
                 | READ_ACTIONS | {CREATE_PULL_REQUEST, UPDATE_PULL_REQUEST})
# Verbs that remove data, history, or access a consent prompt cannot restore.
# An unlisted action with one of these prefixes denies instead of asking.
# Compared against the casefolded action, so a case variant still denies.
DESTRUCTIVE_PREFIXES = ("delete_", "merge_", "archive_", "transfer_", "remove_", "destroy_",
                        "wipe_", "purge_", "drop_", "erase_", "revoke_")
MALFORMED_REASON = "the gate cannot read the tool call or check it"
USAGE_REASON = "the gate received an unknown --client value and cannot check the call"
ERROR_REASON = "the gate raised an unexpected error. The gate cannot clear this call"
COMMENT_REASON = ("GitHub MCP review comment and reply tools bypass the wrapper. Post only on an "
                  "active human request through scripts/trusted_gh.py comment")
CONSENT_COMMENT_REASON = ("Repository workflow requires execution consent. The GitHub MCP tool "
                          "posts an issue or pull request comment (Rule 17)")
DENIED_REASON = "agents never merge, enable auto-merge, or open a pull request that is not a draft"
LABELS_REASON = "agents never add, remove, or change labels (Rule 23)"
DRAFT_REASON = "open every pull request as a draft (Rule 5)"
READY_REASON = "agents never mark a pull request ready without consent (Rule 5)"
ASK_REASON = "Repository workflow requires execution consent. The GitHub MCP tool writes to GitHub."
DESTRUCTIVE_REASON = "the MCP tool name marks a destructive action the gate never clears"
UNLISTED_REASON = ("Repository workflow requires execution consent. The MCP tool is not on the "
                   "gate's verified read list")
READ_SERVER_REASON = ("Repository workflow requires execution consent. A read passes without "
                      "consent only on a GitHub MCP server")
NO_CONSENT_REASON = "This client offers the hook no consent prompt, so the gate denies."


class MalformedCall(ValueError):
    """The payload names an MCP call the gate cannot read."""


def _tool_action(tool_name: str) -> str:
    """Return the text after the last `__` of a name the caller found prefixed."""
    return tool_name.rsplit(MCP_SEPARATOR, 1)[-1]


def _flat_candidates(name: str) -> tuple:
    """Return each suffix after an underscore in a flat `<server>_<tool>` name."""
    if len(name) > MAX_FLAT_NAME_LENGTH:
        return (name,)
    return tuple(name[index + 1:] for index, character in enumerate(name)
                 if character == FLAT_SEPARATOR) or (name,)


def _prefixed_call(payload: dict):
    """Return (server, candidates, input) for an `mcp__` name, or None for another tool."""
    tool_name = payload.get("tool_name")
    if not isinstance(tool_name, str):
        raise MalformedCall
    if not tool_name.startswith(MCP_PREFIX):
        return None
    action = _tool_action(tool_name)
    # A prefixed name with no action, such as `mcp__github__`, is still an MCP
    # call. Treating it as a non-MCP tool would let it pass unchecked.
    if not action:
        raise MalformedCall
    server, separator, _tool = tool_name[len(MCP_PREFIX):].rpartition(MCP_SEPARATOR)
    return (server if separator else ""), (action,), payload.get("tool_input")


def _flat_call(payload: dict):
    """Return (server, candidates, input) for a Gemini `mcp_` name, or None otherwise.

    The server stays empty, because no split of a flat name recovers it.
    """
    tool_name = payload.get("tool_name")
    if not isinstance(tool_name, str):
        raise MalformedCall
    if not tool_name.startswith(FLAT_MCP_PREFIX):
        return None
    return "", _flat_candidates(tool_name[len(FLAT_MCP_PREFIX):]), payload.get("tool_input")


def _antigravity_call(payload: dict):
    """Return (server, candidates, input) for an Antigravity MCP call, or None otherwise."""
    call = payload.get("toolCall")
    if not isinstance(call, dict) or not isinstance(call.get("name"), str):
        raise MalformedCall
    name, args = call["name"], call.get("args")
    if not isinstance(args, dict):
        raise MalformedCall
    if name == ANTIGRAVITY_MCP_TOOL:
        action = args.get(ANTIGRAVITY_TOOL_FIELD)
        if not isinstance(action, str) or not action:
            raise MalformedCall
        server = args.get(ANTIGRAVITY_SERVER_FIELD)
        return ((server if isinstance(server, str) else ""), (action,),
                args.get(ANTIGRAVITY_ARGUMENTS_FIELD, {}))
    if name.startswith(FLAT_MCP_PREFIX):
        return "", _flat_candidates(name[len(FLAT_MCP_PREFIX):]), args
    return None


CALL_READERS = {CLAUDE: _prefixed_call, CODEX: _prefixed_call, GEMINI: _flat_call,
                ANTIGRAVITY: _antigravity_call}


def _pull_request_decision(action: str, tool_input: dict) -> tuple:
    """Return (decision, reason) for the pull request create and update tools."""
    if action == CREATE_PULL_REQUEST and tool_input.get(DRAFT_FIELD) is not True:
        return "deny", DRAFT_REASON
    if action == UPDATE_PULL_REQUEST and tool_input.get(DRAFT_FIELD) is False:
        return "deny", READY_REASON
    return "ask", ASK_REASON


def _known_decision(server: str, action: str, tool_input: dict) -> tuple:
    """Return (decision, reason) for one action on the gate's known lists."""
    if action in READ_ACTIONS:
        return ("", "") if server in READ_SERVERS else ("ask", READ_SERVER_REASON)
    if action in COMMENT_ACTIONS:
        return "deny", COMMENT_REASON
    if action in CONSENT_COMMENT_ACTIONS:
        return "ask", CONSENT_COMMENT_REASON
    if action in DENIED_ACTIONS:
        return "deny", DENIED_REASON
    if action in (CREATE_PULL_REQUEST, UPDATE_PULL_REQUEST):
        return _pull_request_decision(action, tool_input)
    return "ask", ASK_REASON


def _unknown_decision(candidates: tuple) -> tuple:
    """Deny a destructive name and ask for every other unlisted action."""
    if any(candidate.casefold().startswith(DESTRUCTIVE_PREFIXES) for candidate in candidates):
        return "deny", DESTRUCTIVE_REASON
    return "ask", UNLISTED_REASON


def write_decision(payload: dict, client: str = CLAUDE) -> tuple:
    """Return (decision, reason) for one pre-tool payload from `client`."""
    try:
        call = CALL_READERS[client](payload)
    except MalformedCall:
        return "deny", MALFORMED_REASON
    if call is None:
        return "", ""
    server, candidates, tool_input = call
    if not isinstance(tool_input, dict):
        return "deny", MALFORMED_REASON
    # Any present labels field writes labels. An empty list clears every label.
    if LABELS_FIELD in tool_input:
        return "deny", LABELS_REASON
    action = next((candidate for candidate in candidates if candidate in KNOWN_ACTIONS), "")
    if action:
        return _known_decision(server, action, tool_input)
    return _unknown_decision(candidates)


def emit_decision(client: str, payload: dict, decision: str, reason: str) -> int:
    """Print the native response for `client` and return the exit code it needs."""
    if not decision:
        return 0
    if decision == "ask" and client in DENY_ONLY_CLIENTS:
        decision, reason = "deny", f"{reason.rstrip('.')}. {NO_CONSENT_REASON}"
    if client == CLAUDE:
        return core.decide(GATE, payload, decision, reason)
    if client not in JSON_DECISION_CLIENTS:
        return core.emit(GATE, decision, reason)
    message = f"blocked by hooks/{GATE}: {reason}"
    if decision == "deny":
        message = core.with_denial_response(message)
    native = ANTIGRAVITY_ASK if decision == "ask" else decision
    print(json.dumps({"decision": native, "reason": message}))
    return 0


def selected_client(argv: list):
    """Return the client named by `--client`, the default, or None for a bad value."""
    if CLIENT_OPTION not in argv:
        return CLAUDE
    index = argv.index(CLIENT_OPTION) + 1
    value = argv[index] if index < len(argv) else None
    return value if value in CLIENTS else None


def main(argv=None) -> int:
    """Read one pre-tool payload and emit a deny, an ask, or nothing."""
    client = selected_client(sys.argv[1:] if argv is None else argv)
    if client is None:
        return core.emit(GATE, "deny", USAGE_REASON)
    try:
        payload = core.read_payload()
        if payload is None:
            return emit_decision(client, {}, "deny", MALFORMED_REASON)
        decision, reason = write_decision(payload, client)
        return emit_decision(client, payload, decision, reason)
    except Exception:
        # A non-blocking exit lets the call through unchecked on every client.
        # Each client receives a deny in its own format instead.
        return emit_decision(client, {}, "deny", ERROR_REASON)


if __name__ == "__main__":
    sys.exit(main())
