# Turtle native bot SQL result ownership — 2026-09-21

## Confirmed fault

CMaNGOS Database::Query/PQuery returns std::unique_ptr<QueryResult>. Turtle's API returns an owning raw QueryResult*. The imported native bot module used auto at the call sites, silently changing ownership when compiled against Turtle. The pointers were not deleted on scope exit or replacement.

Turtle QueryResultMysql::NextRow frees its row storage/MySQL result only after reaching the end; it does not delete the wrapper. One-row reads and early returns retain both the wrapper and the MySQL result/Field storage. Repeated pet-health queries are a concrete hot path: PetIsDeadValue::Calculate checks a missing hunter pet at most once per five seconds and reads one row without advancing or deleting the result.

## Runtime evidence

Production PID 4336, 6,000 bots, background_config_pct=10, activity_priorities_disabled=0: private memory rose from 8,771.52 MiB at 13:59:48 to 12,904.55 MiB at 21:06:51 (server log clock). The bot-cache estimate grew from 623.59 to about 817 MiB, insufficient to explain all growth by itself. A separate 4.33-minute memory-history comparison grew 36.59 MiB private; measured navigation growth was 7.46 MiB. Ledgers are partial and overlapping.

The bounded C++ allocation capture sampled at 1/1024 with zero reported allocation/site drops. After recording stopped and the follow-up observation, site stacks through Database::Query -> Database::PQuery -> PetIsDeadValue::Calculate retained two sampled result wrappers (80 bytes). C++ sampling does not measure the associated MySQL DLL allocations and must not be used to claim the total number of bytes this fix will recover. Source ownership tracing confirms the leak independently of sampling. The older DLL could allocate into a separate CRT heap; upgrading it did not correct caller ownership.

Capture artifacts are in the task workspace memory-growth-20260921. The existing HeapSummary operation took about 32 seconds per snapshot; capture-window tick timings are perturbed and excluded from normal performance comparisons. The bounded capture is finished; no restart or persistent configuration changes were made.

## Change

88 synchronous result-producing calls across 24 playerbot source files now immediately take ownership with std::unique_ptr<QueryResult>. This handles early return, empty results, exceptions, full iteration, and replacement. SQL text, parameters, gameplay decisions and scheduling are unchanged. The active cmangos-ahbot implementation already owns its results and was not modified. Async callbacks/SqlQueryHolder keep their existing ownership contracts. Disabled legacy bot/AH modules and the separate CMaNGOS checkout were not modified.

The core diagnostics now export memory.database_query_results from the existing atomic PerfStats::g_totalQueryResults. This is a live-object count, not bytes. It adds one atomic read to the existing memory snapshot and is disabled with the existing diagnostics build/runtime controls.

## Validation and next run

Python tests/query_ownership_audit.py passes: all 95 active synchronous database call sites in playerbot and cmangos-ahbot have explicit ownership. Guard fixtures detect old raw calls, including if initializers; comments are ignored. A separate comparison proved that removing only the 88 ownership wrappers and added includes restores each pre-change file byte-for-byte. Changed-file git diff --check passes. The existing unrelated shared-factory edits have pre-existing whitespace warnings.

No C++ build, deployment, restart, or publication was performed. User builds locally, deploys, and restarts. Then compare the query-result live count and memory slope after 6,000 bots settle with unchanged activity settings. Fixed ownership is established; elimination of all production RAM growth is not yet established. CMaNGOS already has the owning return type and should not receive redundant wrappers without checking its current API.

## Build correction

The user build found an existing separate results_guard in CustomStrategy::LoadActionLines. The first ownership conversion attempted to copy the new unique_ptr into that guard (MSVC C2280). Removed the redundant guard: the result now has exactly one owner. Of the 88 converted calls, this call already had cleanup; 87 lacked explicit ownership. The source audit now rejects this duplicate-guard pattern. Audited all other QueryResult guards/deletes in the active playerbot sources; the remaining delete belongs to the unchanged async DatabasePing callback. User rebuild remains required; no build was run by the assistant.
