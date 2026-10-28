"""Actual Classic/TBC side selection scans past dead/opposite-side players."""
from pathlib import Path
import subprocess,tempfile

root=Path(__file__).resolve().parents[2]
fixture=r'''
#include <cassert>
#include <iostream>
#include <vector>
constexpr unsigned TYPE_GOTHIK=7,IN_PROGRESS=1,SPELL_CHECK_UNRELENTING_SIDE=29875,SPELL_CHECK_SPECTRAL_SIDE=28749;
using SpellEffectIndex=unsigned;
struct Player{bool alive=true,right=false;bool IsAlive(){return alive;}};
struct Ref{Player*p=nullptr;Player*getSource()const{return p;}};
struct Map{struct PlayerList:std::vector<Ref>{using std::vector<Ref>::operator=;bool isEmpty()const{return empty();}}players;PlayerList&GetPlayers(){return players;}};
struct instance_naxxramas{Map*instance;unsigned state=IN_PROGRESS;unsigned GetData(unsigned){return state;}bool IsInRightSideGothikArea(Player*p){return p->right;}};
struct Brain{unsigned attacks=0;void AttackClosestEnemy(){++attacks;}};
struct Unit{instance_naxxramas*instance;Brain brain;Brain*AI(){return &brain;}instance_naxxramas*GetInstanceData(){return instance;}};
struct Creature:Unit{unsigned zones=0;void SetInCombatWithZone(){++zones;}};
struct SpellInfo{unsigned Id;};struct Spell{Unit*caster;SpellInfo*m_spellInfo;Unit*GetCaster(){return caster;}};
struct SpellScript{virtual void OnEffectExecute(Spell*,SpellEffectIndex)const{}};
__METHOD__
int main(){Map map;instance_naxxramas instance{&map};Creature caster;caster.instance=&instance;
 SpellInfo info{SPELL_CHECK_UNRELENTING_SIDE};Spell spell{&caster,&info};CheckGothikSide script;
 Player dead{false,true},wrong{true,false},right{true,true};map.players={{&dead},{&wrong},{&right}};
 script.OnEffectExecute(&spell,0);assert(caster.brain.attacks==1);
 caster.brain.attacks=0;map.players={{&dead},{&wrong}};script.OnEffectExecute(&spell,0);assert(caster.brain.attacks==0);
 info.Id=SPELL_CHECK_SPECTRAL_SIDE;map.players={{&dead},{&right},{&wrong}};script.OnEffectExecute(&spell,0);assert(caster.brain.attacks==1);
 caster.brain.attacks=0;map.players.clear();script.OnEffectExecute(&spell,0);assert(caster.brain.attacks==0);
 instance.state=2;script.OnEffectExecute(&spell,0);assert(caster.brain.attacks==1&&caster.zones==1);
 std::cout<<"PASS actual native Gothik side scan, dead/wrong-side order and open gate\n";
}
'''
for era in ('classic','tbc'):
    source=(root/era/'src/game/AI/ScriptDevAI/scripts/eastern_kingdoms/naxxramas/boss_gothik.cpp').read_text()
    method=source[source.index('struct CheckGothikSide'):source.index('// 28781')]
    with tempfile.TemporaryDirectory(prefix='gothik-native-') as folder:
        p=Path(folder);(p/'test.cpp').write_text(fixture.replace('__METHOD__',method))
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=p,check=True)
        subprocess.run([str(p/'test.exe')],cwd=p,check=True)
# Wrath's native implementation uses HandleOpenGates/assault events, not this script.
wrath=(root/'wotlk/src/game/AI/ScriptDevAI/scripts/northrend/naxxramas/boss_gothik.cpp').read_text()
assert 'struct CheckGothikSide' not in wrath and 'void HandleOpenGates()' in wrath
