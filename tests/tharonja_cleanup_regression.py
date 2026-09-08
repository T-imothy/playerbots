"""Execute the native cleanup handler and boss lifecycle methods."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[2]/'mangos-wotlk-behavior'
s=(root/'src/game/AI/ScriptDevAI/scripts/northrend/draktharon_keep/boss_tharonja.cpp').read_text()
methods='\n'.join(block(s,needle).replace(' override','') for needle in ['    void ClearPlayerForms()', '    void Reset()', '    void JustDied(', '    void JustReachedHome()'])
phase=block(s[s.index('            case PHASE_RETURN_FLESH:'):],'if (DoCastSpellIfCan')
handler=block(s,'struct ClearGiftOfTharonja').replace(' override','')
code=r'''
#include <cassert>
#include <vector>
#include <map>
#include <iostream>
using uint32=unsigned;using SpellEffectIndex=unsigned;
enum{SPELL_GIFT_OF_THARONJA=52509,SPELL_CLEAR_GIFT_OF_THARONJA=53242,SPELL_ACHIEVEMENT_CHECK=61863,SAY_DEATH=1,CAST_TRIGGERED=2,CAST_FORCE_CAST=4,TYPE_THARONJA=1,DONE=3,FAIL=4,PHASE_SKELETAL=0,PHASE_SKELETAL_END=4,NPC_THARONJA_SKELETAL=26632,CAST_OK=0,EFFECT_INDEX_0=0,TYPEID_PLAYER=1};
unsigned urand(unsigned lo,unsigned){return lo;}
struct Unit{virtual ~Unit()=default;unsigned guid=77,type=2;std::map<unsigned,unsigned>gifts;unsigned GetObjectGuid(){return guid;}unsigned GetTypeId(){return type;}void RemoveAurasByCasterSpell(unsigned id,unsigned caster){assert(id==52509);gifts.erase(caster);}};
struct Player:Unit{Player(){type=TYPEID_PLAYER;}};
struct Ref{Player*p;Player*getSource()const{return p;}};
struct Map{std::vector<Ref>players;const std::vector<Ref>&GetPlayers(){return players;}};
struct CreatureInfo{};CreatureInfo info;CreatureInfo const*GetCreatureTemplateStore(unsigned){return &info;}
struct Creature:Unit{Map*map;unsigned display=9;Map*GetMap(){return map;}unsigned GetDisplayId(){return display;}void SetDisplayId(unsigned value){display=value;}static unsigned ChooseDisplayId(CreatureInfo const*){return 8;}};
struct Instance{unsigned state=0;void SetData(unsigned,unsigned value){state=value;}};
void DoScriptText(unsigned,Creature*){}
struct SpellScript{};struct Spell{Unit*caster,*target;Unit*GetCaster(){return caster;}Unit*GetUnitTarget(){return target;}};
struct AI{
 Creature*m_creature;Instance*m_pInstance;unsigned m_uiPhase=2,m_uiCurseLifeTimer,m_uiRainFireTimer,m_uiShadowVolleyTimer,m_uiLightningBreathTimer,m_uiEyeBeamTimer,m_uiPoisonCloudTimer,m_uiReturnFleshTimer;bool reject=false;unsigned checks=0;
 unsigned DoCastSpellIfCan(Creature*,unsigned id,unsigned=0){if(id==SPELL_ACHIEVEMENT_CHECK){++checks;assert(!m_creature->map->players[0].p->gifts.empty());}return reject?1:CAST_OK;}
 __METHODS__
 void ReturnFlesh(){__PHASE__}
};
__HANDLER__;
int main(){
 Player alive,dead,far;Map map{{{&alive},{&dead},{nullptr},{&far}}};Creature boss;boss.map=&map;Instance instance;AI ai{&boss,&instance};
 auto grant=[&](){for(Player*p:{&alive,&dead,&far}){p->gifts[77]=52509;p->gifts[88]=52509;}};
 auto clean=[&](){for(Player*p:{&alive,&dead,&far})assert(p->gifts.count(77)==0&&p->gifts.count(88)==1);};
 grant();ai.Reset();clean();assert(ai.m_uiPhase==PHASE_SKELETAL&&ai.m_uiReturnFleshTimer==26000);
 grant();ai.reject=true;ai.ReturnFlesh();assert(alive.gifts.count(77));ai.reject=false;ai.ReturnFlesh();clean();assert(ai.m_uiPhase==PHASE_SKELETAL_END&&boss.display==8);
 for(unsigned phase=0;phase<5;++phase){grant();ai.m_uiPhase=phase;ai.JustDied(nullptr);clean();assert(instance.state==DONE);}assert(ai.checks==5);
 grant();boss.display=9;ai.JustReachedHome();clean();assert(instance.state==FAIL&&boss.display==8);
 ClearGiftOfTharonja handler;Spell spell{&boss,&alive};grant();handler.OnEffectExecute(&spell,1);assert(alive.gifts.count(77));handler.OnEffectExecute(&spell,0);assert(!alive.gifts.count(77)&&alive.gifts.count(88));handler.OnEffectExecute(&spell,0);
 spell.target=&boss;boss.gifts[77]=52509;handler.OnEffectExecute(&spell,0);assert(boss.gifts.count(77));spell.target=nullptr;handler.OnEffectExecute(&spell,0);spell.caster=nullptr;handler.OnEffectExecute(&spell,0);
 std::cout<<"PASS: return cast retry, reset/death in every phase/home, achievement ordering, dead/out-of-range cleanup, caster isolation and handler guards\n";
}
'''.replace('__METHODS__',methods).replace('__PHASE__',phase).replace('__HANDLER__',handler)
with tempfile.TemporaryDirectory(prefix='tharonja-cleanup-') as folder:
 path=Path(folder);(path/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,check=True,timeout=60)
 subprocess.run([str(path/'test.exe')],cwd=path,check=True,timeout=20)
