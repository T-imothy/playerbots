"""Execute native Grip, Instability expiry and active-talent Unchained selection."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[2]
source=(root/'mangos-wotlk-behavior/src/game/AI/ScriptDevAI/scripts/northrend/icecrown_citadel/icecrown_citadel/boss_sindragosa.cpp').read_text()
methods='\n'.join(block(source,s).replace(' override','')+(';' if s.startswith('struct ') else '') for s in ('struct spell_sindragosa_icy_grip','struct spell_sindragosa_instability','static uint32 SindragosaUnchainedRole','struct spell_sindragosa_unchained_magic'))
code=r"""
#include <cassert>
#include <map>
#include <vector>
#include <set>
#include <algorithm>
#include <cstdint>
#include <iostream>
using uint32=uint32_t;using uint64=uint64_t;using int32=int32_t;using SpellEffectIndex=unsigned;
enum{EFFECT_INDEX_0, AURA_REMOVE_BY_EXPIRE=1,TRIGGERED_OLD_TRIGGERED=2,TYPE_SINDRAGOSA=3,IN_PROGRESS=4,NPC_SINDRAGOSA=36853,
 CLASS_WARRIOR=1,CLASS_PALADIN=2,CLASS_HUNTER=3,CLASS_ROGUE=4,CLASS_PRIEST=5,CLASS_DEATH_KNIGHT=6,CLASS_SHAMAN=7,CLASS_MAGE=8,CLASS_WARLOCK=9,CLASS_DRUID=11,PLAYERSPELL_REMOVED=1};
enum Difficulty{RAID_DIFFICULTY_10MAN_NORMAL,RAID_DIFFICULTY_25MAN_NORMAL,RAID_DIFFICULTY_10MAN_HEROIC,RAID_DIFFICULTY_25MAN_HEROIC};
struct Player;struct Creature;struct Aura;
struct Instance{virtual ~Instance()=default;};
struct instance_icecrown_citadel:Instance{Creature*boss=nullptr;unsigned state=IN_PROGRESS;Creature*GetSingleCreatureFromStorage(unsigned){return boss;}unsigned GetData(unsigned){return state;}};
struct Ref{Player*p;Player*getSource()const{return p;}};
struct Map{Difficulty difficulty=RAID_DIFFICULTY_10MAN_NORMAL;std::vector<Ref>players;const auto&GetPlayers(){return players;}Difficulty GetDifficulty(){return difficulty;}};
struct Guid{uint64 id;uint64 GetRawValue(){return id;}};
struct Unit{virtual ~Unit()=default;bool alive=true,player=false,combat=true;unsigned calls=0,last=0;int32 damage=0;uint64 original=0;Map*map=nullptr;Instance*instance=nullptr;Unit*victim=nullptr,*castTarget=nullptr;std::set<unsigned>auras;
 bool IsPlayer(){return player;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasAura(unsigned id){return auras.count(id);}Unit*GetVictim(){return victim;}Map*GetMap(){return map;}Instance*GetInstanceData(){return instance;}
 bool IsWithinDistInMap(Player*,float);
 void CastSpell(Unit*target,unsigned id,unsigned){++calls;last=id;castTarget=target;}
 void CastCustomSpell(Unit*target,unsigned id,int32*amount,void*,void*,unsigned,void*,Aura*,uint64 guid){CastSpell(target,id,0);damage=*amount;original=guid;}
};
struct TalentEntry{unsigned TalentTab;};struct PlayerTalent{TalentEntry*talentEntry;unsigned currentRank=0,state=0;};
struct Player:Unit{unsigned cls=CLASS_MAGE;uint64 guid=1;bool gm=false,teleport=false,near=true;std::map<unsigned,PlayerTalent>talents;Player(){player=true;}
 unsigned getClass(){return cls;}bool IsGameMaster(){return gm;}bool IsBeingTeleported(){return teleport;}const auto&GetActiveTalents(){return talents;}Guid GetObjectGuid(){return {guid};}};
bool Unit::IsWithinDistInMap(Player*p,float){return map==p->map&&p->near;}
struct Creature:Unit{};
struct Spell{Unit*caster=nullptr,*target=nullptr;uint64 value=0;Unit*GetCaster()const{return caster;}Unit*GetUnitTarget(){return target;}uint64 GetScriptValue()const{return value;}void SetScriptValue(uint64 v){value=v;}};
struct Aura{Unit*target=nullptr,*caster=nullptr;unsigned effect=0,mode=AURA_REMOVE_BY_EXPIRE;int32 amount=6000;unsigned GetEffIndex(){return effect;}unsigned GetRemoveMode(){return mode;}Unit*GetTarget(){return target;}Unit*GetCaster(){return caster;}int32 GetAmount(){return amount;}uint64 GetCasterGuid(){return 77;}};
struct SpellScript{};struct AuraScript{};unsigned urand(unsigned,unsigned){return 12345;}
__METHODS__
int main(){
 Map map;Creature boss;boss.map=&map;Player p,tank;p.map=tank.map=&map;boss.victim=&tank;Spell spell{&boss,&p};spell_sindragosa_icy_grip grip;
 assert(grip.OnCheckTarget(&spell,&p,0));assert(!grip.OnCheckTarget(&spell,&tank,0));
 for(unsigned id:{70126u,70157u}){p.auras.insert(id);assert(!grip.OnCheckTarget(&spell,&p,0));p.auras.clear();}
 p.alive=false;assert(!grip.OnCheckTarget(&spell,&p,0));p.alive=true;
 grip.OnEffectExecute(&spell,1);assert(p.calls==0);grip.OnEffectExecute(&spell,0);assert(p.last==70122&&p.castTarget==&boss);
 instance_icecrown_citadel instance;instance.boss=&boss;p.instance=&instance;Aura aura{&p,&p};spell_sindragosa_instability instability;
 auto calls=p.calls;instability.OnApply(&aura,true);assert(p.calls==calls);aura.mode=0;instability.OnApply(&aura,false);assert(p.calls==calls);
 aura.mode=AURA_REMOVE_BY_EXPIRE;instability.OnApply(&aura,false);assert(p.calls==calls+1&&p.damage==6000&&p.last==69770&&p.original==77);
 calls=p.calls;instance.state=0;instability.OnApply(&aura,false);assert(p.calls==calls);instance.state=IN_PROGRESS;
 boss.alive=false;instability.OnApply(&aura,false);assert(p.calls==calls);boss.alive=true;
 aura.amount=0;instability.OnApply(&aura,false);assert(p.calls==calls);aura.amount=6000;p.alive=false;instability.OnApply(&aura,false);assert(p.calls==calls);p.alive=true;
 // Native active talent trees: every eligible/ineligible class and specialization.
 for(auto pair:std::vector<std::pair<unsigned,unsigned>>{{201,CLASS_PRIEST},{202,CLASS_PRIEST},{382,CLASS_PALADIN},{262,CLASS_SHAMAN},{282,CLASS_DRUID}}){
  TalentEntry tree{pair.first};p.cls=pair.second;p.talents={{1,{&tree,4,0}}};assert(SindragosaUnchainedRole(&p)==1);
  p.talents[1].state=PLAYERSPELL_REMOVED;assert(SindragosaUnchainedRole(&p)!=1);
 }p.talents.clear();
 for(auto pair:std::vector<std::pair<unsigned,unsigned>>{{263,CLASS_SHAMAN},{281,CLASS_DRUID},{381,CLASS_PALADIN},{383,CLASS_PALADIN}}){TalentEntry tree{pair.first};p.cls=pair.second;p.talents={{1,{&tree,4,0}}};assert(SindragosaUnchainedRole(&p)==0);}p.talents.clear();
 for(unsigned cls:{CLASS_MAGE,CLASS_WARLOCK,CLASS_PRIEST,CLASS_DRUID,CLASS_SHAMAN}){p.cls=cls;assert(SindragosaUnchainedRole(&p)==2);}
 for(unsigned cls:{CLASS_WARRIOR,CLASS_HUNTER,CLASS_ROGUE,CLASS_DEATH_KNIGHT,CLASS_PALADIN}){p.cls=cls;assert(SindragosaUnchainedRole(&p)==0);}
 // Per-cast stable selection, healer caps, all four difficulties and missing-healer fill.
 Player group[20];TalentEntry holy{202};map.players.clear();
 for(unsigned i=0;i<20;++i){group[i].guid=i+1;group[i].map=&map;if(i<8){group[i].cls=CLASS_PRIEST;group[i].talents={{1,{&holy,4,0}}};}map.players.push_back({&group[i]});}
 spell_sindragosa_unchained_magic unchained;unchained.OnInit(&spell);
 for(auto diff:{RAID_DIFFICULTY_10MAN_NORMAL,RAID_DIFFICULTY_10MAN_HEROIC,RAID_DIFFICULTY_25MAN_NORMAL,RAID_DIFFICULTY_25MAN_HEROIC}){
  map.difficulty=diff;unsigned healers=0,total=0;std::set<uint64>selected;
  for(auto&member:group){bool yes=unchained.OnCheckTarget(&spell,&member,0);assert(yes==unchained.OnCheckTarget(&spell,&member,1));if(yes){++total;healers+=SindragosaUnchainedRole(&member)==1;selected.insert(member.guid);}}
  bool large=diff==RAID_DIFFICULTY_25MAN_NORMAL||diff==RAID_DIFFICULTY_25MAN_HEROIC;assert(total==(large?6u:2u)&&healers==(large?3u:1u));
  std::reverse(map.players.begin(),map.players.end());for(auto&member:group)assert(unchained.OnCheckTarget(&spell,&member,0)==bool(selected.count(member.guid)));
 }
 for(unsigned i=0;i<8;++i)group[i].alive=false;unsigned total=0;for(auto&member:group)total+=unchained.OnCheckTarget(&spell,&member,0);assert(total==6);
 for(bool Player::*flag:{&Player::gm,&Player::teleport}){group[12].*flag=true;assert(!unchained.OnCheckTarget(&spell,&group[12],0));group[12].*flag=false;}
 group[12].near=false;assert(!unchained.OnCheckTarget(&spell,&group[12],0));group[12].near=true;group[12].auras.insert(70157);assert(!unchained.OnCheckTarget(&spell,&group[12],0));
 std::cout<<"PASS: native Icy Grip, expiry-only Backlash, active talent role selection and stable capped Unchained targets across raid difficulties\n";
}
""".replace('__METHODS__',methods)
with tempfile.TemporaryDirectory(prefix='sindragosa-combat-') as folder:
 path=Path(folder);(path/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,check=True,timeout=60)
 subprocess.run([str(path/'test.exe')],cwd=path,check=True,timeout=20)
