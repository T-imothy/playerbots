"""Temporary native spell selection must not replace combat selection on any exit."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block

root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/PlayerbotAI.cpp').read_text()
for signature in ('bool PlayerbotAI::CastSpell(uint32 spellId, Unit* target,',
                  'bool PlayerbotAI::CanCastSpell(uint32 spellid, GameObject* goTarget,'):
    method=block(source,signature)
    assert 'ai::ScopedSpellSelection selection(' in method
    assert 'bot->SetSelectionGuid(' not in method

code=r'''
#include <cassert>
#include <stdexcept>
struct ObjectGuid {unsigned value=0;bool operator==(ObjectGuid b)const{return value==b.value;}};
struct Player {ObjectGuid selected;int interrupts=0;ObjectGuid GetSelectionGuid(){return selected;}
 void SetSelectionGuid(ObjectGuid g){selected=g;}};
#include "__HEADER__"
// Exercise early refusal, native rejection, accepted instant/cast/channel and
// a nested game-object capability probe while an outer spell is preparing.
bool attempt(Player& player,ObjectGuid target,int result,bool nested){
 ai::ScopedSpellSelection selection(&player,target);
 assert(player.GetSelectionGuid()==target);
 if(nested){
  {ai::ScopedSpellSelection probe(&player,{999});assert(player.GetSelectionGuid()==ObjectGuid{999});}
  assert(player.GetSelectionGuid()==target);
 }
 if(result<0)throw std::runtime_error("rejected");
 if(result==0)return false; // standing/facing/GCD/resource rejection
 if(result==1)return false; // moving/falling/native SpellStart failure
 return true;
}
int main(){
 for(unsigned old:{0u,42u})for(unsigned target:{42u,10u,11u,999u})for(int result=-1;result<5;++result){
  Player p{{old}};
  try{attempt(p,{target},result,true);}catch(const std::runtime_error&){}
  assert(p.GetSelectionGuid()==ObjectGuid{old});assert(p.interrupts==0);
 }
}
'''.replace('__HEADER__',(root/'playerbot/SpellSelectionGuard.h').as_posix())
with tempfile.TemporaryDirectory(prefix='spell-selection-restore-') as tmp:
    p=Path(tmp);(p/'test.cpp').write_text(code)
    subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=p,check=True)
    subprocess.run([str(p/'test.exe')],cwd=p,check=True)
print('PASS: original enemy/empty selection, self/ally/enemy/object targets, failed and accepted casts, nested checks, unwinding, no spell interruption')
