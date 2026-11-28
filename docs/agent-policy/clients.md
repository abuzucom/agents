# Client lifecycle
Every client follows the matching skill in `skills/`.

Client APIs differ. Do not claim coverage that the client cannot observe.
Repository hooks remain defense in depth only.

No repository check verifies model compliance.

A multi-repository Claude Code cloud session starts above the clones. It loads
no repository hooks. The rule reaches it only through the synchronized policy
copies. Agents there run the branch checker manually.

Clients without hooks create `.scratch/<id>/` and `.worktrees/<id>/` with
`mkdir -p`.

Ask each open choice through the client's question tool.

`docs/gate-internals.md` describes each client's hook events and delivery.
