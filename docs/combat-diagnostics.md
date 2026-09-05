# Temporary combat and class-behavior diagnostics

Implemented on `playerbot-behavior-enhancements`, across Classic/TBC/Wrath. Disabled in distributed defaults; enable only for bounded investigations. No SQL migration, combat decision change, extra CheckCast invocation, forced spell cast, target selection or automatic gameplay test is added.

## Configuration

Requires `AiPlayerbot.Diagnostics.Mode` greater than zero; uses its existing `Interval` and manager-thread flush. These settings are loaded with the bot configuration; restart is the verified activation workflow.

| Key after `AiPlayerbot.CombatDiagnostics.` | Default | Meaning |
|---|---:|---|
| Enabled | 0 | Independent on/off switch; turn off when investigation ends. |
| SampleRate | 16 | One in N eligible observation points per worker thread. Minimum 1. This is deterministic sampling, not a statistical guarantee. |
| ClassMask | 4094 | Bit `1 << classId`; e.g. warrior 2, priest 32, warlock 512. Default covers supported class IDs; older realms do not gain DKs. |
| TraceBot | 0 | If nonzero, that bot GUID bypasses sampling and gets detail (still subject to class and interval limits). Other bots remain sampled for summaries. Zero uses sampled detail from GUIDs divisible by 256. |
| MaxKeys | 2048 | Distinct summary buckets per flush; clamped to 16–4096. Overflow is counted. |
| MaxTraces | 128 | Detail records per flush; clamped to 0–1024. Overflow is counted; sequences may therefore be incomplete. |
| MaxFileMB | 8 | Per-file size limit, clamped to 1–64 MiB. One rotated generation retained. |

Outputs are `LogsDir/PlayerbotCombat.log` and `.log.1`. Default total retention is at most 16 MiB. Rotation removes the previous `.1` generation, not any game data. Do not store this file indefinitely expecting a complete history.

## Interpretation

`PB_COMBAT_WINDOW`: expansion, sampling, selected trace bot, dropped-key and dropped-trace counts. `completion_observed=0` is explicit: this facility does not observe spell completion, damage, healing or whether an effect landed.

`PB_COMBAT_COUNT`: sampled counts by class, exact level, coarse tank/healer/ranged/melee role, combat state, action/source, stage, spell ID and result. Noncombat records are deliberate: conjuring, learning/capability checks and utility actions also changed in the audits. Counts are not exact population attempt totals; detailed trace bots are intentionally oversampled. Do not add stages together as if each were a separate cast.

Stages:

- `action_execute`: existing engine execution result (1 true, 0 false). It is action-level success, not proof of damage or a completed spell.
- `action_impossible`, `action_useless`, `action_unknown`, `suppressed_impossible`, `suppressed_failed`: existing engine decisions, not new failure detection.
- `spell_check`: observes the existing unit-target `CanCastSpell` result output, including core `CheckCast` when that path is reached. Raw enum and the core's result-name formatter are recorded. -1 means no result was written. Some raw failures such as moving/facing are intentionally tolerated by the existing wrapper; the raw result is not its boolean return. The original caller's result output is preserved.
- `cast_wrapper_result`: normal `CastSpellAction` wrapper's boolean result and selected spell ID, where that implementation is used. This means the wrapper reported success/failure, not that effects completed. Overrides/custom actions can instead be visible through engine/check records; do not interpret absence as missing capability.

`PB_COMBAT_TRACE`: observation sequence number, monotonic time, bot GUID, map/instance and the above fields. The actual spell-check unit target is recorded as self/pet/other_unit, with raw GUID, core reaction rank and distance when on the same map. Engine-only/wrapper-result records intentionally say `none_or_unobserved`; no target is guessed or reevaluated. Thread-local action context associates spell checks with the engine action when available; direct calls are labeled `outside_engine_action`.

## Coverage and gaps

Use action/spell buckets to identify which corrected abilities actually ran. Missing buckets mean **not observed**, not passed or broken. Examine eligible population, samples and dropped counts before drawing conclusions. Targeted GUID traces can expose flee/approach loops and repeated invalid selections without chat spam, but must be interpreted with their sampling/drop limits.

This captures autonomous bots, not just companions with a human tester. It does not automatically create talent/level/target conditions, observe all GameObject-target cast paths, prove dungeon mechanics, or record full per-fight DPS/healing. Spell completion/effect telemetry is not implemented and must not be claimed. A real scenario is still needed to exercise each ability.

## Cost, safety and removal register

Disabled mode exits before bot context, formatting, locks or file I/O (the small action-context guard also remains). Enabled mode adds sampled role/context reads, bounded strings, a shared buffer mutex and periodic I/O. Worker threads do not write files; no SQL writes are added. Snapshot/flush memory remains bounded, including the batch being written. Measure enabled-versus-disabled overhead before making this a production default.

Final disposition: disable `CombatDiagnostics.Enabled` when the audit is complete, retain opt-in troubleshooting only if useful. If removing implementation later, remove `CombatDiagnostics.{h,cpp}`, `CombatSpellCheck` and its unit-target hook in PlayerbotAI, Engine context/outcome hooks, GenericSpellActions wrapper hook, PlayerbotDiagnostics flush hook, the seven config fields/parser entries/defaults in all three config templates, and `tests/combat_diagnostics_regression.py`. Remove retained log files only after preserving any evidence still needed. Do not remove game spell validation or behavior fixes along with instrumentation.

Regression harness covers off mode, class filters, sampling, nested action contexts, preservation of written/unwritten spell results, bounded keys/traces, flush clearing and file rotation in all three expansion variants. Full realm builds and a running log smoke test are separate requirements.
