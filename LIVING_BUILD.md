# Living TBC build contract

This fork preserves the deployed Playerbots base and Living patch-242 behavior.
The immutable import is `codex/import-living-242`, tagged
`living-baseline-242-20260910`; no newer upstream commits were merged.

The paired application repository owns `dependencies.lock.json` and the explicit
CMaNGOS core-patch manifest. Its Linux validation job prepares the pinned core
`140802b5409bfdaff9c7aad2bd9812d31ba9781a` plus those core patches, then compiles
this fork at the exact lock revision. Core patches do not belong in this fork.

This public repository's credential-free CI compiles actual native policy code
with ASan/UBSan. It is necessary but not sufficient: full paired-realm builds,
native executor tests, isolated integration and gameplay acceptance remain in
the application's release gate. A policy-only green check is not a realm build.

Removed inherited Classic/TBC/WotLK CI assumed the fork owner also owned three
CMaNGOS core repositories. No Discord notifications or production-host runners
are used. The historical workflows remain available in the import baseline.
