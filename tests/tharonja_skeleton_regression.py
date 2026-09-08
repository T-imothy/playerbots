"""Execute native-form bot decisions with actual production action methods."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
s=(root/'playerbot/strategy/actions/DungeonActions.cpp').read_text()
methods='\n'.join(block(s,key) for key in ['Unit* TharonjaSkeletonAction::GetBoss()', 'uint32 TharonjaSkeletonAction::SelectSpell(', 'bool TharonjaSkeletonAction::isUseful()', 'bool TharonjaSkeletonAction::Execute('])
code=r'''
#include <cassert>
#include <set>
#include <iostream>
using uint32=unsigned;
struct Unit{bool world=true,alive=true,combat=true,charmed=false,sameMap=true;unsigned entry=26632;Unit*victim=nullptr;bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charmed;}bool IsInMap(Unit*u){return u&&u->sameMap;}unsigned GetEntry(){return entry;}Unit*GetVictim(){return victim;}};
struct SpellAuraHolder{Unit*caster;Unit*GetCaster(){return caster;}};
struct Player:Unit{unsigned map=600,form=10;bool grouped=true,teleport=false,melee=true,armor=false;float hp=100;SpellAuraHolder*gift;unsigned GetMapId(){return map;}bool GetGroup(){return grouped;}bool IsBeingTeleported(){return teleport;}unsigned GetShapeshiftForm(){return form;}SpellAuraHolder*GetSpellAuraHolder(unsigned id){assert(id==52509);return gift;}float GetHealthPercent(){return hp;}bool HasAura(unsigned id){assert(id==49609);return armor;}bool CanReachWithMeleeAttack(Unit*){return melee;}};
struct Facade{bool friendly=false;bool IsFriendlyTo(Unit*,Unit*){return friendly;}}sServerFacade;
struct SpellShapeshiftFormEntry{uint32 spellId[8]={50799,49613,49609,49617};};
struct Store{SpellShapeshiftFormEntry form;bool present=true;const SpellShapeshiftFormEntry*LookupEntry(unsigned id){assert(id==10);return present?&form:nullptr;}}sSpellShapeshiftFormStore;
struct PlayerbotAI{Player*bot;bool real=false,tank=false,castOK=true;std::set<unsigned>ready;Unit*recipient=nullptr;unsigned cast=0;bool IsRealPlayer(){return real;}bool IsTank(Player*){return tank;}bool CanCastSpell(unsigned id,Unit*,unsigned mask,bool learned){assert(!mask&&!learned);return ready.count(id);}bool CastSpell(unsigned id,Unit*t,void*,bool wait,unsigned*duration){assert(!wait);cast=id;recipient=t;*duration=1500;return castOK;}};
struct Event{};
struct TharonjaSkeletonAction{Player*bot;PlayerbotAI*ai;unsigned duration=0,moves=0;bool path=true;Unit*GetBoss();uint32 SelectSpell(Unit*,Unit*&);bool isUseful();bool Execute(Event&);void SetDuration(unsigned value){duration=value;}bool MoveNear(Unit*,float distance){assert(distance==2);++moves;return path;}};
__METHODS__
int main(){
 Unit boss,other;SpellAuraHolder gift{&boss};Player bot;bot.gift=&gift;PlayerbotAI ai{&bot};TharonjaSkeletonAction action{&bot,&ai};Event event;Unit*target=nullptr;
 ai.ready={49617,49609,49613,50799};boss.victim=&other;
#ifdef MANGOSBOT_TWO
 assert(action.GetBoss()==&boss&&action.isUseful());assert(action.SelectSpell(&boss,target)==50799&&target==&boss);
 bot.hp=50;assert(action.SelectSpell(&boss,target)==49617&&target==&boss);ai.ready.erase(49617);assert(action.SelectSpell(&boss,target)==49609&&target==&bot);
 bot.hp=100;ai.tank=true;assert(action.SelectSpell(&boss,target)==49613&&target==&boss);boss.victim=&bot;assert(action.SelectSpell(&boss,target)==49609&&target==&bot);
 bot.armor=true;assert(action.SelectSpell(&boss,target)==50799);assert(action.Execute(event)&&ai.cast==50799&&ai.recipient==&boss&&action.duration==1500);
 ai.castOK=false;assert(!action.Execute(event));ai.castOK=true;ai.ready.clear();assert(!action.isUseful());bot.melee=false;assert(action.isUseful()&&action.Execute(event)&&action.moves==1);action.path=false;assert(!action.Execute(event));
 ai.ready={50799};sSpellShapeshiftFormStore.form.spellId[0]=0;assert(action.SelectSpell(&boss,target)==0&&target==nullptr);sSpellShapeshiftFormStore.form.spellId[0]=50799;
 sSpellShapeshiftFormStore.present=false;assert(!action.SelectSpell(&boss,target));sSpellShapeshiftFormStore.present=true;
 bot.form=1;assert(!action.GetBoss()&&!action.Execute(event));bot.form=10;bot.map=1;assert(!action.GetBoss());bot.map=600;
 bot.gift=nullptr;assert(!action.GetBoss());bot.gift=&gift;gift.caster=nullptr;assert(!action.GetBoss());gift.caster=&boss;
 for(bool*flag:{&bot.world,&bot.alive,&bot.combat,&bot.grouped,&boss.world,&boss.alive,&boss.combat,&boss.sameMap}){*flag=false;assert(!action.GetBoss());*flag=true;}
 for(bool*flag:{&bot.teleport,&bot.charmed,&boss.charmed,&ai.real,&sServerFacade.friendly}){*flag=true;assert(!action.GetBoss());*flag=false;}
 boss.entry=1;assert(!action.GetBoss());boss.entry=26632;bot.gift=nullptr;assert(!action.isUseful()&&!action.Execute(event));
#else
 assert(!action.GetBoss()&&!action.isUseful()&&!action.Execute(event));assert(action.SelectSpell(&boss,target)==0&&target==nullptr);
#endif
 std::cout<<"PASS: native form abilities, healing/armor/tank-only taunt priorities, cooldown failure, path rejection, expired form/owner and era gates\n";
}
'''.replace('__METHODS__',methods)
for era in ['ZERO','ONE','TWO']:
 with tempfile.TemporaryDirectory(prefix='tharonja-skeleton-') as folder:
  path=Path(folder);(path/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=path,check=True,timeout=60)
  subprocess.run([str(path/'test.exe')],cwd=path,check=True,timeout=20)
