# Shared bot registration tables

The native module previously constructed the same common action, trigger, value and strategy creator maps for each bot. These registrations contain names and actor-independent creation functions, not bot state. With thousands of bots, the repeated map nodes, strings and function wrappers consume substantial memory.

Twelve common contexts now opt into one immutable registration table per concrete context type. C++ static initialization publishes it once, including concurrent first callers. Each context keeps its own created-object cache, actor-specific values, reset/erase behavior, mutex and optional registration overrides. Class-specific and dynamic factory registrations remain unchanged.

Validation: a regression using the production factory/context classes passed concurrent initialization, distinct actor objects, qualifiers, unsupported keys, reset/erase, local overrides, separate registry types and retry after initialization failure. An MSVC Release allocation fixture with 200 contexts and 1,500 registrations allocated 47,400,000 bytes without sharing versus 40,000 bytes after the shared table was initialized. These are controlled allocation totals, not a production RAM measurement. Full native Release build passed; CTest has no registered tests in this configured build.

This removes demonstrated duplication. It does not establish the cause of all post-Arch4 growth, guarantee an 8–10 GB working set, or change bot activity. Production RAM and growth need checking after restart. Includes the already integrated upstream changes through 4120aa9d.

## Class-specific follow-up

A further 118 class-specific contexts now share immutable registrations using the same opt-in mechanism. The ten class source files contain 2,088 registrations in total; each bot only uses its own class. Constructor flags, callback bodies, conditional compilation, per-bot caches and mutable actions/triggers/strategies are preserved. Death-knight source is kept consistent but does not enable that class in Turtle.

The regression additionally checks identical short context names in different class namespaces and independent actors within one class. A token comparison against pre-change files verified that only sharing wrappers and whitespace changed. Production Release build validation is recorded in the local build log.

Runtime observation before this follow-up: PID 1504 retained 6,000 players. Between the two captured snapshots (6.9 minutes), resident memory rose from 9.377 to 9.655 GiB and private bytes from 9.906 to 10.225 GiB, while tracked nav-tile bytes fell about 27.9 MiB and creature/item counts fell slightly. This does not attribute the growth to any specific cache or prove a leak. Sharing class registrations targets fixed per-bot duplication, not this unresolved growth. No intrusive heap capture or production restart was performed.
