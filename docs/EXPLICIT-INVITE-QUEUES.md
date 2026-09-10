# Explicit player invites and autonomous queues

The recruitment coordinator previously rejected queued bots as `queued_activity`.
On TBC this included `m_lfgInfo.queued`, even for a bot standing in an ordinary
world zone. The response did not mean the bot was inside a battleground.

Authorized player invitations now disregard the bot's LFG/BG enrollment during
eligibility checks, cancel its personal queue entries through native APIs, and
accept the invitation after earlier LFG callbacks have drained. Eligibility is
rechecked after that asynchronous boundary. Queue cancellation does not remove
another player's group queue. Ordinary command security retains its queue rules.

Private-account authorization, faction policy, ignores, level/gearscore policy,
another human controller, existing parties, competing invitations/reservations,
group capacity and session/transfer checks remain in force. A BG raid alone is
not treated as another player's party; its original party still is. A requester
inside a battleground remains excluded, now with `requester_battleground`.

An invite accepts party membership; summoning is the separate existing command.
Invitation acceptance preserves combat, death, health, mana, talents and gear.
Explicit summons retain their resurrection and post-arrival HP/mana refill.

Validation: deterministic tests execute the production coordinator, permission
policy, queue-cleanup and summon bodies with simulated native boundaries across
Classic, TBC and Wrath. They cover deferred queue callbacks and ownership changes
while waiting. These are code-level tests, not live in-game testing of the reported
characters or a claim that their exact runtime queue flags were observed.
