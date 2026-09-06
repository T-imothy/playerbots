# Naxxramas native-mechanic audit — partial coverage

Classic/TBC use the level-60 instance; Wrath uses its own difficulty-aware core
scripts. Shared map/creature IDs do not establish identical encounter rules.

## Grobbulus injection and Kel'Thuzad mana burst

All three native `boss_grobbulus.cpp` implementations register aura 28169's
removal script. Expiration casts Embalming Cloud 28322; dispelling casts Mutagen
Explosion 28206. Both create Poison Cloud 28240. Read-only local spell/DBC
verification found 28206 radius index 9 = 20 yards and 28322 index 14 = 8 yards
in each expansion. The AI uses the larger actual burst radius plus two yards.

Classic/TBC's Kel'Thuzad aura script maps 27819 to 27820 and burns 50% mana.
Wrath's `Aura::TriggerSpell` handler burns one-third on normal, half on heroic,
then casts 27820. Its native radius index 13 = 10 yards in all three versions.
The AI only changes positioning; it never modifies the native mana/damage rule.

The new Naxx position value observes those actual aura lifetimes. Carriers
separate from living same-map/phase group members, other bots avoid carriers,
and mixed carrier types use their respective radii. The native active boss tank
keeps its position. The one-second value has at most eight native path checks;
execution also checks the current group positions and hazards before movement.
Expired auras, changed groups/maps/phases, death, charm and teleportation release
the decision. Boss death does not prematurely release a surviving burst aura.
Normal stationary casts and hazard/fissure escapes remain available.

This is burst separation, not complete poison-cloud placement, Grobbulus tank
kiting, Kel'Thuzad Frost Blast/guardian/phase handling or a demonstrated raid clear.

## Harmful automatic dispels

The native dispel implementation randomly selects from eligible auras. It is
therefore unsafe to cast a disease-removing spell on an injected player even
when another disease, poison or magic effect prompted that action.

- The common disease candidate query rejects an injected friendly recipient.
- Automatic spell selection and execution check every native DISPEL effect,
  preserving magic-only/curse-only/poison-only cures that cannot remove disease.
- Party cure values include the intended spell name, so a multi-effect Cleanse
  can select a different safe recipient instead of repeatedly rejecting the first.
  Old type-only value callers remain compatible.
- Immediate periodic disease-removal payloads (Abolish Disease) and native
  cleansing totem 8170 are not newly cast during a live Grobbulus encounter or
  while a same-instance group member still has injection. Wrath's renamed totem
  uses the same ID; its native pulse is not treated as an older-client spell.
- Manual casting stays on its existing native path. No aura, totem, boss spell,
  immunity, damage rule or database row is removed or weakened.

Important remaining limit: a cleansing totem or Abolish Disease applied *before*
the pull can still pulse. The implementation does not retroactively delete such
effects from people. Group leaders must not pre-place/pre-buff those effects for
the current test. Self-immunity/item removals, existing totem lifecycle and any
additional indirect removal paths need separate native review.

## Existing support retained, not invented

Wrath Loatheb uses Necrotic Aura 55593, unlike Classic/TBC's class-specific
Corrupted Mind dispatch. Existing healing actions already inspect the native
healing-percentage modifier and reject a target at -100%. This observation is
not a tested healer-window/rotation coordinator and does not make Loatheb complete.
Existing Naxx activation, Horsemen cleanup and void-zone avoidance are retained.

## Validation and remaining work

Actual-source fixtures compile the position value/action/multiplier, the dispel
policy, party selector and cure triggers for all three expansion defines. They
exercise native mask helpers, mixed radii, fresh invalidated destinations,
native tank victim changes, aura/phase/group lifecycle, multi-effect cures,
legacy qualifier compatibility and periodic/totem prevention. Full native builds
and actual client encounter testing are separate requirements.

All wings still need complete mechanic-by-mechanic review: Anub'Rekhan, Faerlina,
Maexxna, Noth, Heigan, Loatheb, Razuvious, Gothik, Four Horsemen, Patchwerk,
Grobbulus, Gluth, Thaddius, Sapphiron and Kel'Thuzad. Targeted safeguards are not
complete strategies. No new diagnostic file, SQL table, worker or migration is
introduced; the one-second position value is functional AI state.
