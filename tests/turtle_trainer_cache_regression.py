from pathlib import Path
root=Path(__file__).resolve().parents[1]
source = (root/'playerbot/strategy/values/TrainerValues.cpp').read_text()
calc = source[source.index('trainableSpellMap* TrainableSpellMapValue::Calculate()'):source.index('std::string TrainableSpellsValue::Format()')]
available = source[source.index('std::vector<int32> AvailableTrainersValue::Calculate()'):source.index('uint32 TrainCostValue::Calculate()')]
code = r'''
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <map>
#include <memory>
#include <string>
#include <tuple>
#include <unordered_map>
#include <vector>
#include <cstdio>
using uint32=uint32_t;using int32=int32_t;using int8=int8_t;
using std::stoi;
enum TrainerType {TRAINER_TYPE_CLASS,TRAINER_TYPE_MOUNTS,TRAINER_TYPE_TRADESKILLS,TRAINER_TYPE_PETS};
enum TrainerSpellState {TRAINER_SPELL_RED,TRAINER_SPELL_GREEN};
constexpr uint32 SPELL_EFFECT_SKILL=1,SPELL_EFFECT_SKILL_STEP=2;
struct TrainerSpell {uint32 spell=0,spellCost=0,reqSkill=0,reqSkillValue=0,reqLevel=1;bool isProvidedReqLevel=false;uint32 conditionId=0,learnedSpell=0;};
struct TrainerSpellData {std::map<uint32,TrainerSpell> spellList;const TrainerSpell* Find(uint32 id)const{auto it=spellList.find(id);return it==spellList.end()?nullptr:&it->second;}};
struct CreatureInfo {uint32 Entry=0,TrainerType=0,TrainerClass=0,TrainerRace=0,TrainerTemplateId=0;};
struct SpellEntry {uint32 Effect[3]{};int32 EffectMiscValue[3]{};};
template<class V>struct Storage {std::map<uint32,V> data;template<class T>const T* LookupEntry(uint32 id)const {auto it=data.find(id);return it==data.end()?nullptr:&it->second;}};
Storage<CreatureInfo> sCreatureStorage;Storage<SpellEntry> sSpellTemplate;
struct ObjectMgr {std::map<uint32,int> creatures;std::map<uint32,TrainerSpellData> entries,templates;
auto const& GetCreatureInfoMap()const{return creatures;}
const TrainerSpellData* GetNpcTrainerSpells(uint32 id)const {auto it=entries.find(id);return it==entries.end()?nullptr:&it->second;}
const TrainerSpellData* GetNpcTrainerTemplateSpells(uint32 id)const {auto it=templates.find(id);return it==templates.end()?nullptr:&it->second;}
}sObjectMgr;
struct SpellMgr {bool IsProfessionSpell(uint32)const{return false;}uint32 GetSpellRank(uint32)const{return 0;}}sSpellMgr;
using spellTrainerMap=std::unordered_map<const TrainerSpell*,std::vector<int32>>;
using trainableSpellMap=std::unordered_map<TrainerType,std::unordered_map<uint32,spellTrainerMap>>;
struct Bot {uint32 getClass()const{return 8;}uint32 getRace()const{return 9;}uint32 GetLevel()const{return 20;}TrainerSpellState GetTrainerSpellState(const TrainerSpell* s,uint32)const{return s->reqLevel<=20?TRAINER_SPELL_GREEN:TRAINER_SPELL_RED;}} testBot;
trainableSpellMap* activeMap=nullptr;std::vector<const TrainerSpell*> activeSpells;
#define GAI_VALUE(type,name) activeMap
#define AI_VALUE2(type,name,qualifier) activeSpells
#define MANGOSBOT_ZERO
struct TrainableSpellMapValue {trainableSpellMap* Calculate();};
struct TrainableSpellsValue {Bot* bot=&testBot;std::string qualifier;std::string getQualifier()const{return qualifier;}std::vector<const TrainerSpell*> Calculate();};
struct AvailableTrainersValue {Bot* bot=&testBot;std::string qualifier;std::string getQualifier()const{return qualifier;}std::vector<int32> Calculate();};
''' + calc + available + r'''
void trainer(uint32 id,TrainerType type,uint32 cls,uint32 race,uint32 tpl){sObjectMgr.creatures[id]=0;sCreatureStorage.data[id]={id,uint32(type),cls,race,tpl};}
TrainerSpell offer(uint32 spell,uint32 cost=10,uint32 skill=0,uint32 level=1){TrainerSpell s;s.spell=spell;s.learnedSpell=spell;s.spellCost=cost;s.reqSkill=skill;s.reqLevel=level;return s;}
bool contains(const std::vector<int32>& v,int32 n){return std::find(v.begin(),v.end(),n)!=v.end();}
int main(){
 trainer(10,TRAINER_TYPE_CLASS,8,0,20);trainer(11,TRAINER_TYPE_CLASS,1,0,20);
 trainer(20,TRAINER_TYPE_CLASS,8,0,0);trainer(30,TRAINER_TYPE_MOUNTS,0,9,0);
 trainer(31,TRAINER_TYPE_MOUNTS,0,10,0);trainer(40,TRAINER_TYPE_TRADESKILLS,0,0,0);
 trainer(41,TRAINER_TYPE_CLASS,8,0,20);trainer(42,TRAINER_TYPE_CLASS,8,0,0);
 sObjectMgr.templates[20].spellList={{100,offer(100)},{101,offer(101)}};
 sObjectMgr.entries[10].spellList={{100,offer(100,99)},{102,offer(102)}};
 sObjectMgr.entries[20].spellList={{200,offer(200)}};
 sObjectMgr.entries[30].spellList={{300,offer(300)}};sObjectMgr.entries[31].spellList={{301,offer(301)}};
 sObjectMgr.entries[40].spellList={{400,offer(400,10,164)},{401,offer(401)},{402,offer(402)},{403,offer(403)}};
 sSpellTemplate.data[401].Effect[0]=SPELL_EFFECT_SKILL;sSpellTemplate.data[401].EffectMiscValue[0]=165;
 sSpellTemplate.data[403].Effect[2]=SPELL_EFFECT_SKILL_STEP;sSpellTemplate.data[403].EffectMiscValue[2]=171;
 sObjectMgr.entries[42].spellList={{100,offer(100)}};sObjectMgr.entries[42].spellList[100].conditionId=77;
 TrainableSpellMapValue builder;std::unique_ptr<trainableSpellMap> result(builder.Calculate());activeMap=result.get();
 auto& mage=(*result)[TRAINER_TYPE_CLASS][8];int overrides=0,templates=0,conditioned=0;
 for(auto const& [s,ids]:mage){
  if(s->spell==100 && s->spellCost==99){assert(contains(ids,10)&&!contains(ids,41));++overrides;}
  if(s->spell==100 && s->spellCost==10 && !s->conditionId){assert(!contains(ids,10)&&contains(ids,41));++templates;}
  if(s->conditionId==77){assert(ids==std::vector<int32>{42});++conditioned;}
  if(s->spell==101){assert(contains(ids,10)&&contains(ids,41)&&!contains(ids,11));}
  if(s->spell==200){assert(ids==std::vector<int32>{20});}
 }
 assert(overrides==1&&templates==1&&conditioned==1);
 assert((*result)[TRAINER_TYPE_CLASS][1].size()==2);
 auto& skills=(*result)[TRAINER_TYPE_TRADESKILLS];assert(skills[164].size()==1&&skills[165].size()==1&&skills[171].size()==1&&skills[0].size()==1);
 TrainableSpellsValue spells;activeSpells=spells.Calculate();assert(!activeSpells.empty());
 AvailableTrainersValue trainers;auto ids=trainers.Calculate();assert(contains(ids,10)&&contains(ids,20)&&contains(ids,30)&&contains(ids,40)&&!contains(ids,11)&&!contains(ids,31));
 spells.qualifier="0";activeSpells=spells.Calculate();trainers.qualifier="0";ids=trainers.Calculate();assert(contains(ids,10)&&!contains(ids,30)&&!contains(ids,40));
 spells.qualifier="1";activeSpells=spells.Calculate();trainers.qualifier="1";ids=trainers.Calculate();assert(ids==std::vector<int32>{30});
 puts("PASS trainer namespaces, merged lists, entry precedence, class/race/skill requirements, missing spells, offer identity, and qualified/unqualified consumers");
}
'''
import tempfile, subprocess, shutil
with tempfile.TemporaryDirectory(prefix='turtle-integration-') as folder:
    folder=Path(folder)
    cpp=folder/'integration.cpp'; cpp.write_text(code,encoding='utf-8')
    cl=shutil.which('cl')
    if cl:
        exe=folder/'integration.exe'
        command=[cl,'/nologo','/std:c++17','/EHsc','/MD','/O2','/I'+str(Path(__file__).resolve().parents[3]/'src/shared'),str(cpp),'/Fe'+str(exe),'/Fo'+str(folder/'integration.obj')]
    else:
        compiler=shutil.which('c++')
        if not compiler: raise SystemExit('Run in a C++ compiler environment (Visual Studio Developer PowerShell on Windows).')
        exe=folder/'integration'
        command=[compiler,'-std=c++17','-pthread','-I'+str(Path(__file__).resolve().parents[3]/'src/shared'),str(cpp),'-o',str(exe)]
    subprocess.run(command,check=True,cwd=folder)
    subprocess.run([str(exe)],check=True)
