"""Source-only melee wiring checks. Does not compile, start a realm or claim runtime coverage."""
from pathlib import Path
import re
from behavior_regression import block

ROOT = Path(__file__).resolve().parents[1] / 'playerbot/strategy'

def source(path, era):
    text = (ROOT / path).read_text()
    active = True
    stack = []
    output = []
    def condition(expr):
        expr = re.sub(r'defined\s*\(?\s*(\w+)\s*\)?', lambda m: str(m[1] in (era, 'CMANGOS')), expr)
        expr = re.sub(r'\b[A-Za-z_]\w*\b', lambda m: m[0] if m[0] in ('True', 'False') else str(m[0] in (era, 'CMANGOS')), expr)
        expr = expr.replace('&&', ' and ').replace('||', ' or ').replace('!', ' not ')
        assert re.fullmatch(r'[\s()TrueFalsandornt01]+', expr), expr
        return bool(eval(expr, {'__builtins__': {}}, {}))
    for line in text.splitlines():
        match = re.match(r'\s*#(ifdef|ifndef|if|elif|else|endif)\b\s*(.*)', line)
        if not match:
            if active: output.append(line)
            continue
        kind, expr = match.groups()
        expr = expr.split('//')[0].strip()
        if kind in ('ifdef', 'ifndef', 'if'):
            enabled = condition(expr)
            if kind == 'ifndef': enabled = not enabled
            stack.append([active, enabled])
            active = active and enabled
        elif kind == 'elif':
            parent, taken = stack[-1]
            enabled = not taken and condition(expr)
            stack[-1][1] |= enabled
            active = parent and enabled
        elif kind == 'else':
            parent, taken = stack[-1]
            active = parent and not taken
        else:
            active = stack.pop()[0]
    assert not stack
    return '\n'.join(output)

def method(path, name, era):
    return block(source(path, era), name)

for era in ('MANGOSBOT_ZERO', 'MANGOSBOT_ONE', 'MANGOSBOT_TWO'):
    fury = method('warrior/FuryWarriorStrategy.cpp', 'void FuryWarriorAoeStrategy::InitCombatTriggers', era)
    assert '"whirlwind"' in fury
    assert ('"sweeping strikes"' in fury) == (era == 'MANGOSBOT_ONE')
    rogue_combat = method('rogue/CombatRogueStrategy.cpp', 'void CombatRogueBoostStrategy::InitCombatTriggers', era)
    rogue_idle = method('rogue/CombatRogueStrategy.cpp', 'void CombatRogueBoostStrategy::InitNonCombatTriggers', era)
    assert '"adrenaline rush"' in rogue_combat and '"adrenaline rush"' not in rogue_idle
    assert ('"killing spree"' in rogue_combat) == (era == 'MANGOSBOT_TWO')
    enhancement = method('shaman/EnhancementShamanStrategy.cpp', 'void EnhancementShamanStrategy::InitCombatTriggers', era)
    assert ('"shamanistic rage"' in enhancement) == (era != 'MANGOSBOT_ZERO')
    assert ('"maelstrom lightning"' in enhancement) == (era == 'MANGOSBOT_TWO')
    assert ('"lava lash"' in enhancement) == (era == 'MANGOSBOT_TWO')
    nova = method('shaman/ShamanActions.h', 'class CastFireNovaAction', era)
    assert ('"fire nova totem"' in nova) == (era != 'MANGOSBOT_TWO')
    assert 'TOTEM_SLOT_FIRE' in nova and 'SafeMeleeTargetCount' in nova
    cat_boost = method('druid/DpsFeralDruidStrategy.cpp', 'void DpsFeralDruidBoostStrategy::InitCombatTriggers', era)
    assert ('"berserk"' in cat_boost) == (era == 'MANGOSBOT_TWO')
    cc = method('druid/DpsFeralDruidStrategy.cpp', 'void DpsFeralDruidCcStrategy::InitCombatTriggers', era)
    assert ('"maim"' in cc) == (era != 'MANGOSBOT_ZERO')
    rogue = source('rogue/RogueAiObjectContext.cpp', era)
    assert ('return new CastShadowDanceAction' in rogue) == (era == 'MANGOSBOT_TWO')
    assert ('return new CastShivAction' in rogue) == (era != 'MANGOSBOT_ZERO')
    assert ('return new CastDeadlyThrowAction' in rogue) == (era != 'MANGOSBOT_ZERO')
    assert ('new CastSafeMeleeAreaAction(ai, "fan of knives"' in rogue) == (era == 'MANGOSBOT_TWO')
    powershift = method('druid/DruidTriggers.h', 'class PowershiftTrigger', era)
    assert ('"furor"' in powershift) == (era != 'MANGOSBOT_TWO')
    paladin = source('paladin/PaladinActions.h', era)
    assert ('return "hand of freedom"' in paladin) == (era == 'MANGOSBOT_TWO')
    assert 'ret seal recovery' in paladin and 'GetAuraApplyMSTime' in paladin
    assert 'ret seal recovery' in method('paladin/RetributionPaladinStrategy.cpp', 'void RetributionPaladinStrategy::InitCombatTriggers', era)
    print('PASS source routes and expansion guards:', era)

triggers = (ROOT / 'triggers/TriggerContext.h').read_text()
for level in ('light', 'medium', 'high', 'very high'):
    line = next(line for line in triggers.splitlines() if 'creators["melee ' + level + ' aoe"]' in line)
    assert 'new Melee' in line and 'new Ranged' not in line
policy = (ROOT / 'MeleeCombatPolicy.h').read_text()
assert 'possible targets no los' in policy and 'HasBreakableByDamageCrowdControlAura' in policy
assert 'IsCcTarget' in policy and 'IsWithinDistInMap(unit, radius)' in policy and 'IsWithinLOSInMap' in policy
actions = (ROOT / 'actions/MeleeAbilityActions.h').read_text()
assert 'GetAura(53817, bot)' in actions and 'GetStackAmount() >= 5' in actions
assert 'return isUseful() && CastSpellAction::Execute(event)' in actions
engine = (ROOT / 'Engine.cpp').read_text()
assert 'float(ACTION_MOVE + 1)' in engine and 'prerequisiteRelevance + 0.01' in engine
assert 'existing->second.readiness == GetFailureReadiness(action)' in engine
assert engine.index('IsExplicitPlayerCommand(action, event)', engine.index('bool Engine::IsFailureBackedOff')) < engine.index('actionFailures.find', engine.index('bool Engine::IsFailureBackedOff'))
assert 'new NextAction("empower weapon"' not in (ROOT / 'deathknight/FrostDKStrategy.cpp').read_text()
assert 'new NextAction("pestilence", ACTION_HIGH + 2)' in (ROOT / 'deathknight/GenericDKStrategy.cpp').read_text()
for path in [ROOT / 'MeleeCombatPolicy.h', ROOT / 'actions/MeleeAbilityActions.h']:
    text = path.read_text()
    assert not re.search(r'(?<!::)\b(?:BOT_STATE_COMBAT|ACTION_THREAT_AOE)\b', text)
    assert not re.search(r'CanCastSpell\([^,\n]+,\s*(?:bot|target)\)', text)
print('PASS shared source guards, active proc selection, native action keys and scoped APIs')
print('SOURCE CHECKS ONLY: C++ compilation and runtime combat tests remain pending.')
