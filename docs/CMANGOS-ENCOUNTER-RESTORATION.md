# CMaNGOS encounter restoration — 2026-09-08

This notice supersedes the native encounter repair claims in earlier audit notes.
CMaNGOS is the authority for dungeon and raid mechanics and encounter data.
Playerbots encounter work must change bot decisions in response to that behavior;
it must not alter boss scripts, spells, timers, phases, targeting or world data
to make a proposed bot response work. Potential native changes belong on the
separate archive branch for review, not on the production baseline.

The complete previous changes and unpublished experiments are preserved on
`archive/native-encounter-audit-20260908` in the core, database and Playerbots forks.
The archive includes `docs/native-encounter-archive/CHANGE-INVENTORY.md` with
79 distinct encounters (43 raid and 36 dungeon encounters across expansions).
The archive is not an approved or validated encounter implementation.

The affected native source is restored byte-for-byte to official CMaNGOS.
Compensating database migrations restore affected encounter rows and bindings;
the superseded experimental migrations are removed from active Updates.
Unrelated class, healing, pulling, loot-policy and portable-vendor changes remain.

Bot responses that depended on removed mechanics are removed: Eadric facing
arbitration, Emalon 25-player distance mitigation, Tyrannus Brand offense/healing
holds, Sindragosa tomb/Backlash spacing and cover, Instability casting holds,
and heroic Garfrost rock-cover selection. Normal Garfrost cover remains.
Other reactions remain gated on actual native objects, spells and auras.

Native-only regression scripts from the earlier audit are historical tests for
the archived implementation, not acceptance criteria for the restored baseline.
The current verification compares restored source with CMaNGOS and exercises
bot damage holds, cover, spreading and cast escapes in all three expansions.
Database migration and exact rollback are rehearsed on temporary tables.
Compilation and those checks do not prove live completion of every encounter.

Do not resume native encounter development as part of the Playerbots audit.
Any later CMaNGOS synchronization must use official upstream revisions and
recheck bot assumptions instead of importing third-party encounter mechanics.

## Reference revisions

- Archived source parent: `49c7eb751e3b6009fa99532b7ebcf3db6f26e530`
- Archive commit: `63c6d129c4fbdce4013c049f5b708198ef277514`
