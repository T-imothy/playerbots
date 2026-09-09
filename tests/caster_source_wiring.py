"""Caster source wiring/expansion checks; does not compile or execute combat."""
from pathlib import Path
import re,collections
from types import SimpleNamespace
from behavior_regression import block
from melee_source_wiring import source
P=Path(__file__).resolve().parents[1]
h=SimpleNamespace(PB=P,block=block)
def src(path,era):return source(path,era)
stage=P
results=[]
for era in ('MANGOSBOT_ZERO','MANGOSBOT_ONE','MANGOSBOT_TWO'):
 registries={c:src(c+'/'+c.title()+'AiObjectContext.cpp',era) for c in ('mage','warlock','priest','druid','shaman')}
 extras={'mage':['arcane barrage','focus magic','slow'], 'warlock':['demonic empowerment','shadowflame','demonic circle: summon','immolation aura','shadow cleave','demon charge'], 'priest':['mind sear','psychic horror'], 'druid':['force of nature','cyclone','typhoon'], 'shaman':['elemental mastery','hex','thunderstorm','fire elemental totem','earth elemental totem']}
 for cls,s in registries.items():
  assert s.count('creators["caster fallback"]')==2
  for kind in ('Trigger','Action'):
   m=re.search(r'class \w+\s*:\s*public NamedObjectContext<'+kind+r'>\s*\{',s)
   b=h.block(s[m.start():],m[0]); keys=re.findall(r'creators\["([^"]+)"\]',b)
   duplicate=[k for k,v in collections.Counter(keys).items() if v>1 and (cls,kind,k)!=('druid','Action','hibernate')]
   assert not duplicate,(era,cls,kind,duplicate)
  for name in extras[cls]:
   expected= era=='MANGOSBOT_TWO' or name=='elemental mastery' or (era=='MANGOSBOT_ONE' and name in ('slow','force of nature','cyclone','fire elemental totem','earth elemental totem'))
   assert s.count('creators["'+name+'"]')==(2 if expected else 0),(era,cls,name)
  # Every new caster route needs both factories in this exact expansion.
  folder=h.PB/'playerbot/strategy'/cls
  for p in folder.glob('*Strategy.cpp'):
   text=src(cls+'/'+p.name,era)
   for name in re.findall(r'new TriggerNode\("([^"]+)"',text):
    if name.startswith('caster ') or name in extras[cls] or name in ('health funnel','fel domination','hellfire','recover demon','stop unsafe health channel','demonic circle: teleport'):
     assert 'creators["'+name+'"]' in s,(era,cls,p.name,name)
  # Include paths in modified contexts must resolve in the overlay or source.
  for inc in re.findall(r'#include "(playerbot/[^"]+)"',s):
   assert (stage/inc).exists() or (h.PB/inc).exists(),inc
 mage=src('mage/ArcaneMageStrategy.cpp',era)
 assert 'new NextAction("arcane power"' not in h.block(mage,'void ArcaneMageBuffStrategy::InitCombatTriggers')
 assert 'new NextAction("arcane power"' in h.block(mage,'void ArcaneMageBoostStrategy::InitCombatTriggers')
 cold=h.block(src('mage/MageTriggers.h',era),'class ColdSnapTrigger')
 assert '12472' not in cold and '11958' not in cold and '"cold snap"' in cold
 drain=h.block(src('warlock/WarlockTriggers.cpp',era),'bool DrainSoulTrigger::IsActive')
 assert ('25.0f' in drain)==(era=='MANGOSBOT_TWO')
 assert 'item' in drain and '6265' in drain
 conflagrate=h.block(src('warlock/WarlockTriggers.cpp',era),'bool ConflagrateTrigger::IsActive')
 assert ('56235' in conflagrate)==(era=='MANGOSBOT_TWO')
 assert '7000' in conflagrate
 actions=src('CasterCombatActions.h',era)
 assert ('bot->GetGameObject(48018)' in actions)==(era=='MANGOSBOT_TWO')
 assert ('bot->HasAura(63165)' in actions)==(era=='MANGOSBOT_TWO')
 assert 'CasterControlAvailable' in actions and 'pet target' in actions and 'GetTargetQualifier() override' in actions
 assert 'CasterPersonalDot(spell)' in src('triggers/GenericTriggers.h',era)
 assert 'attacker without my aura' in src('triggers/GenericTriggers.cpp',era)
 assert 'attacker without my aura' in h.block(src('actions/GenericSpellActions.h',era),'class CastRangedDebuffSpellOnAttackerAction')
 results.append({'expansion':era,'source_wiring':'passed','compiled':False,'runtime_tested':False})
 print('PASS staged caster source checks:',era)
print('SOURCE CHECKS ONLY: C++ compilation and gameplay testing remain pending.')
