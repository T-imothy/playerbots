# Bot recruitment, summons and preparation

## Compatibility and scope

The current Group Builder (addon baseline `fb3b759`, version 0.8.0) uses ordinary `who`/`summon` whispers, native invitations, talent/strategy commands and six `.bot` preparation commands. These legacy paths remain supported. The optional `recruit v1` interface is **not consumed by 0.8.0**. No addon files or native dungeon/boss mechanics are changed by this work.

Composition, explicit human role assignments, selected existing bots, activity choice and explicit raid conversion remain the caller's responsibility. The service operates on explicitly selected bot GUIDs; it does not infer human roles, rearrange subgroups, convert groups, manufacture raid templates, or autonomously choose an entire composition. The existing addon already performs that planning. The v1 invite size parameter additionally bounds admission to the selected size. Native instance-entry limits still apply.

## Code-backed defects and changes

- `WhoAction::Execute` used the default full-control `TellPlayer` permission despite incoming `who` being unsecured. Exact raw `who` now enters a bounded world-thread queue from `PlayerbotAI::HandleCommand`; `WhoAction` also delegates empty queries. Identity and recruitment eligibility are checked before a direct whisper containing the existing `QuerySpec` format. Optional AI chatter/silent mode and proximity do not suppress this specific reply. General `TellPlayer` security is unchanged. Humans and unauthorized alts receive no bot-identification payload.
- `AcceptInvitationAction` ran in the non-combat AI strategy and also reset strategies/AI, reset raids and updated gear. Human native invitations now register with the world-thread coordinator and expire after 15 seconds. Acceptance does not depend on AI sleep, combat, AFK or death; unsafe transfers/control defer. Native group acceptance is retained. Joining only assigns the authorized controller/default non-combat movement and removes autonomous LFG/BG strategies; it does not resurrect, heal, teleport, reset talents/AI, reset raids or regear. Bot-led autonomous invitations retain their old path.
- Human `join` helper calls now use native invitations through the coordinator: no external-group departure and no automatic raid conversion. Existing external groups include bot-only groups. Revalidate session identity, controller, policy, invite identity, leader, group size and instance at acceptance. Old AI invite packets cannot accept expired human invitations. Human session/group updates run before pending bot acceptance.
- Convenience `summon` requests are bounded and preserve native teleport checks. Explicit convenience summons proceed while the requester, bot, or both are in combat. Taxi/transport, charm and active transfers still defer until the native transition is safe; ownership, queue and instance-entry checks remain enforced. Acceptance and arrival are separate statuses. Arrival can be acknowledged in combat; gear preparation is also permitted in combat, while supply and talent changes retain their separate combat checks. Arrival requires completed transition, matching map AND instance, alive, within 10 yards and line of sight. Same-map/different-instance shortcuts are refused. Native summon responses, warlock rituals, meeting-stone ritual interaction and recent teleport acknowledgement safeguards are preserved.
- Deferred convenience revival now also records the destination instance. `AiPlayerbot.Recruitment.Revive = 1` preserves the prior allowed revival policy; setting 0 refuses dead convenience summons. Native resurrection/summon rules are unchanged. The existing `NonGmFreeSummon`, innkeeper, faction, guild, level and gear-score settings remain authoritative.
- The six gear/supply commands and their aliases validate bot identity, controller, world/transition state and pending summons. `gear`/`equip` work in combat, including their HP/mana refill; supply and talent changes continue to reject combat. Manual preparation has **no newly invented distance/map requirement**. Structured preparation additionally requires arrival. No GM privileges are granted. Supply factories use the bot's level rather than the requester's level, and report storage/missing-data failures. Existing adequate supplies and inapplicable class/ammo operations are documented successful no-ops. Reagents for explicit supply requests derive from learned non-generic class spells in the actual expansion; reusable spell totems retain the existing checks.
- Legacy preparation repeats with the same requester, bot, command, parameter, level and talent link replay their response for 60 seconds. Structured IDs replay for 10 minutes. Unsupported gear spec detection occurs before equipment destruction. Gear still uses the existing spec-aware factory; this does not redesign gear scoring.
- Talent inspection no longer reapplies talents, modifies public notes or invokes auto-learning. The first named build (stored spec number 1 / index 0) is reported correctly, and unset spec numbers no longer underflow. Missing premade paths use the class-indexed base spec. Guild/public-note writes tolerate a missing guild/member record. Mutating talent commands retain authorization and now reject unsafe preparation states.

## Exact optional interface

Send as an ordinary chat command, e.g. SAY:

```
.bot recruit v1 <id> discover <classId> <minLevel> <maxLevel> <cursor>
.bot recruit v1 <id> status <botGuidLow>
.bot recruit v1 <id> reserve <botGuidLow>
.bot recruit v1 <id> invite <botGuidLow> <selectedSize>
.bot recruit v1 <id> summon <botGuidLow>
.bot recruit v1 <id> prepare <botGuidLow> <operation>
.bot recruit v1 <id> cancel <botGuidLow-or-0-for-all>
```

ID: 1ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ32 ASCII letters, digits, `_` or `-`, scoped to the requester. Input maximum 240 characters. Use one ID per logical operation; retry identical payloads with the same ID. A changed payload under the same ID returns `id_conflict`. New status polls use new IDs (reusing an old ID returns its recorded answer). Discovery cursor starts at 0; follow the returned cursor until it is 0. Discovery lists eligible public/free random bots managed by the random-bot holder; direct identity/status checks also support authorized online account/guild alts. No account IDs or private-alt inventory are returned.

Preparation operation: exactly `gear`, `food`, `potions`, `consumes`, `reagents`, `ammo`. Talents and strategy configuration continue through existing commands; v1 does not infer or automatically apply a role. Selected size must be 5, 10, 20, 25 or 40; no automatic conversion. A party's native limit remains five regardless of a larger requested size.

System response:

```
PBRECRUIT 1 <id> <botGuidLow> <state> <reason-or-result>
```

Discovery candidate suffix: `<name> <classId> <level>` after `eligible ok`. Completion: `complete cursor=<next>;scanned=<count>`. An identical discovery retry replays the candidate batch and completion.

States: `eligible`, `reserved`, `invite_pending`, `joined`, `summon_pending`, `arrived`, `complete`, `refused`, `timed_out`, `cancelled`; initial stored state is `pending queued`. `joined` is actual membership, not fight readiness; `arrived` is not a confirmation of talents/gear/supplies. A repeated request while another summon is active returns `summon_pending existing_request`; poll actual status for readiness.

Reasons include `not_available_bot`, `not_authorized`, `wrong_faction`, `ignored`, `external_group`, `other_controller`, `existing`, `queued_activity`, `invited_elsewhere`, `recruitment_policy`, `not_controller`, `reserved`, `group_full`, `not_leader`, `stale_invite`, `different_instance`, `bot_transfer`, `requester_transfer`, `controlled`, `deadline`, `queue_deadline`, `requester_session_changed`, `bot_session_changed`, `membership_changed`, `leader_changed`, `destination_changed`, `revival_disabled`, `destination_or_summon_policy`, `not_arrived`, `unsupported_preparation`, `syntax`, `arguments`, `guid_required`, `size_required`, `unsupported_operation`, `id_conflict`, `busy`, `receipt_limit`, `discovery_rate_limit`.

Legacy summon/invite outcomes also produce readable system messages, e.g. `Botname: summon_pending (teleport_started)`. Eligible legacy `who` keeps `(43 lvl)` and `100 GS (` formatting after WoW markup stripping. An unavailable authorized bot instead whispers `Recruitment unavailable: <reason>`; this is not an eligibility proof that should trigger an invite.

Cancellation releases pending recruitment and reservations, leaves joined members and completed preparation alone, and never interrupts an already accepted native teleport. `transfer_may_complete` explicitly communicates that limitation. Disconnect/session replacement cancels pending mutations. There is no persistent exactly-once guarantee across a server restart or after the 10-minute receipt retention: reconcile state and require a deliberate new operation rather than blindly replaying old IDs. Cancellation does not erase successful operation receipts.

## Bounds and policies

- 256 incoming commands, at most 16 queued per requester; at most 8 dispatched per 250-ms update.
- At most 256 pending invites and 256 summons, each limited to 40 per requester; maximum 8 accepts and 2 teleport starts per update.
- Invitation deadline 15 seconds from native invite registration; reservation 15 seconds. Summon deadline 40 seconds after dispatch; bounded ingress may add delay. Repeated summon commands do not reset the original deadline.
- Discovery examines at most 128 entries and returns at most 8 candidates per request; at most once per second globally and once per two seconds per requester. No per-slot/per-tick population scan.
- At most 8192 ten-minute receipts, 512 per requester. A full receipt store refuses new operations rather than evicting unexpired idempotency protection. Legacy prep cache also capped at 8192.
- At most 2 gear operations and 32 supply operations globally per second; at most 8 preparation operations per requester per second. Cached acknowledgments do not repeat work. On a rate-limit refusal, wait and deliberately retry with a fresh operation ID; on an unknown/lost result, retry the SAME ID.
- Existing policies observed before implementation: convenience free summon enabled on all three; guild bots enabled only on Wrath; cross-faction grouping enabled only on Classic. These deployed settings are not changed. BG/arena and queued matchmaking candidates are unavailable to recruitment. Convenience summoning does not bypass active matchmaking.

## Verification and remaining limits

`tests/recruitment_regression.py` compiles the actual service implementation with deterministic player/session/native-operation boundaries in all three expansion variants. It covers combat/dead/AFK joining without preparation side effects, transfer deferral/deadlines, replaced/stale invites, competing reservations, human-assistant invitations into bot-led raids, ownership and private alts, faction/queue gates, logout, transport/combat summons, arrival versus initiation, instance mismatch, revival-disabled policy, duplicate/id-conflicting preparation, cancellation, human-first full-group capacity and mixed 40-member raids. Discovery and ingress limits are asserted, including simultaneous submissions from 32 simulated requesters. These are controlled code-path tests, **not a running server or live 40-player load test**.

Full native builds, deployment hashes and live results are recorded in the release handoff separately. Live taxi/worldport, instance lockouts, dead-bot revival, exact gear/supply contents for every class/level, native rituals, native LFG groups, and multiple concurrent real clients still need gameplay verification. The harness stubs native group/teleport/inventory boundaries and does not establish those end-to-end results.

The addon must keep its existing human-role and Keep/Prepare protections. A later addon task may adopt v1 for explicit statuses and replay safety. No claim is made that the core alone now orchestrates an entire party/raid or that existing 0.8.0 understands v1.

Discovery minimum and maximum levels are inclusive. The maximum must not exceed either the configured MaxPlayerLevel or the expansion cap (60 Classic, 70 TBC, 80 Wrath). Malformed/reversed ranges are refused. Existing group members are unaffected.
