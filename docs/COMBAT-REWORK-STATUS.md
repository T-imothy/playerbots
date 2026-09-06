# Combat and summon rework — work in progress

Requested scope: all three ManTech testing cores, class-rotation review and the
full dungeon/raid coverage inventory. Production and ManTech master branches are
not deployment targets. This document is an implementation ledger, **not a
claim that every encounter has been implemented or played successfully**.

## Implemented source changes

### Shared Classic, TBC and Wrath

- Inn summons no longer require a hearthstone or its readiness, apply its
  cooldown, or clear an existing genuine hearth cooldown. Meeting stones retain
  their existing no-hearth behavior. Inn/stone location restrictions remain.
- Bare convenience summons only move the bot, never a real player. Reject
  logout/teleport transitions, combat, charm, taxi and transport contexts rather
  than attaching passengers with incompatible coordinates.
- Check core map admission and the return value of `Player::TeleportTo`.
  Same-map movement does not misuse `Map::CanEnter`, which rejects a player
  already in that map. Same-number/different-instance movement is rejected;
  this does not bypass instance bindings or normal entrance handling.
- Do not clear movement or rewrite stay/guard anchors after a rejected move.
  Acceptance is not completion: a far transfer still needs its normal ACK.
- Existing safe dead-bot revival is deferred until ACK at the intended
  destination. Rejection, fallback location, expiry and duplicate completion
  cannot grant a resurrection. One bounded pending record per AI, not a queue.
- Suppress the misleading missing-stone announcement before trying an inn.
- Explicit warlock summons no longer fail map admission merely because the
  target is already on the warlock's map. Ritual fidelity/reagents remain a
  separate open review item; no new claim of complete native ritual simulation.
- Wire Naxxramas entry in combat/noncombat and exit in noncombat. Correct the
  Horsemen cleanup lookup and use Korth'azz, present in both eras, rather than
  the Classic-only Mograine identifier. This is not a complete Naxx strategy.

### TBC and Wrath

- Assassination Envenom candidate uses the existing combo threshold, learned
  spell/cast rules and the core's own Deadly Poison ownership/family selector.
  Require enough owned doses for the combo points; preserve Eviscerate fallback.

### Wrath only

| Class | New scheduling/behavior |
|---|---|
| Warrior | Register existing Enraged Regeneration action; consider it at low health, retaining native enrage/cooldown requirements. |
| Paladin | Divine Plea at low mana for non-healing roles; Protection Shield of Righteousness through melee/core equipment checks. |
| Hunter | Kill Shot through native target-health, learned-spell, range and cooldown validation. |
| Rogue | Hunger for Blood only with a bleeding target and a learned/ready spell. |
| Priest | Discipline Penance on an injured party member; healing-role Divine Hymn for critical group damage. Channels use the existing casting path. |
| Shaman | Elemental owned Flame Shock and Lava Burst sequence; Enhancement Feral Spirit follows the existing boost policy. |
| Warlock | Destruction Chaos Bolt, owned Haunt for Affliction, Metamorphosis under the existing Demonology boost policy. Remove obsolete Wrath raid Demonic Sacrifice scheduling and restore raid pet maintenance, preferring a learned Felguard. Classic/TBC sacrifice policy is unchanged. |
| Druid | Cat-form/combo-gated Savage Roar; Nourish prefers an owned periodic heal using the same test as our core spell script; Wild Growth for group injury. Restoration form prerequisites and existing heal fallbacks remain. |

Mage/DK donor comparisons are not silently classified as fixed. Their earlier
class-audit corrections remain inherited; further proc/rune/channel policy work
is still open. No DK implementation is added to Classic/TBC. Older DBCs may have
NPC spells with Wrath-like names; that does not enable these player actions.

## Validation completed so far

- Intermediate native x64 RelWithDebInfo builds succeeded for Classic, TBC and
  Wrath. Later edits require a final build of the exact committed revisions.
- Actual-source controlled C++ tests passed for convenience summon rejection,
  admission, owned bot direction, post-ACK revival and duplicate/expired/fallback
  cases; explicit warlock summon eligibility; placement retry/crowd behavior.
- Actual-source predicate tests passed for Envenom dose/ownership, Nourish HoT
  ownership and Lava Burst's owned Flame Shock/core-castability requirement.
- Existing class and combat diagnostics regression suites passed, including the
  Classic/TBC/Wrath diagnostics probes. Static Naxx registration checks passed.
- No new encounter play tests have been performed. No damage/healing gain or
  performance improvement percentage is established by these tests.

## Remaining before the full requested scope is complete

- Boss-by-boss, mechanic-by-mechanic review against each CMaNGOS expansion's
  actual scripts; the earlier inventory is not that complete semantic audit.
- Implement/adapt the Onyxia placeholder strategy, legitimate Netherspite beam
  handling replacing aura shortcuts, remaining MC bosses, and missing Karazhan
  and Mechanar mechanics. Do not remove cheats and falsely call the raid supported.
- Review/implement the other missing raid/dungeon libraries from the complete
  coverage matrix. Preserve normal/heroic, raid-size, expansion, threat, CC,
  movement, admission and spell rules; reject donor boss weakening/aura cheats.
- Resolve remaining class comparison leads (Vigilance/assigned support,
  Misdirection/Tricks, proc and channel clipping, rune/disease policy, etc.) against
  native APIs and actual reachable behavior; do not treat name differences as bugs.
- Final exact-revision builds, matching EXE/PDB checks, dev installation and
  GitHub verification. Keep runtime files stopped/unchanged until installation is
  actually performed and reported. Do not present a partial snapshot as full completion.
- User encounter testing is still required after implementation/build validation.

## Diagnostics and database impact

No new log file, per-bot scan thread or SQL migration is introduced by the changes
listed here. Existing sampled combat diagnostics already observe the new action
names/outcomes. Pending summon revival is functional state, not removable
diagnostic instrumentation. Existing diagnostic caps/lifecycle policy remain.

The 10,000-bot Classic soak was stopped through the normal console signal; the
server logged `Halting process...` at 19:16:48 local on 2026-09-05. Shutdown also
reported existing hunter-trap owner-reference warnings. Those are separate
investigation leads, not proof that the newly edited code caused a crash (it was
not running in that process).
