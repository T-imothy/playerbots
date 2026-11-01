"""Exercise local item target construction against the actual Classic native writer."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/tests/CommandRaidLab.cpp').read_text()
native=(root.parent/'classic/src/game/Spells/Spell.cpp').read_text()
code=r'''
#include <cassert>
#include <cstdint>
#include <string>
#include <vector>
#include <iostream>
using uint16=uint16_t;using uint8=uint8_t;
constexpr unsigned TARGET_FLAG_UNIT=2,TARGET_FLAG_CORPSE_ENEMY=512,TARGET_FLAG_GAMEOBJECT=2048,TARGET_FLAG_CORPSE_ALLY=32768,TARGET_FLAG_UNIT_MINIPET=65536,
 TARGET_FLAG_LOCKED=16384,TARGET_FLAG_ITEM=16,TARGET_FLAG_TRADE_ITEM=4096,TARGET_FLAG_SOURCE_LOCATION=32,TARGET_FLAG_DEST_LOCATION=64,TARGET_FLAG_STRING=8192;
struct Guid{unsigned id=91;unsigned WriteAsPacked()const{return id;}};
struct GameObject{Guid guid;Guid GetObjectGuid(){return guid;}unsigned GetPackGUID(){return guid.id;}};
struct ByteBuffer{std::vector<unsigned long long>fields;template<class T>ByteBuffer&operator<<(T x){fields.push_back((unsigned long long)x);return *this;}
 ByteBuffer&operator<<(const std::string&x){fields.push_back(x.size());return *this;}};
struct SpellCastTargets{unsigned m_targetMask=0;GameObject*m_GOTarget=nullptr,*m_unitTarget=nullptr,*m_itemTarget=nullptr;Guid m_GOTargetGUID,m_CorpseTargetGUID;
 struct Point{float x=0,y=0,z=0;}m_srcPos,m_destPos;std::string m_strTarget;
 void setGOTarget(GameObject*);void write(ByteBuffer&)const;};
'''+block(native,'void SpellCastTargets::setGOTarget(')+block(native,'void SpellCastTargets::write(')+block(source,'SpellCastTargets RaidLabNativeItemTargets(')+r'''
int main(){
 GameObject brazier;SpellCastTargets old;old.setGOTarget(&brazier);ByteBuffer rejected;old.write(rejected);
 assert(rejected.fields.size()==1&&rejected.fields[0]==0); // Reproduce the empty old packet.
 auto target=RaidLabNativeItemTargets(&brazier);ByteBuffer packet;target.write(packet);
 assert(target.m_GOTarget==&brazier&&packet.fields.size()==2&&packet.fields[0]==TARGET_FLAG_GAMEOBJECT&&packet.fields[1]==91);
 auto itemOnly=RaidLabNativeItemTargets(nullptr);ByteBuffer untouched;itemOnly.write(untouched);
 assert(untouched.fields.size()==1&&untouched.fields[0]==0);
 std::cout<<"PASS native Classic item writer includes selected brazier; old missing-mask packet reproduced; targetless lure preserved\n";
}
'''
assert 'SpellCastTargets targets=RaidLabNativeItemTargets(object);' in block(source,'TestResult CommandRaidLabEvent::Execute(')
with tempfile.TemporaryDirectory(prefix='raid-item-packet-') as folder:
 path=Path(folder);(path/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,check=True)
 subprocess.run([str(path/'test.exe')],cwd=path,check=True)
