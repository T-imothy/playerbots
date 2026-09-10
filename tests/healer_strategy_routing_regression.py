"""Compile actual healer strategy initialization and inheritance in all eras.
The game-independent trigger container is mocked; this is not live combat.
"""
import re,subprocess,tempfile
from pathlib import Path
from behavior_regression import block
PB=Path(__file__).resolve().parents[1]
def preprocess(text,mode):
    active=True;stack=[];out=[]
    for line in text.splitlines():
        m=re.match(r'\s*#(ifdef|ifndef|if|elif|else|endif)\b\s*(.*)',line)
        if not m:
            if active:out.append(line)
            continue
        kind,expr=m.groups();expr=expr.split('//')[0].strip()
        negate=expr.startswith('!defined(')
        if negate:expr=expr[1:]
        expr=re.sub(r'^defined\((\w+)\)$',r'\1',expr)
        if kind in ('ifdef','ifndef','if'):
            assert expr in ('MANGOSBOT_ZERO','MANGOSBOT_ONE','MANGOSBOT_TWO','GenerateBotHelp'),expr
            condition=expr==mode
            if negate:condition=not condition
            if kind=='ifndef':condition=not condition
            stack.append([active,condition]);active=active and condition
        elif kind=='elif':
            assert expr in ('MANGOSBOT_ZERO','MANGOSBOT_ONE','MANGOSBOT_TWO','GenerateBotHelp'),expr
            parent,taken=stack[-1];condition=not taken and ((expr!=mode) if negate else (expr==mode))
            stack[-1][1]|=condition;active=parent and condition
        elif kind=='else':
            parent,taken=stack[-1];active=parent and not taken;stack[-1][1]=True
        else:active=stack.pop()[0]
    assert not stack
    return '\n'.join(out)

specs=['HolyPriest','DisciplinePriest','HolyPaladin','RestorationShaman','RestorationDruid']
for era,define in enumerate(('MANGOSBOT_ZERO','MANGOSBOT_ONE','MANGOSBOT_TWO')):
 funcs={};contexts={}
 for cls in ('priest','paladin','shaman','druid'):
  contexts[cls]=preprocess((PB/f'playerbot/strategy/{cls}/{cls.capitalize()}AiObjectContext.cpp').read_text(),define)
  for path in (PB/f'playerbot/strategy/{cls}').glob('*Strategy.cpp'):
   text=preprocess(path.read_text(),define)
   for m in re.finditer(r'void (\w+::Init(?:Combat|NonCombat|Reaction|Dead)Triggers)\([^)]*\)\s*\{',text):
    assert m[1] not in funcs
    funcs[m[1]]=block(text[m.start():],m[0])
 needed={}
 def collect(name):
  if name in needed:return
  body=funcs.get(name,'void '+name+'(std::list<TriggerNode*>& triggers) {}')
  needed[name]=body
  for call in re.findall(r'(\w+::Init\w+Triggers)\(triggers\)',body):collect(call)
 roots=[]
 for spec in specs:
  for mode in ('Pve','Raid','Pvp'):
   for state in ('Combat','NonCombat'):
    names=[spec+suffix+mode+'Strategy::Init'+state+'Triggers' for suffix in ('','Buff','Boost','Aoe','Cure')]
    names=[n for n in names if n in funcs]
    for n in names:collect(n)
    roots.append((spec,mode,state,names))
 code=r"""
#include <cassert>
#include <list>
#include <vector>
#include <string>
#include <cstdarg>
#include <iostream>
enum { ACTION_IDLE=1,ACTION_NORMAL=10,ACTION_HIGH=20,ACTION_MOVE=30,ACTION_INTERRUPT=40,ACTION_DISPEL=50,ACTION_LIGHT_HEAL=60,ACTION_MEDIUM_HEAL=70,ACTION_CRITICAL_HEAL=80,ACTION_EMERGENCY=90,ACTION_PASSTROUGH=100 };
struct NextAction {std::string name;float priority; NextAction(const char*n,float p):name(n),priority(p){} static std::vector<NextAction*> array(int count,...){std::vector<NextAction*> r;va_list a;va_start(a,count);while(auto p=va_arg(a,NextAction*))r.push_back(p);va_end(a);return r;}};
struct TriggerNode {std::string name;std::vector<NextAction*> actions;TriggerNode(const char*n,std::vector<NextAction*>a):name(n),actions(a){}};
struct BotAI {void* GetBot(){return nullptr;}} botAI;BotAI* ai=&botAI;
struct RandomMgr {bool IsRandomBot(void*){return false;}} sRandomPlayerbotMgr;
bool has(const std::list<TriggerNode*>&t,std::string action,std::string trigger=""){for(auto n:t)if(trigger.empty()||n->name==trigger)for(auto a:n->actions)if(a->name==action)return true;return false;}
void clear(std::list<TriggerNode*>&t){for(auto n:t){for(auto a:n->actions)delete a;delete n;}t.clear();}
"""
 flatten=lambda s:re.sub(r'(\w+)::(Init\w+Triggers)',r'\1_\2',s)
 code+='\n'.join('void '+flatten(n)+'(std::list<TriggerNode*>& triggers);' for n in needed)
 code+='\n'+'\n'.join(flatten(b) for b in needed.values())+'\nint main(){std::list<TriggerNode*> t;\n'
 def require(action,trigger='',expected=True):
  global code
  code+='assert('+('' if expected else '!')+'has(t,"'+action+'","'+trigger+'"));\n'
 for spec,mode,state,names in roots:
  code+='clear(t);\n'+''.join(flatten(n)+'(t);\n' for n in names)
  if spec=='RestorationShaman':
   require('earth shield on party tank',expected=era>0)
   require('riptide','critical health',era==2)
   require('riptide on party','party member critical health',era==2)
   require('chain heal','medium aoe heal')
   require('lesser healing wave on party','party member critical health')
   require('tidal force',expected=era==2 and state=='Combat')
  if spec in ('RestorationShaman','RestorationDruid'):
   require("nature's swiftness heal",'critical health');require("nature's swiftness heal on party",'party member critical health')
  if spec=='RestorationDruid':
   require('lifebloom','lifebloom',era>0)
   require('wild growth on party','medium aoe heal',era==2)
   require('nourish on party','party member low health',era==2)
  if spec in ('HolyPriest','DisciplinePriest'):
   require('binding heal','party member critical health',era>0)
   require('prayer of mending',expected=era>0)
   require('hymn of hope',expected=era==2 and state=='Combat')
   require('flash heal','critical health')
  if spec=='DisciplinePriest':
   require('penance on party','party member critical health',era==2)
   require('penance','critical health',era==2)
  if spec=='HolyPriest':require('guardian spirit on party','party member critical health',era==2 and state=='Combat')
  if spec=='HolyPaladin':
   require('beacon of light',expected=era==2);require('sacred shield',expected=era==2)
 code+='clear(t);std::cout<<"PASS strategy routing: five healing specs, PvE/dungeon, raid, PvP, combat/noncombat\\n";}\n'
 for cls,keys in {'shaman':["nature's swiftness","nature's swiftness heal","nature's swiftness heal on party"],'druid':["nature's swiftness heal","nature's swiftness heal on party"]}.items():
  for key in keys:assert 'creators["'+key+'"]' in contexts[cls]
 for cls,keys in {'priest':['guardian spirit','hymn of hope','stop hymn of hope'],'paladin':['beacon of light','sacred shield','aura mastery'],'shaman':['tidal force']}.items():
  for key in keys:assert ('creators["'+key+'"]' in contexts[cls])==(era==2)
 with tempfile.TemporaryDirectory(prefix='healer-routes-') as tmp:
  p=Path(tmp);(p/'test.cpp').write_text(code)
  r=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,capture_output=True,text=True)
  if r.returncode:raise RuntimeError(r.stdout+r.stderr)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
 shaman=(PB/'playerbot/strategy/shaman/RestorationShamanStrategy.cpp').read_text()
 assert 'ACTION_NODE_A(earthliving_weapon, "earthliving weapon", "flametongue weapon")' in shaman
print('PASS expansion registration gates and weapon fallback')
