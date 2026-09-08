# Encounter repair release — 2026-09-08

This is the current status; earlier checkpoint documents are historical.

Confirmed repairs cover Arlokk/C'Thun bindings and Thaddius cleanup in all eras;
Blackheart/Kael target bounds and Gruul target lifetime in TBC/Wrath; and Wrath
Brand, Amanitar, Krystallus, Emalon, Sindragosa, Freya, Hodir helper, Tharon'ja,
Kologarn, Volazj phase/lifetime and Lich King phase-boundary defects. Bot changes
include encounter damage holds, spreading/cover and Tharon'ja form abilities.
Existing class-combat fixes and server-only loot policy are retained.

The combined regression suite passed 189 runners initially; two stale pull test
fixtures were corrected and their runners passed in all three eras. All 191
runners now pass. Native syntax checks passed for the changed encounter and
shared vehicle sources and affected bot sources across applicable expansions.
Full spell binding imports passed on session-local temporary tables: Classic
583 rows, TBC 1,308 and Wrath 2,367. Incremental migrations were tested on
temporary tables, including repeat application. These are source/fixture checks,
not proof of live raid completion or measured performance improvement.

Migration numbering was reconciled with newer published baselines: TBC Arlokk
0022 and C'Thun 0023; Wrath Krystallus 5895. Their earlier draft numbers collided
with already published unrelated migrations. SQL content is unchanged.
Classic's existing portable-vendor migration 4842 was absent from its published
database baseline and is included in history without reapplying vendor changes.

Full builds, publishing, database rollout and file deployment are recorded in
the release manifest and deployment receipts; this source note is not a claim
that those later operations have already succeeded.

## Remaining content and validation

- Full Lich King native encounter phases, platform/realm/outro/NPC systems are
  incomplete in the active core. The separate ICC restoration is not imported.
- Volazj class/spec-based illusion spawning and combat are incomplete native
  content; this release repairs existing phase and lifetime handling only.
- Sindragosa final-phase Asphyxiation timing remains unresolved between primary
  emulator references. No arbitrary timer was introduced.
- Complete live tank/healer/DPS, difficulty and event/escort/vehicle coverage
  remains in the saved encounter audit matrix, including real-room pathing,
  Sindragosa tomb/cover collision, Kologarn exit landing and overlapping mechanics.
- Representative bot-load CPU, update time and memory measurements remain open.

These missing systems and live checks are not marked completed by this release.
