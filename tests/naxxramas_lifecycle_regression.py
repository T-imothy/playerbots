"""Compile actual native Thaddius lifecycle handlers, without a running world."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
fixture = r'''
#include <cassert>
#include <chrono>
#include <iostream>
#include <map>
#include <vector>
#include <set>
using namespace std::chrono_literals;
using uint32=unsigned;
enum {IN_PROGRESS=1,DONE=2,TYPE_THADDIUS=3,NPC_FEUGEN=15930,NPC_STALAGG=15929,
 SAY_STAL_DEATH=10,SAY_FEUG_DEATH=11,UNIT_FIELD_FLAGS=1,UNIT_FLAG_UNINTERACTIBLE=2,
 UNIT_FLAG_IMMUNE_TO_PLAYER=4,UNIT_STAND_STATE_DEAD=5,AURA_STATE_HEALTHLESS_20_PERCENT=6,
 AURA_STATE_HEALTHLESS_35_PERCENT=7,THADDIUS_ADD_REVIVE=8,SPELL_CLEAR_CHARGES=63133};
enum{TYPEID_PLAYER=1,SPELL_POSITIVE_CHARGE=28059,SPELL_NEGATIVE_CHARGE=28084,SPELL_POSITIVE_CHARGE_BUFF=29659,SPELL_NEGATIVE_CHARGE_BUFF=29660};
struct Unit{unsigned type=2;std::set<unsigned>auras;unsigned GetTypeId(){return type;}void RemoveAurasDueToSpell(unsigned id){auras.erase(id);}};
struct Player:Unit{Player(){type=TYPEID_PLAYER;}};struct Creature;
struct ScriptedInstance { unsigned state=IN_PROGRESS,changes=0;std::map<unsigned,Creature*> creatures;
 void SetData(unsigned type,unsigned value){assert(type==TYPE_THADDIUS);state=value;++changes;}
 Creature* GetSingleCreatureFromStorage(unsigned id){auto it=creatures.find(id);return it==creatures.end()?nullptr:it->second;}};
struct MotionMaster{void Clear(){} void MoveIdle(){}};
struct Ref{Player*p;Player*getSource()const{return p;}};
struct Map{std::vector<Ref>players;Unit* GetUnit(unsigned){return nullptr;}const std::vector<Ref>&GetPlayers(){return players;}};
struct Creature:Unit{unsigned entry=NPC_FEUGEN,health=100,flags=0,stand=0,despawns=0;bool stopped=false;
 ScriptedInstance* instance=nullptr;MotionMaster motion;Map map;
 unsigned GetEntry()const{return entry;}ScriptedInstance* GetInstanceData(){return instance;}
 void ForcedDespawn(){++despawns;}void InterruptNonMeleeSpells(bool){}void SetHealth(unsigned value){health=value;}
 void StopMoving(){stopped=true;}void ClearComboPointHolders(){}void RemoveAllAurasOnDeath(){}
 void ModifyAuraState(unsigned,bool){}void SetFlag(unsigned,unsigned value){flags|=value;}
 void ClearAllReactives(){}MotionMaster* GetMotionMaster(){return &motion;}void SetStandState(unsigned value){stand=value;}
 Map* GetMap(){return &map;}void CastSpell(Unit*,unsigned,unsigned){}
};
unsigned textCount=0,lastText=0;Unit* textRecipient=nullptr;
void DoBroadcastText(unsigned text,Creature*,Unit* recipient){++textCount;lastText=text;textRecipient=recipient;}
unsigned urand(unsigned a,unsigned){return a;}
struct CombatAI{unsigned deathCalls=0;virtual void JustDied(Unit* =nullptr){++deathCalls;}virtual void JustPreventedDeath(Unit*){}};
struct QueuedCast{unsigned target=0,spellId=0,flags=0;};
struct BossAI:CombatAI{Creature* m_creature;unsigned m_instanceDataType=TYPE_THADDIUS,opened=0,closed=0;
 std::vector<unsigned> m_onKilledTexts{99};std::vector<QueuedCast> m_castOnDeath;
 explicit BossAI(Creature* creature):m_creature(creature){}
 void JustDied(Unit* killer=nullptr)override;
 void Aggro(Unit*){m_creature->instance->SetData(m_instanceDataType,IN_PROGRESS);++closed;}
 void OpenEntrances(){++opened;}void OpenExits(){++opened;}
};
__NATIVE_BASE_DEATH__
__CLEAR_HELPER__
struct Boss:BossAI{ScriptedInstance* m_instance;unsigned cleared=0;
 Boss(Creature* c):BossAI(c),m_instance(c->instance){}
 void DoCastSpellIfCan(Unit*,unsigned spell){assert(spell==SPELL_CLEAR_CHARGES);++cleared;}
 __CLEAR_PLAYERS__
 __BOSS_DEATH__
};
struct Adds:BossAI{ScriptedInstance* m_instance;bool m_isFakingDeath=false,script=false;unsigned timer=0;
 Adds(Creature* c):BossAI(c),m_instance(c->instance){}
 void SetCombatScriptStatus(bool value){script=value;}
 void ResetTimer(unsigned id,std::chrono::seconds value){assert(id==THADDIUS_ADD_REVIVE);timer=unsigned(value.count());}
 __GET_OTHER__
 __FAKE_DEATH__
};
__OLD_CLASSES__
int main(){
 ScriptedInstance instance;Creature feugen,stalagg,thaddius;stalagg.entry=NPC_STALAGG;
 for(auto c:{&feugen,&stalagg,&thaddius})c->instance=&instance;
 instance.creatures={{NPC_FEUGEN,&feugen},{NPC_STALAGG,&stalagg}};Unit attacker;
 Adds first(&feugen),second(&stalagg);Boss boss(&thaddius);
 assert(first.GetOtherAdd()==&stalagg&&second.GetOtherAdd()==&feugen);
 first.JustPreventedDeath(&attacker);
 assert(instance.state==IN_PROGRESS&&instance.changes==0&&first.deathCalls==0&&first.opened==0);
 assert(first.m_isFakingDeath&&first.script&&first.timer==10&&feugen.health==1&&feugen.stopped);
 assert(lastText==SAY_FEUG_DEATH&&textRecipient==&attacker&&textCount==1);
 second.JustPreventedDeath(&attacker);
 assert(instance.state==IN_PROGRESS&&instance.changes==0&&second.timer==10&&lastText==SAY_STAL_DEATH&&textCount==2);
 assert(feugen.despawns==0&&stalagg.despawns==0); // no premature completion/despawn
 Player living,dead,far;for(Player*p:{&living,&dead,&far})p->auras={28059,28084,29659,29660,12345};
 thaddius.map.players={{&living},{&dead},{nullptr},{&far}};
 boss.JustDied(&attacker);
 for(Player*p:{&living,&dead,&far})assert(p->auras==std::set<unsigned>{12345});
 assert(instance.state==DONE&&instance.changes==1&&boss.deathCalls==1&&boss.opened==2&&boss.closed==0);
 assert(feugen.despawns==1&&stalagg.despawns==1);
 instance.creatures.erase(NPC_STALAGG);assert(first.GetOtherAdd()==nullptr);
 Creature orphan;Adds outside(&orphan);assert(outside.GetOtherAdd()==nullptr);
 unsigned count=textCount;outside.JustPreventedDeath(&attacker);assert(textCount==count&&!outside.m_isFakingDeath&&outside.timer==0);
 Boss noInstance(&orphan);noInstance.JustDied(&attacker);assert(noInstance.deathCalls==1);
 __OLD_TESTS__
 std::cout<<"PASS: native Thaddius completion, reversible add deaths, text/timer preservation and missing-instance guards\n";
}
'''

for realm in ('classic', 'tbc', 'wotlk'):
    repo=root.parent/f'mangos-{realm}-behavior'
    area='northrend' if realm=='wotlk' else 'eastern_kingdoms'
    relative=f'src/game/AI/ScriptDevAI/scripts/{area}/naxxramas/boss_thaddius.cpp'
    source=(repo/relative).read_text()
    native=(repo/'src/game/AI/ScriptDevAI/base/BossAI.cpp').read_text()
    boss=block(source.split('struct boss_thaddiusAI :')[1], 'void JustDied(')
    adds=source.split('struct boss_thaddiusAddsAI :')[1]
    fake=block(adds,'void JustPreventedDeath(')
    other=block(adds,'Creature* GetOtherAdd() const')
    # Wrath has an interposed comment between signature and body; block retains it.
    code=fixture.replace('__NATIVE_BASE_DEATH__',block(native,'void BossAI::JustDied('))
    code=code.replace('__CLEAR_HELPER__',block(source,'static void ClearThaddiusPlayerCharges(')).replace('__CLEAR_PLAYERS__',block(source,'void ClearPlayerCharges()'))
    code=code.replace('__BOSS_DEATH__',boss).replace('__FAKE_DEATH__',fake).replace('__GET_OTHER__',other)
    old=subprocess.check_output(['git','-c',f'safe.directory={repo.as_posix()}','-C',str(repo),'show',f'HEAD:{relative}'],text=True)
    old_fake=block(old.split('struct boss_thaddiusAddsAI :')[1],'void JustPreventedDeath(')
    old_classes=old_tests=''
    if 'JustDied(attacker);' in old_fake:
        old_classes='struct OldAdds:Adds{using Adds::Adds;'+old_fake+'};'
        old_tests='instance.state=IN_PROGRESS;OldAdds oldAdd(&feugen);oldAdd.JustPreventedDeath(&attacker);assert(instance.state==DONE);'
    old_boss=block(old.split('struct boss_thaddiusAI :')[1],'void JustDied(')
    if 'BossAI::Aggro(killer);' in old_boss:
        old_classes+='struct OldBoss:Boss{using Boss::Boss;'+old_boss+'};'
        old_tests+='instance.state=DONE;OldBoss oldBoss(&thaddius);oldBoss.JustDied(&attacker);assert(instance.state==IN_PROGRESS);'
    code=code.replace('__OLD_CLASSES__',old_classes).replace('__OLD_TESTS__',old_tests)
    with tempfile.TemporaryDirectory(prefix=f'mantech-thaddius-{realm}-') as directory:
        tmp=Path(directory);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
    assert 'SetDataType(TYPE_THADDIUS)' in adds
print('PASS: native era-specific death handlers; previous false-completion/re-aggro defects reproduced when present in HEAD')
