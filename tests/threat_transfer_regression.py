"""Execute the native-adapter targeting/eligibility code using controlled group objects."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root=Path(__file__).resolve().parents[1]/'playerbot/strategy'
source=(root/'actions/GenericSpellActions.cpp').read_text()
methods='\n'.join(block(source,name) for name in ('Unit* TankThreatTransferAction::GetTarget(', 'bool TankThreatTransferAction::isUseful('))
code=r'''
#include <cassert>
#include <string>
#include <iostream>
struct Map{}; struct Group{};
struct Unit {bool player=false,world=true,alive=true,charmed=false;Map* map=nullptr;Unit* victim=nullptr;
 bool IsPlayer(){return player;}bool IsInWorld(){return world;}bool IsAlive(){return alive;}
 bool HasCharmer(){return charmed;}Map* GetMap(){return map;}Unit* GetVictim(){return victim;}};
struct Player:Unit {Group* group=nullptr;bool tank=false;Player(){player=true;}Group* GetGroup(){return group;}};
struct Value {Unit* target=nullptr;Unit* Get(){return target;}};
struct Context {Value enemy;template<class T>Value* GetValue(std::string){return &enemy;}};
struct PlayerbotAI {Player bot;Context context;Unit* fallback=nullptr;bool eligible=true,ownAura=false;
 bool IsTank(Player* p){return p->tank;}bool HasAura(std::string,Player*){return ownAura;}};
struct CastSpellAction {PlayerbotAI* ai;Player* bot;Context* context;
 CastSpellAction(PlayerbotAI* a):ai(a),bot(&a->bot),context(&a->context){}
 virtual Unit* GetTarget(){return ai->fallback;}virtual bool isUseful(){return ai->eligible;}
 std::string GetSpellName(){return "redirect";}};
struct BuffOnTankAction:CastSpellAction{using CastSpellAction::CastSpellAction;};
struct TankThreatTransferAction:BuffOnTankAction {
 using BuffOnTankAction::BuffOnTankAction;Unit* GetTarget()override;bool isUseful()override;
};
__METHODS__
int main(){
 PlayerbotAI ai;Map map,other;Group group,otherGroup;Player tank,backup,healer;Unit enemy;
 ai.bot.map=tank.map=backup.map=healer.map=enemy.map=&map;
 ai.bot.group=tank.group=backup.group=healer.group=&group;tank.tank=backup.tank=true;
 ai.context.enemy.target=&enemy;enemy.victim=&tank;ai.fallback=&backup;
 TankThreatTransferAction action(&ai);assert(action.GetTarget()==&tank);assert(action.isUseful());
 enemy.victim=&healer;assert(action.GetTarget()==&backup);assert(action.isUseful());
 ai.fallback=&healer;assert(!action.isUseful());ai.fallback=&backup;
 enemy.victim=&tank;tank.group=&otherGroup;assert(action.GetTarget()==&backup);tank.group=&group;
 tank.map=&other;assert(action.GetTarget()==&backup);tank.map=&map;
 tank.alive=false;assert(action.GetTarget()==&backup);tank.alive=true;
 tank.world=false;assert(action.GetTarget()==&backup);tank.world=true;
 tank.charmed=true;assert(!action.isUseful());tank.charmed=false;
 ai.ownAura=true;assert(!action.isUseful());ai.ownAura=false;
 ai.bot.tank=true;assert(!action.isUseful());ai.bot.tank=false;
 ai.bot.charmed=true;assert(!action.isUseful());ai.bot.charmed=false;
 ai.eligible=false;assert(!action.isUseful());ai.eligible=true;
 enemy.victim=nullptr;ai.fallback=&ai.bot;assert(!action.isUseful());
 ai.bot.group=nullptr;assert(!action.GetTarget());assert(!action.isUseful());
 std::cout<<"PASS: actual threat-transfer group/tank/map/life/control/own-aura/base eligibility and current-victim preference\n";
}
'''.replace('__METHODS__',methods)
with tempfile.TemporaryDirectory(prefix='mantech-threat-transfer-') as tmp:
    tmp=Path(tmp)
    (tmp/'test.cpp').write_text(code)
    subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/W4','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
    subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)

strategy=(root/'generic/ClassStrategy.cpp').read_text()
classic=strategy.split('#ifdef MANGOSBOT_ZERO',1)[1].split('#ifdef MANGOSBOT_ONE',1)[0]
tbc=strategy.split('#ifdef MANGOSBOT_ONE',1)[1].split('#ifdef MANGOSBOT_TWO',1)[0]
wrath=strategy.split('#ifdef MANGOSBOT_TWO',1)[1]
assert 'tank threat transfer' not in classic
assert 'misdirection on party tank' in tbc and 'tricks of the trade' not in tbc
assert 'misdirection on party tank' in wrath and 'tricks of the trade' in wrath
print('PASS: combat scheduling excludes unsupported expansion abilities')
