"""Compile actual battlemaster selection and diagnostic formatting, not replicas."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
value = (root / 'playerbot/strategy/Value.h').read_text()
methods = '\n'.join((block(value, 'class CDPairCalculatedValue') + ';',
                     block(value, 'class CDPairListCalculatedValue') + ';',
                     block((root / 'playerbot/strategy/values/PvpValues.cpp').read_text(),
                           'CreatureDataPair const* BgMasterValue::NearestBm(')))
code = r'''
#include <cassert>
#include <list>
#include <map>
#include <sstream>
#include <string>
#include <ctime>
#include <iostream>
using uint32=unsigned;
enum {ALLIANCE=1,HORDE=2,REP_NEUTRAL=0,DEAD=1};
struct CreatureData {unsigned id=0,map=0,area=0;float distance=0;};
using CreatureDataPair=std::pair<unsigned,CreatureData>;
struct CreatureInfo {const char* Name="battlemaster";unsigned Faction=1;};
struct FactionTemplateEntry {int reaction=0;};
struct AreaTableEntry {unsigned team=0;};
struct Unit {int state=0;int GetDeathState(){return state;}};
struct Player {unsigned GetMapId(){return 0;}unsigned GetTeam(){return ALLIANCE;}};
struct ObjectMgr {static std::map<unsigned,CreatureInfo> templates;
 static const CreatureInfo* GetCreatureTemplate(unsigned id){auto i=templates.find(id);return i==templates.end()?nullptr:&i->second;}};
std::map<unsigned,CreatureInfo> ObjectMgr::templates;
struct Factions {std::map<unsigned,FactionTemplateEntry> entries;
 const FactionTemplateEntry* LookupEntry(unsigned id){auto i=entries.find(id);return i==entries.end()?nullptr:&i->second;}}sFactionTemplateStore;
struct WorldPosition {const CreatureDataPair* pair=nullptr;WorldPosition(Player*){}WorldPosition(const CreatureDataPair* p):pair(p){assert(p);}
 float distance(WorldPosition p){return p.pair->second.distance;}unsigned getMapId(){return pair->second.map;}
 const AreaTableEntry* GetArea(){static AreaTableEntry neutral;return pair->second.area?&neutral:nullptr;}};
struct PlayerbotAI {std::map<unsigned,Unit*> units;unsigned reactions=0;
 int getReaction(const FactionTemplateEntry* entry){assert(entry);++reactions;return entry->reaction;}
 Unit* GetUnit(const CreatureDataPair* p){return units[p->first];}};
template<class T>struct CalculatedValue {time_t lastCheckTime=0;T value{};
 CalculatedValue(PlayerbotAI*,std::string,int){}virtual ~CalculatedValue()=default;
 virtual T Calculate(){return value;}virtual std::string Format(){return {};}};
std::list<CreatureDataPair const*> records;
#define GAI_VALUE2(type,key,qualifier) records
struct BgMasterValue {Player* bot;PlayerbotAI* ai;std::string qualifier="1";
 const CreatureDataPair* NearestBm(bool allowDead);};
__METHODS__
int main(){
 Player bot;PlayerbotAI ai;BgMasterValue selector{&bot,&ai};
 CDPairCalculatedValue single(&ai);CDPairListCalculatedValue list(&ai);
 assert(single.Format()=="<none>");assert(list.Format()=="{}");
 CreatureDataPair near{1,{42,0,1,10}},far{2,{42,0,1,20}},missingTemplate{3,{99,0,1,5}};
 single.value=&missingTemplate;assert(single.Format()=="<none>");
 ObjectMgr::templates[42]=CreatureInfo{};single.value=&near;assert(single.Format()=="battlemaster");
 list.value={nullptr,&near,nullptr,&far};assert(list.Format()=="{1,2,}");
 records={nullptr,&missingTemplate,&near,&far};Unit live,dead;dead.state=DEAD;
 ai.units[1]=&live;ai.units[2]=&dead;
 assert(!selector.NearestBm(false));assert(ai.reactions==0); // invalid faction must not reach reaction logic
 sFactionTemplateStore.entries[1]={0};assert(selector.NearestBm(false)==&near);
 live.state=DEAD;assert(!selector.NearestBm(false));assert(selector.NearestBm(true)==&near);
 live.state=0;near.second.map=1;assert(!selector.NearestBm(false));near.second.map=0;
 near.second.area=0;assert(!selector.NearestBm(false));near.second.area=1;
 sFactionTemplateStore.entries[1].reaction=-1;assert(!selector.NearestBm(true));
 records={nullptr};assert(!selector.NearestBm(false));assert(!selector.NearestBm(true));
 std::cout<<"PASS: actual battlemaster missing record/template/faction, dead fallback and null-safe diagnostics\n";
}
'''.replace('__METHODS__', methods)
for era in ('ZERO', 'ONE', 'TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-battlemaster-') as folder:
        tmp = Path(folder)
        (tmp / 'test.cpp').write_text(code)
        subprocess.run(['cl', '/nologo', '/EHsc', '/std:c++17', f'/DMANGOSBOT_{era}',
                        'test.cpp', '/Fe:test.exe'], cwd=tmp, check=True)
        subprocess.run([str(tmp / 'test.exe')], cwd=tmp, check=True)
