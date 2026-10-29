"""Native-interface fixtures for the actual Classic room defense selector."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block

def run(source,role_code):
    code=role_code.replace('#include <algorithm>', '#include <algorithm>\n#include <cmath>\n#include <set>')
    code=code.replace('unsigned guid=0,entry=0,map=469,instance=1;', 'float x=0,hp=100;Unit* controlled=nullptr;Unit* GetCharm(){return controlled;}float GetHealthPercent(){return hp;}\n unsigned guid=0,entry=0,map=469,instance=1;')
    code=code.replace('float GetDistance(Unit*){return 10;}', 'float GetDistance(Unit*u){return std::fabs(x-u->x);}')
    code=code.replace('bool tank=false,healer=false,ranged=false,transfer=false;', 'bool CanAttack(Unit*u){return u->valid;}bool tank=false,healer=false,ranged=false,transfer=false;')
    code=code.replace('Player* GetBot(){return bot;}', 'PlayerbotAI* GetAiObjectContext(){return this;}bool movable=true;bool CanMove(){return movable;}Player* GetBot(){return bot;}')
    code=code.replace('virtual bool IsPlayer()const', 'bool HasFlag(unsigned,unsigned){return !valid;}virtual bool IsPlayer()const')
    code=code.replace('struct Unit{virtual', 'struct Combat{bool evade=false;bool IsInEvadeMode()const{return evade;}};\nstruct Unit{Combat state;const Combat& GetCombatManager()const{return state;}virtual')
    code=code.replace('struct PossibleAttackTargetsValue{', 'struct PossibleAttackTargetsValue{static bool IsCcTarget(Unit*u,Player*){return u->cc;}')
    code=code.replace('Unit* RazorgoreDefenseTarget(PlayerbotAI*,bool& active){active=false;return nullptr;}\nbool RazorgoreEggPhase(PlayerbotAI*){return false;}Unit* RazorgoreCreature(Unit*,unsigned){return nullptr;}', r'''
using AiObjectContext=PlayerbotAI;using WorldObject=Unit;using Creature=Unit;struct GameObject:Unit{};
enum{UNIT_FIELD_FLAGS=0,UNIT_FLAG_NOT_ATTACKABLE_1=1,UNIT_FLAG_UNTARGETABLE=2,UNIT_FLAG_UNINTERACTIBLE=4};
struct MeleeCcCheck{MeleeCcCheck(PlayerbotAI*){}bool Protected(Unit*u){return u->cc;}};
bool eggPhase=true;Unit* dragon=nullptr;GameObject* orb=nullptr;std::list<Unit*> room;
Unit* RazorgoreDefenseTarget(PlayerbotAI*,bool&);bool NeedsRazorgoreControllerHealing(PlayerbotAI*,Unit*);
bool RazorgoreEggPhase(PlayerbotAI*a){auto*b=a->bot;return eggPhase&&b->world&&b->alive&&b->map==469&&!b->transfer&&!b->charm&&!a->real&&b->group;}
Unit* RazorgoreCreature(Unit*,unsigned){return dragon;}
std::vector<GameObject*> RazorgoreObjects(Unit*,unsigned){return orb?std::vector<GameObject*>{orb}:std::vector<GameObject*>{};}
namespace MaNGOS{
struct AnyUnitInObjectRangeCheck{Unit* center;float range;AnyUnitInObjectRangeCheck(Unit*c,float r):center(c),range(r){}};
template<class T>struct UnitListSearcher{std::list<Unit*>&out;T&check;UnitListSearcher(std::list<Unit*>&o,T&c):out(o),check(c){}};
}
namespace Cell{template<class T>void VisitAllObjects(Unit*,T&s,float){for(auto*u:room)if(u->alive&&u->IsInMap(s.check.center)&&u->GetDistance(s.check.center)<=s.check.range)s.out.push_back(u);}}
''')
    code=code.replace('int main(){', 'void baseline_main(){')
    code+='\n'+block(source,'Unit* ai::RazorgoreDefenseTarget(').replace('ai::','')
    code+='\n'+block(source,'bool ai::NeedsRazorgoreControllerHealing(').replace('ai::','')
    code+=r'''
int main(){
 Player a,b,c,d,human,dps,healer;Player* members[]={&a,&b,&c,&d,&human,&dps,&healer};
 PlayerbotAI aa{&a},ba{&b},ca{&c},da{&d},ha{&human},pa{&dps},hea{&healer};
 PlayerbotAI* brains[]={&aa,&ba,&ca,&da,&ha,&pa,&hea};Group group;GroupReference refs[7];
 for(unsigned i=0;i<7;++i){members[i]->guid=i+1;members[i]->group=&group;members[i]->brain=brains[i];refs[i]={members[i],i<6?&refs[i+1]:nullptr};units[i+1]=members[i];}group.first=&refs[0];
 a.tank=b.tank=c.tank=d.tank=true;healer.healer=true;ha.real=true;
 GameObject altar;orb=&altar;Unit boss;boss.guid=100;boss.entry=12435;boss.charmer=&human;boss.master=&human;dragon=&boss;human.controlled=&boss;
 Unit adds[16];for(unsigned i=0;i<16;++i){adds[i].guid=200+i;adds[i].entry=i%3==0?12420:12416;adds[i].victim=&healer;units[adds[i].guid]=&adds[i];}
 adds[15].victim=&human;adds[15].x=5;room={&adds[0],&adds[1],&adds[2],&adds[15]};
 auto select=[](PlayerbotAI*x){bool active=false;Unit*u=RazorgoreDefenseTarget(x,active);return std::make_pair(active,u);};
#ifdef MANGOSBOT_ZERO
 // Different nearby target lists no longer hide an attacker on the platform.
 assert(select(&aa).second==&adds[15]);std::set<Unit*> picked;
 for(auto*x:{&aa,&ba,&ca,&da}){targets={};auto r=select(x);assert(r.first&&r.second);picked.insert(r.second);}
 assert(picked.size()==4);pa.guids["attack target"]=200;pa.guids["rti target"]=201;
 assert(select(&pa).second==&adds[15]);
 BlackwingLairPriorityTargetAction action{&pa,&dps};assert(action.GetTarget()==&adds[15]);
 // Holding one add cannot prevent the other three tanks picking up theirs.
 adds[15].victim=&a;a.victim=&adds[15];picked.clear();
 for(auto*x:{&aa,&ba,&ca,&da}){auto r=select(x);assert(r.second);picked.insert(r.second);}
 assert(picked.size()==4&&select(&aa).second==&adds[15]);
 // Native victim updates after each pickup: all sixteen eventually covered.
 room.clear();for(auto&u:adds){u.victim=&healer;room.push_back(&u);}adds[15].victim=&human;
 for(unsigned round=0;round<8;++round)for(auto*x:{&aa,&ba,&ca,&da})if(auto*u=select(x).second)u->victim=x->bot;
 for(auto&u:adds)assert(dynamic_cast<Player*>(u.victim)->tank);
 room={&adds[15]};adds[15].victim=&human;a.alive=b.alive=c.alive=false;
 assert(!select(&aa).first&&select(&da).second==&adds[15]);da.movable=false;assert(!select(&da).second);da.movable=true;
 // A controller whose normal role is tank is still defenseless while using
 // the orb. Only an actual, non-controlling human tank retains ownership.
 human.tank=true;assert(select(&da).second==&adds[15]);
 human.controlled=nullptr;boss.charmer=nullptr;assert(!select(&da).second);
 human.controlled=&boss;boss.charmer=&human;human.tank=false;
 adds[15].cc=true;assert(!select(&pa).second);adds[15].cc=false;adds[15].hardCC=true;assert(!select(&pa).second);adds[15].hardCC=false;
 adds[15].instance=2;assert(!select(&pa).second);adds[15].instance=1;
 adds[15].combat=false;assert(!select(&pa).second);adds[15].combat=true;
 Player outsider;adds[15].victim=&outsider;assert(!select(&pa).second);adds[15].victim=&boss;assert(select(&pa).second==&adds[15]);
 human.hp=50;assert(NeedsRazorgoreControllerHealing(&hea,&human));human.hp=100;assert(!NeedsRazorgoreControllerHealing(&hea,&human));
 human.hp=50;human.controlled=nullptr;assert(!NeedsRazorgoreControllerHealing(&hea,&human));human.controlled=&boss;
 eggPhase=false;assert(!select(&da).first&&!NeedsRazorgoreControllerHealing(&hea,&human));eggPhase=true;
 orb=nullptr;assert(!select(&da).first);orb=&altar;assert(!select(&hea).first&&!select(&ha).first);
#else
 assert(!select(&aa).first&&!select(&pa).first&&!NeedsRazorgoreControllerHealing(&hea,&human));
#endif
 std::cout<<"PASS actual Razorgore room assignments, controller rescue, 16-add pickup, healing and phase isolation\n";
}
'''
    for era in ('ZERO','ONE','TWO'):
        with tempfile.TemporaryDirectory(prefix='mantech-razorgore-defense-') as folder:
            tmp=Path(folder);(tmp/'test.cpp').write_text(code)
            subprocess.run(['cl','/nologo','/EHsc','/std:c++17',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
            subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
