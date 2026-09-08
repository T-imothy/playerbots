"""Execute native proc-mask admission and the real Icy Blast summon effect."""
from pathlib import Path
import subprocess,tempfile,re
from behavior_regression import block
root=Path(__file__).resolve().parents[2]
core=root/'mangos-wotlk-behavior/src/game'
source=(core/'AI/ScriptDevAI/scripts/northrend/icecrown_citadel/frozen_halls/pit_of_saron/boss_scourgelord_tyrannus.cpp').read_text()
header=(core/'Spells/SpellMgr.h').read_text();mgr=(core/'Spells/SpellMgr.cpp').read_text()
proc=block(mgr,'bool SpellMgr::IsSpellProcEventCanTriggeredBy(').replace('SpellMgr::','')
sql=(root/'wotlk-db-behavior/Updates/5879_tyrannus_overlords_brand.sql').read_text()
flags,extra=re.search(r'\(69172, (0x[0-9A-Fa-f]+), (0x[0-9A-Fa-f]+)\)',sql).groups()
code=r'''
#include <cassert>
#include <iostream>
using uint32=unsigned;using int32=int;
enum{SPELL_SCHOOL_MASK_NORMAL=1,EFFECT_INDEX_1=1,TEMPSPAWN_TIMED_DESPAWN=7};
using SpellEffectIndex=unsigned;
__FLAGS__
__EXTRA__
struct SpellEntry{unsigned Id=0,SpellFamilyName=1,SchoolMask=1;int duration=60000;};
struct SpellProcEventEntry{unsigned procEx=__SQL_EXTRA__,schoolMask=0,spellFamilyName=0;};
__PROC__
__ENUM__
struct Unit{unsigned summons=0,type=0,lifetime=0;float x=0,y=0,z=0;
 void SummonCreature(unsigned entry,float a,float b,float c,int,unsigned t,unsigned life){
  assert(entry==NPC_ICY_BLAST);++summons;type=t;lifetime=life;x=a;y=b;z=c;
 }
};
struct SpellScript{};
struct Targets{void getDestination(float&x,float&y,float&z){x=10;y=20;z=30;}};
struct Spell{Unit*caster;Targets m_targets;Unit*GetAffectiveCaster(){return caster;}};
SpellEntry blast;bool missing=false;
struct Store{template<class T>const T*LookupEntry(unsigned id){assert(id==SPELL_ICY_BLAST_AURA);return missing?nullptr:&blast;}}sSpellTemplate;
int GetSpellDuration(const SpellEntry*s){return s->duration;}
__ICY__
int main(){
 SpellProcEventEntry event;SpellEntry spell;const unsigned flags=__SQL_FLAGS__;
 for(unsigned type:{PROC_FLAG_DEAL_MELEE_SWING,PROC_FLAG_DEAL_MELEE_ABILITY,PROC_FLAG_DEAL_RANGED_ATTACK,
  PROC_FLAG_DEAL_RANGED_ABILITY,PROC_FLAG_DEAL_HELPFUL_ABILITY,PROC_FLAG_DEAL_HARMFUL_ABILITY,
  PROC_FLAG_DEAL_HELPFUL_SPELL,PROC_FLAG_DEAL_HARMFUL_SPELL,PROC_FLAG_DEAL_HARMFUL_PERIODIC}){
  for(unsigned hit:{PROC_EX_NORMAL_HIT,PROC_EX_CRITICAL_HIT})assert(IsSpellProcEventCanTriggeredBy(&event,flags,&spell,type,hit));
  for(unsigned miss:{PROC_EX_MISS,PROC_EX_RESIST,PROC_EX_IMMUNE,PROC_EX_CAST_END})assert(!IsSpellProcEventCanTriggeredBy(&event,flags,&spell,type,miss));
 }
 assert(IsSpellProcEventCanTriggeredBy(&event,flags,&spell,PROC_FLAG_DEAL_HARMFUL_PERIODIC,PROC_EX_NORMAL_HIT|PROC_EX_INTERNAL_HOT|PROC_EX_PERIODIC_POSITIVE));
 for(unsigned type:{PROC_FLAG_TAKE_MELEE_SWING,PROC_FLAG_TAKE_HARMFUL_SPELL,PROC_FLAG_TAKE_HELPFUL_SPELL,PROC_FLAG_TAKE_HARMFUL_PERIODIC,PROC_FLAG_KILL,PROC_FLAG_DEATH})
  assert(!IsSpellProcEventCanTriggeredBy(&event,flags,&spell,type,PROC_EX_NORMAL_HIT));
 assert(IsSpellProcEventCanTriggeredBy(&event,flags,nullptr,PROC_FLAG_DEAL_MELEE_SWING,PROC_EX_NORMAL_HIT));
 Unit caster;Spell cast{&caster};spell_icy_blast icy;
 for(int duration:{30000,60000}){blast.duration=duration;icy.OnEffectExecute(&cast,EFFECT_INDEX_1);assert(caster.type==TEMPSPAWN_TIMED_DESPAWN&&caster.lifetime==duration);}
 assert(caster.summons==2&&caster.x==10&&caster.y==20&&caster.z==30);
 for(int duration:{0,-1}){blast.duration=duration;icy.OnEffectExecute(&cast,EFFECT_INDEX_1);}assert(caster.summons==2);
 blast.duration=60000;missing=true;icy.OnEffectExecute(&cast,EFFECT_INDEX_1);assert(caster.summons==2);missing=false;
 icy.OnEffectExecute(&cast,0);assert(caster.summons==2);cast.caster=nullptr;icy.OnEffectExecute(&cast,EFFECT_INDEX_1);assert(caster.summons==2);
 std::cout<<"PASS: actual native proc mask for attacks/spells/DoT/HoT and negative cases; Icy Blast timed actor follows spell duration\n";
}
'''.replace('__FLAGS__',block(header,'enum ProcFlags :')+';').replace('__EXTRA__',block(header,'enum ProcFlagsEx')+';').replace('__PROC__',proc).replace('__ENUM__',block(source,'enum\n')+';').replace('__ICY__',block(source,'struct spell_icy_blast').replace(' override','')+';').replace('__SQL_FLAGS__',flags).replace('__SQL_EXTRA__',extra)
with tempfile.TemporaryDirectory(prefix='tyrannus-spell-data-') as directory:
    p=Path(directory);(p/'test.cpp').write_text(code)
    subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True)
    subprocess.run([str(p/'test.exe')],cwd=p,check=True)
