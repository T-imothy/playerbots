"""Source-only hunter wiring checks; no C++ compilation or realm startup."""
from pathlib import Path
import re
from melee_source_wiring import source, ROOT
from behavior_regression import block
P=ROOT.parents[1]
results=[]
for era in ('MANGOSBOT_ZERO','MANGOSBOT_ONE','MANGOSBOT_TWO'):
    def src(name):
        s=source(name,era)
        return re.sub(r'//[^\n]*','',re.sub(r'/\*.*?\*/','',s,flags=re.S))
    routes=src('hunter/HunterStrategy.cpp');registry=src('hunter/HunterAiObjectContext.cpp')
    triggers=src('hunter/HunterTriggers.h');actions=src('hunter/HunterActions.h');cpp=src('hunter/HunterActions.cpp')
    base=block(routes,'void HunterStrategy::InitCombatTriggers')
    assert 'new NextAction("arcane shot"' in base and 'new NextAction("equip ammo"' in base
    assert 'new NextAction("mongoose bite"' in base and 'new NextAction("tame beast"' not in routes
    assert 'HunterStingPveStrategy::InitCombatTriggers' in block(routes,'void HunterStingRaidStrategy::InitCombatTriggers')
    assert 'CastScatterShotOnClosestAttackerTargetingMeAction(ai)' in registry
    assert 'HasSpell(19434)' not in triggers and 'black arrow on snare target' not in registry
    assert 'GetMinMaxRange(true)' in src('hunter/HunterCombatPolicy.h')
    assert 'HunterAmmoReserve(ai)' in block(triggers,'class HunterNoAmmoTrigger')
    assert 'HunterAmmoReady(ai)' in block(triggers,'class SwitchToRangedTrigger')
    assert 'new NextAction(reachAction' not in block(actions,'class TrapOnTargetAction')
    assert 'ACTION_THREAT_AOE' in block(actions,'class CastMultiShotAction')
    assert 'ACTION_THREAT_AOE' in block(actions,'class CastVolleyAction')
    assert 'HunterAreaSafe' in block(cpp,'bool CastVolleyAction::isUseful')
    assert 'isUseful() && CastSpellAction::Execute' in block(actions,'class HunterDisengageAction')
    for key in ('hunter wyvern sting','hunter disengage'):
        assert registry.count('creators["'+key+'"]')==2
    for key in ("hunter master's call",'hunter freezing arrow'):
        assert (registry.count('creators["'+key+'"]')==2)==(era=='MANGOSBOT_TWO')
    assert ('creators["snake trap in place"]' in registry)==(era!='MANGOSBOT_ZERO')
    assert ('"hunter recover mana"' in routes)==(era!='MANGOSBOT_ZERO')
    # Every directly registered class in the hunter context must have a declaration
    # in the strategy source tree for that expansion (macro classes included).
    declared='\n'.join(src(str(p.relative_to(P/'playerbot/strategy'))) for folder in ('hunter','triggers','generic','actions') for p in (P/'playerbot/strategy'/folder).glob('*.h'))
    for name in set(re.findall(r'new (Hunter\w+|Cast\w+)\(ai',registry)):
        assert re.search(r'\b'+name+r'\b',declared), (era,name)
    # Changed hunter files must not acquire broken repository-relative includes.
    for p in (P/'playerbot/strategy/hunter').glob('*'):
        if p.suffix not in ('.h','.cpp'):continue
        for include in re.findall(r'#include "(playerbot/[^\"]+)"',p.read_text()):
            assert (P/include).exists(),include
    results.append({'expansion':era,'source_route_checks':'passed','compiled':False,'runtime_tested':False})
    print('PASS source wiring and expansion exclusions:',era)
print('SOURCE CHECKS ONLY: compilation and runtime combat tests remain pending.')
