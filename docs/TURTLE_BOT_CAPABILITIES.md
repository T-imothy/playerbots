# Turtle bot recovery, incident history and party tactics

These additions belong to the Turtle-native ManTech module. They adapt three useful ideas from the Sagiroth comparison to the existing ManTech AI and native Turtle execution paths. They do not replace the combat engine or import the Sagiroth module. No database migration or additional core hook is required.

## Pursuit progress

Autonomous bots temporarily exclude a hostile creature after 15 seconds without line of sight or measurable pursuit progress. Getting more than 2 metres closer or moving 8 metres resets the timer, allowing pathfinding detours. The exclusion lasts 5 minutes and is limited to 32 target GUIDs per bot. Native pathfinding still owns movement; existing attacker validation and target selection consume the exclusion.

Player-controlled bots, PvP targets and creatures already attacking anyone are exempt. Friendly targets, casting, taxis, transports, charm and transfers do not accumulate failure time. Intentional waits reset pursuit tracking. Map/instance changes, full AI resets and resurrection clear state. Native combat and encounter checks remain in place.

`AiPlayerbot.UnreachableTargetTimeout = 15000` and `AiPlayerbot.UnreachableTargetRetry = 300000` use milliseconds. Set the timeout to `0` to disable this policy. The policy works independently of diagnostic collection.

## Incident history

With `AiPlayerbot.Diagnostics.Mode = 2` and `AiPlayerbot.Diagnostics.Incidents = 1`, each AI observes progress at most once per second:

- `STUCK`: 60 seconds with point-movement intent and no 2-metre displacement.
- `DEAD_LONG`: continuously dead for 120 seconds.
- `ACTION_LOOP`: sustained repetitions of a failing action/target without successful actions or positional progress.
- `UNREACHABLE_TARGET`: the pursuit policy excludes a target.

Ordinary idle, rest and stationary casting are not automatically classified as stuck. These are conservative detectors, not proof of a pathfinding bug or exhaustive coverage of every movement generator. A gap longer than 10 seconds resets observation, and records with no refresh for 90 seconds expire as `telemetry_expired`. Reset/transfer/logout closes records as `observation_reset`; neither label claims verified recovery.

The service retains at most 1024 active incidents and 200 resolved incidents. Overflow is reported explicitly. AI owners submit transitions and 30-second refreshes under a short mutex; file output runs in the existing manager flush, outside AI execution. It appends complete snapshots to `PlayerbotIncidents.log`, rotating at 8 MiB to `.1`. Total file retention is bounded to about 16 MiB. Current incident state is not restored after a restart; retained log files provide bounded historical evidence. There is no new database table or always-running HTTP service.

Set `AiPlayerbot.Diagnostics.Incidents = 0` to disable additional per-bot observations and incident writes. Overall diagnostics mode 0 or 1 also disables them. `PB_DIAG_STATE incidents_enabled` tells consumers whether collection is enabled. This telemetry diagnoses behavior; it does not silently teleport or resurrect bots.

The local diagnostics integration uses the portable assets in `tools/diagnostics/`. It shows active incidents, recent resolutions, raw target IDs and coverage overflow. It rejects incomplete snapshots and marks offline, disabled or old data as historical. It escapes displayed log values and preserves 64-bit target GUIDs as strings.

## Party commands

Select a hostile caster, then enter:

```
.bot action interrupt [request-id]
.bot action cc moon [request-id]
```

CC accepts `star`, `circle`, `diamond`, `triangle`, `moon`, `square`, `cross` or `skull` and uses that party raid marker. IDs are optional, up to 32 ASCII letters, numbers, underscores or hyphens. Generated IDs start with `t`; returned IDs have an `action_` prefix to separate them from recruitment requests.

The existing bounded world-owner recruitment dispatcher processes requests. A request expires after 3 seconds. It revalidates the requester's lifecycle, party, map/instance and current selection/mark. Existing controller, faction, ignore and bot security checks apply. Replaying an ID returns its existing receipt for up to 10 minutes; a different payload with that ID is rejected. These commands are issued once through `.bot`, not broadcast independently to every bot.

The executor checks up to 40 party members and chooses one authorized, living, available bot with a natively castable spell, preferring the nearest and then the lowest GUID. Native spell checks retain ranks, learned abilities, resources, cooldowns, LOS, range, immunities and other cast rules. It attempts only that bot's spell. It does not force a stance change or substitute another caster after a rejected attempt.

Supported interrupts are kick, pummel, shield bash, counterspell, earth shock, silence and feral charge when available. Supported marked CC spells are polymorph, shackle undead, banish, hibernate, sap, repentance and entangling roots. Ground traps and pet-specific CC are not added by this coordinator. A started CC command updates the existing party CC marker strategy so ordinary target protection can follow it.

The response format is:

```
PBACTION 1 action_example interrupt started cast_started;executor=123;spell=456
PBACTION 1 action_example interrupt refused no_ready_bot;executor=0;spell=0
```

`started` means the native casting helper accepted the attempt. It does not claim the spell landed, a crowd control effect survived incoming damage, or a cast was interrupted. Refusal reasons include invalid target, target not casting, no ready bot, native cast rejection, changed target/party/map, expiry, conflicting request ID or queue limits.

## Focused verification

Run `tests/turtle_capabilities_regression.py`, `tests/turtle_progress_integration_regression.py` and `tests/recruitment_regression.py` in a C++17 compiler environment. They compile the actual policies, pursuit hooks, tactical executor and request dispatcher against controlled native fixtures. Existing world-action and recruitment-security regressions cover ownership and authorization. Run `php tools/diagnostics/test-bot-incidents.php tools/diagnostics/mantech-bot-incidents.php` for snapshot parsing.

These fixtures test decisions and boundaries; live gameplay validation is separate. The existing native casting engine determines the eventual combat effect.
