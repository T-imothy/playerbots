"""Execute the real numeric aura lookup and Pestilence caller together.

The production crash was hidden by the aura-lookup stub in the combat-policy
test. Keep both production methods here; stub only their core dependencies.
"""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
lookup = block((root / 'playerbot/PlayerbotAI.cpp').read_text(),
               'Aura* PlayerbotAI::GetAura(uint32 spellId,')
spread = block((root / 'playerbot/strategy/deathknight/DKActions.cpp').read_text(),
               'bool CastPestilenceAction::isUseful(')
code = r'''
#define NOMINMAX
#include <windows.h>
#include <cassert>
#include <iostream>
#include <list>
#include <map>
using uint32 = unsigned;
using ObjectGuid = unsigned;
enum SpellEffectIndex { EFFECT_INDEX_0, EFFECT_INDEX_1, EFFECT_INDEX_2 };
struct Aura;
struct Holder {
    ObjectGuid caster = 1;
    int duration = 10000;
    ObjectGuid GetCasterGuid() { return caster; }
    int GetAuraDuration() { return duration; }
    Aura* effects[3]{};
    Aura* GetAuraByEffectIndex(SpellEffectIndex effect) { return effects[effect]; }
};
using SpellAuraHolder = Holder;
struct Aura {
    Holder* holder;
    bool real = true;
    Holder* GetHolder() { return holder; }
};
struct Map {};
struct Unit {
    Map* map = nullptr;
    bool alive = true, world = true;
    float distance = 0;
    std::map<std::pair<uint32, SpellEffectIndex>, Aura*> auras;
    std::map<std::pair<uint32, SpellEffectIndex>, Aura*> extraAuras;
    Aura* GetAura(uint32 spell, SpellEffectIndex effect) { return auras[{spell, effect}]; }
    SpellAuraHolder* GetSpellAuraHolder(uint32 spell, ObjectGuid caster) {
        SpellAuraHolder* found = nullptr;
        for (auto* entries : {&auras, &extraAuras})
            for (auto& entry : *entries)
                if (entry.first.first == spell && entry.second && entry.second->holder &&
                    entry.second->holder->caster == caster) {
                    if (!found) {
                        found = entry.second->holder;
                        for (auto& effect : found->effects) effect = nullptr;
                    }
                    found->effects[entry.first.second] = entry.second;
                }
        return found;
    }
    bool IsAlive() { return alive; }
    bool IsInWorld() { return world; }
    Map* GetMap() { return map; }
    float GetDistance(Unit* other) { return other->distance; }
};
struct Player : Unit {
    bool glyph = false;
    ObjectGuid GetObjectGuid() { return 1; }
    bool HasAura(uint32 id) { return glyph && id == 63334; }
};
bool IsRealAura(Player*, Aura* aura, Unit*) { return aura && aura->real; }
struct PlayerbotAI {
    Player* bot;
    Unit* source = nullptr;
    bool eligible = true;
    std::list<ObjectGuid> targets;
    std::map<ObjectGuid, Unit*> units;
    Aura* GetAura(uint32 spellId, Unit* unit, bool checkIsOwner);
    Unit* GetUnit(ObjectGuid guid) { return units[guid]; }
};
#define AI_VALUE(type, name) (ai->targets)
struct CastSpellAction {
    PlayerbotAI* ai;
    Player* bot;
    bool isUseful() { return ai->eligible; }
    Unit* GetTarget() { return ai->source; }
};
struct CastPestilenceAction : CastSpellAction { bool isUseful(); };
__LOOKUP__
__SPREAD__
int main() {
    SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX);
    Player bot;
    PlayerbotAI ai{&bot};
    Unit source, nearby;
    Map map;
    bot.map = source.map = nearby.map = &map;
    ai.source = &source;
    ai.units[2] = &nearby;
    ai.targets = {2};
    Holder own, other; other.caster = 2;
    Aura mine{&own}, foreign{&other}, noHolder{nullptr};
    CastPestilenceAction action{{&ai, &bot}};
    assert(!ai.GetAura(55078, nullptr, true));
    assert(!ai.GetAura(0, &source, true));
    assert(!ai.GetAura(55078, &source, true));
    // This is the production crash: a disease exists and ownership is checked.
    source.auras[{55078, EFFECT_INDEX_0}] = &mine;
    assert(ai.GetAura(55078, &source, true) == &mine);
    source.auras[{55078, EFFECT_INDEX_0}] = &foreign;
    source.extraAuras[{55078, EFFECT_INDEX_0}] = &mine;
    assert(ai.GetAura(55078, &source, true) == &mine); // Another DK's same-rank aura may be first.
    assert(ai.GetAura(55078, &source, false) == &foreign);
    source.extraAuras.clear();
    for (uint32 spell : {55078u, 55095u}) {
        for (auto effect : {EFFECT_INDEX_0, EFFECT_INDEX_1, EFFECT_INDEX_2}) {
            source.auras.clear();
            source.auras[{spell, effect}] = &foreign;
            assert(!ai.GetAura(spell, &source, true));
            assert(ai.GetAura(spell, &source, false) == &foreign);
            source.auras[{spell, effect}] = &noHolder;
            assert(!ai.GetAura(spell, &source, true));
            source.auras[{spell, effect}] = &mine;
            assert(ai.GetAura(spell, &source, true) == &mine);
            mine.real = false;
            assert(!ai.GetAura(spell, &source, true));
            mine.real = true;
#ifdef MANGOSBOT_TWO
            assert(action.isUseful());
            nearby.auras[{spell, effect}] = &mine;
            assert(!action.isUseful());
            nearby.auras[{spell, effect}] = &foreign;
            assert(action.isUseful());
            nearby.auras.clear();
#else
            assert(!action.isUseful());
#endif
        }
    }
    source.auras.clear();
    source.auras[{55078, EFFECT_INDEX_0}] = &foreign;
    source.auras[{55078, EFFECT_INDEX_2}] = &mine;
    assert(ai.GetAura(55078, &source, true) == &mine);
    ai.targets.clear();
    bot.glyph = true;
    own.duration = 2999;
#ifdef MANGOSBOT_TWO
    assert(action.isUseful());
    own.duration = 3000;
    assert(!action.isUseful());
#endif
    std::cout << "PASS: actual aura ownership lookup and Pestilence integration\n";
}
'''.replace('__LOOKUP__', lookup).replace('__SPREAD__', spread)
with tempfile.TemporaryDirectory(prefix='mantech-aura-owner-') as tmp:
    tmp = Path(tmp)
    (tmp / 'test.cpp').write_text(code)
    for expansion in ('ZERO', 'ONE', 'TWO'):
        subprocess.run(['cl', '/nologo', '/std:c++17', '/EHsc', '/W3',
                        '/DMANGOSBOT_' + expansion, 'test.cpp', '/Fe:test.exe'],
                       cwd=tmp, check=True)
        result = subprocess.run([str(tmp / 'test.exe')], cwd=tmp)
        if result.returncode:
            raise SystemExit(f'{expansion}: failed with exit 0x{result.returncode & 0xffffffff:08X}')
