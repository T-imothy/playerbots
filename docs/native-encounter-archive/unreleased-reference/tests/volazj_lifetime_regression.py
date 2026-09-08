"""Execute native Insanity lifecycle and phase transfer with repeat callbacks."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[2]/'mangos-wotlk-behavior/src/game/AI/ScriptDevAI/scripts/northrend/azjol-nerub/ahnkahet'
s=(root/'ahnkahet.cpp').read_text()
case=block(s[s.index('void instance_ahnkahet::SetData('):],'        case TYPE_VOLAZJ:')
methods='\n'.join(block(s,key) for key in ['void instance_ahnkahet::OnCreatureDespawn(', 'void instance_ahnkahet::FinishInsanityVisage(', 'void instance_ahnkahet::HandleInsanityClear()', 'void instance_ahnkahet::HandleInsanitySwitch(', 'bool instance_ahnkahet::HasInsanityVisage(', 'void instance_ahnkahet::UpdateInsanityPhases('])
helper=block(s,'static uint32 GetVolazjInsanityPhase(')
summon_handler=block((root/'boss_volazj.cpp').read_text(),'struct SummonVolazjVisage').replace(' override','')
code=r'''
#include <cassert>
#include <set>
#include <map>
#include <list>
#include <vector>
#include <iostream>
using uint32=unsigned;using ObjectGuid=unsigned;using GuidList=std::list<unsigned>;
enum{TYPE_VOLAZJ=0,IN_PROGRESS=1,SPECIAL=2,DONE=3,FAIL=4,ACHIEV_START_VOLAZJ_ID=20382,NPC_HERALD_VOLAZJ=1,NPC_TWISTED_VISAGE_1=30621,TRIGGERED_OLD_TRIGGERED=0,SPELL_TWISTED_VISAGE_DEATH=57555,SPELL_INSANITY_CLEAR=57558,SPELL_INSANITY_PHASE_16=57508,SPELL_INSANITY_PHASE_32=57509,SPELL_INSANITY_PHASE_64=57510,SPELL_INSANITY_PHASE_128=57511,SPELL_INSANITY_PHASE_256=57512};
unsigned urand(unsigned lo,unsigned){return lo;}
enum{SPELL_SUMMON_VISAGE_1=57500,SPELL_SUMMON_VISAGE_5=57504};struct Proto{unsigned Id;};struct Spell{Proto*m_spellInfo;};struct SpellScript{};
__SUMMON_HANDLER__;
struct instance_ahnkahet;
struct Player{unsigned guid;bool alive=true,castOK=true;std::set<unsigned>auras;bool HasAura(unsigned id){return auras.count(id);}bool IsAlive(){return alive;}void CastSpell(Player*,unsigned id,unsigned){if(castOK)auras.insert(id);}void RemoveAurasDueToSpell(unsigned id){auras.erase(id);}};
using PlayerList=std::list<Player*>;
struct Creature{unsigned guid,owner=0,despawns=0,deathCasts=0;bool temp=true;instance_ahnkahet*instance;std::set<unsigned>auras;unsigned entry=30621;bool alive=true;unsigned GetEntry(){return entry;}bool IsAlive(){return alive;}unsigned GetObjectGuid(){return guid;}bool IsTemporarySummon(){return temp;}unsigned GetSpawnerGuid(){return owner;}void CastSpell(Creature*,unsigned id,unsigned){if(id==57555)++deathCasts;}void RemoveAurasDueToSpell(unsigned id){auras.erase(id);}void ForcedDespawn();};
struct Ref{Player*p;Player*getSource()const{return p;}};
struct Map{std::map<unsigned,Player*>players;std::map<unsigned,Creature*>creatures;unsigned attempts=0;std::vector<Ref>GetPlayers(){std::vector<Ref>r;for(auto[p,v]:players)r.push_back({v});return r;}Player*GetPlayer(unsigned id){auto i=players.find(id);return i==players.end()?nullptr:i->second;}Creature*GetCreature(unsigned id){auto i=creatures.find(id);return i==creatures.end()?nullptr:i->second;}void StartEventForAllPlayersInMap(unsigned,void*){++attempts;}};
struct instance_ahnkahet{
 Map*instance;unsigned m_auiEncounter[1]={0},m_uiTwistedVisageCount=0;std::set<ObjectGuid>m_insanityVisages;GuidList m_lInsanityPlayersGuidList;Creature*boss;
 unsigned GetData(unsigned)const{return m_auiEncounter[0];}Creature*GetSingleCreatureFromStorage(unsigned){return boss;}
 void SetData(unsigned uiType,unsigned uiData){switch(uiType){__CASE__}}
 void OnCreatureDespawn(Creature*);void FinishInsanityVisage(Creature*,bool);void HandleInsanityClear();void HandleInsanitySwitch(Player*);bool HasInsanityVisage(uint32)const;void UpdateInsanityPhases();
};
__HELPER__
__METHODS__
void Creature::ForcedDespawn(){++despawns;instance->OnCreatureDespawn(this);}
int main(){
 Proto proto{57500};Spell spell{&proto};SummonVolazjVisage summon;for(unsigned index=0;index<5;++index){proto.Id=57500+index;assert(summon.GetPhaseMaskOverride(&spell)==(16u<<index));}proto.Id=123;assert(summon.GetPhaseMaskOverride(&spell)==1);
 Map map;Player first{11},second{12},dead{13};dead.alive=false;map.players={{11,&first},{12,&second},{13,&dead}};instance_ahnkahet instance{&map};Creature boss{1,0,0,0,false,&instance},one{21,11,0,0,true,&instance},two{22,12,0,0,true,&instance};instance.boss=&boss;two.entry=30622;map.creatures={{21,&one},{22,&two}};
 instance.SetData(TYPE_VOLAZJ,IN_PROGRESS);assert(map.attempts==1);instance.SetData(TYPE_VOLAZJ,IN_PROGRESS);assert(map.attempts==1);
 auto phase=[&](){instance.SetData(TYPE_VOLAZJ,SPECIAL);instance.m_insanityVisages={21,22};instance.m_uiTwistedVisageCount=2;instance.m_lInsanityPlayersGuidList={11,12,13};first.auras={57508,90000};second.auras={57509,90001};dead.auras={57508,90002};boss.auras={57561,99999};};
 phase();instance.FinishInsanityVisage(&one,true);assert(instance.m_uiTwistedVisageCount==1&&one.deathCasts==1);assert(!first.HasAura(57508)&&first.HasAura(57509)&&first.HasAura(90000));assert(dead.HasAura(90002));
 instance.OnCreatureDespawn(&one);instance.FinishInsanityVisage(&one,true);assert(instance.m_uiTwistedVisageCount==1&&one.deathCasts==1);
 instance.OnCreatureDespawn(&two);assert(instance.GetData(0)==IN_PROGRESS&&instance.m_uiTwistedVisageCount==0&&map.attempts==1&&boss.auras==std::set<unsigned>{99999});assert(first.auras==std::set<unsigned>{90000}&&second.auras==std::set<unsigned>{90001}&&dead.auras==std::set<unsigned>{90002});
 phase();instance.SetData(TYPE_VOLAZJ,FAIL);assert(instance.GetData(0)==FAIL&&instance.m_insanityVisages.empty()&&one.despawns==1&&two.despawns==1);instance.FinishInsanityVisage(&one,true);assert(instance.GetData(0)==FAIL&&instance.m_uiTwistedVisageCount==0);instance.SetData(TYPE_VOLAZJ,IN_PROGRESS);assert(map.attempts==2);
 phase();instance.m_insanityVisages.erase(21);first.castOK=false;instance.HandleInsanitySwitch(&first);assert(first.HasAura(57508)&&!first.HasAura(57509));first.castOK=true;second.alive=false;instance.UpdateInsanityPhases();assert(first.HasAura(57509));second.alive=true;instance.HandleInsanitySwitch(&first);assert(first.HasAura(57509)&&!first.HasAura(57508));
 instance.SetData(TYPE_VOLAZJ,DONE);assert(instance.GetData(0)==DONE&&first.HasAura(90000)&&!first.HasAura(57509));instance.OnCreatureDespawn(&two);assert(instance.GetData(0)==DONE);
 Creature third{23,12,0,0,true,&instance};third.entry=30621;map.creatures[23]=&third;
 phase();instance.m_insanityVisages.insert(23);instance.FinishInsanityVisage(&one,true);
 assert(first.HasAura(57508)&&!first.HasAura(57509)&&instance.m_insanityVisages.size()==2);
 instance.FinishInsanityVisage(&third,true);assert(first.HasAura(57509)&&!first.HasAura(57508));
 instance.SetData(TYPE_VOLAZJ,FAIL);
 phase();instance.m_insanityVisages={999};instance.UpdateInsanityPhases();assert(instance.GetData(0)==IN_PROGRESS&&!first.HasAura(57508));
 std::cout<<"PASS: duplicate/reentrant visage death, despawn, wipe/completion cleanup, attempt timer, unrelated phases, failed phase transfer retry, empty-owner destinations, grouped phase completion and missing actors\n";
}
'''.replace('__CASE__',case).replace('__HELPER__',helper).replace('__METHODS__',methods).replace('__SUMMON_HANDLER__',summon_handler)
with tempfile.TemporaryDirectory(prefix='volazj-lifetime-') as folder:
 path=Path(folder);(path/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,check=True,timeout=60)
 subprocess.run([str(path/'test.exe')],cwd=path,check=True,timeout=20)
