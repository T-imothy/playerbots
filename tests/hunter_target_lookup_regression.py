import re

from melee_source_wiring import source
from behavior_regression import block
bad=[]
for era in ('MANGOSBOT_ZERO','MANGOSBOT_ONE','MANGOSBOT_TWO'):
 registered=set(re.findall(r'creators\["([^"\n]+)"\]',source('values/ValueContext.h',era)))
 code=source('hunter/HunterActions.cpp',era);header=source('hunter/HunterActions.h',era)
 methods=[block(code,'bool HunterDisengageAction::isUseful'),block(header,'class CastScatterShotOnClosestAttackerTargetingMeAction')]
 if era!='MANGOSBOT_ZERO':methods.append(block(header,'class HunterSnakeTrapAction'))
 for text in methods:
  keys=re.findall(r'AI_VALUE\(Unit\*,\s*"([^"]+)"\)',text)+re.findall(r'GetTargetName\(\)\s*override\s*\{\s*return\s*"([^"]+)"',text)
  assert keys,era
  bad.extend((era,k) for k in keys if k not in registered)
assert not bad, 'Missing target value registrations: '+str(bad)
print('PASS: hunter defensive target lookups resolve to registered values in all expansions')
