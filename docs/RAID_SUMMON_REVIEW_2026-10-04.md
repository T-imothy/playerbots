# Raid summon save reconciliation — 2026-10-04

The Classic report showed public bots Zanor and Kaler refusing a summon while
Eries and Seno arrived. Read-only live database checks found Zanor (127459) and
Kaler (127544) permanently saved to Molten Core instance 38, alongside Unclebud.
Eries (127742), Seno (127763), Jamary (129866) and Isandra (129920) were saved to
instance 40, alongside Vanillacoke. Both saves have distinct boss progress.
The reporter was offline and the group no longer persisted, so the exact number
of failed bots and the native rejection at that earlier moment cannot be
reconstructed from the available logs. The screenshot's generic refusal does
not identify a native entry reason.

The coordinated human invitation path bypassed `AcceptInvitationAction`, whose
legacy acceptance routine ran `reset raids` to remove off-map bot binds. The
coordinator retained those old saves. Native instance selection prioritizes a
permanent personal save over the group's save, so a public companion can resolve
a different raid copy even after joining the human's raid. The recent October 3
Molten Core movement changes did not edit this invitation/summon path. The
September 23 queue change already reserves intake for a complete 40-person raid;
there is no nine-bot queue limit.

`SummonAction::PrepareRaidBinding` now reconciles a conflicting destination raid
save when a managed invitation succeeds and immediately before an explicit
human summon enters the native teleport path. It applies only to public random
accounts, with a real human requester and shared raid membership, and requires
the group save to match the requester's actual destination instance. It removes
only that destination map's conflicting bot bind at the destination difficulty.
Humans, private alts, unrelated map/difficulty saves, bots already in the
destination map, transfers, full raids and active boss encounters are excluded.
The core's unbind API updates the bot's character database and memory together;
there is no manual SQL migration or live database cleanup.

The existing teleport checks, queue bounds, acknowledged arrival and post-arrival
revival remain in use. A released bind is recorded as `PLAYERBOT_SUMMON` in the
server log. This does not bypass genuine capacity, combat or access failures and
does not transfer bots between two already occupied copies of the same raid.

## Follow-up: companion already inside another copy

After deploying and restarting the first revision, read-only live checks found
Oriano (129047) online in Molten Core with permanent save 27. Vanillacoke (21464)
led group 11, with 40 members and group save 29; the other members' MC saves
matched 29. Restarting does not remove a character's persisted raid bind.

The first revision deliberately excluded bots already on the destination map.
That left a real gap: the coordinator rejected this case as `different_instance`
before any bind reconciliation could run. Native same-map `TeleportTo` uses the
near-teleport path and cannot move a bot between instances; clearing a bind while
still attached to the previous instance is not a safe substitute for departure.
The available evidence does not identify when Oriano originally acquired save 27.

The coordinator now stages an authorized public raid companion's departure to
its existing non-instanced homebind, retaining its original bind during that
worldport. It waits for the native transfer to complete, then performs the normal
explicit summon; the existing reconciliation clears the conflicting destination
bind immediately before entry. Final arrival, resurrection and resource refill
are confirmed in the requested instance, never at the intermediate homebind.
Private characters and dungeon mismatches remain excluded. The destination must
match the shared raid group's save and pass capacity/encounter preflight checks.
There is at most one departure per request, within the existing deadline and
two-transfer-per-tick budget. Membership/session changes cancel the request;
a rejected departure or fallback cannot loop or report arrival.

The production coordinator regression now covers this staged path for all three
core APIs, alive/dead companions, ACK waiting, membership cancellation, rejected
homebinds, full/active raids, mismatched saves, private accounts and fallback.
A mixed one-human/39-bot raid exercises the two-transfer budget and final arrival
with companions both outside MC and inside the wrong MC copy. These controlled
tests do not replace a live 40-person raid test after deployment.

Validation: six regression scripts pass, including the production reconciliation
body for Classic/TBC/Wrath APIs and a one-human/39-bot roster with nine initially
matching saves. Tests also cover private/human saves, another current instance,
missing or mismatching group saves, native capacity/combat checks, repeat calls
and difficulty isolation. Native MSVC syntax checks use each core's actual
headers and compiler definitions. Production binaries are not built or deployed
by this change; live 40-person summon testing remains required.

Deployment: rebuild and deploy Classic, TBC and Wrath from their updated baseline
pins, then restart each world server. No SQL files need to be applied. After
restart, form the raid and summon outside a boss encounter; verify all expected
bots report `arrived (ok)` in the requester's instance, including dead bots.
