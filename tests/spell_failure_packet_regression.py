"""Feed each core's actual interruption packet writer into the actual bot handler."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
repo=Path(__file__).resolve().parents[1]
handler=block((repo/'playerbot/PlayerbotAI.cpp').read_text(),'case SMSG_SPELL_FAILURE:')
for era,define in (('classic','ZERO'),('tbc','ONE'),('wotlk','TWO')):
    native=repo.parent/f'mangos-{era}-behavior/src/game/Spells/Spell.cpp'
    writer=block(native.read_text(),'void Spell::SendInterrupted(')
    code=r'''
#include <cassert>
#include <cstdint>
#include <iostream>
#include <vector>
using uint8=uint8_t;using uint32=uint32_t;using uint64=uint64_t;
enum{SMSG_SPELL_FAILURE=1,SMSG_SPELL_FAILED_OTHER=2};
enum SpellCastResult{SPELL_FAILED_INTERRUPTED=15};
struct ObjectGuid;
struct PackedWrite{uint64 value;};struct PackedRead{ObjectGuid*guid;};
struct ObjectGuid{uint64 value=0;PackedRead ReadAsPacked(){return {this};}bool operator!=(const ObjectGuid&other)const{return value!=other.value;}};
struct WorldPacket{
 unsigned opcode;std::vector<uint8>data;size_t pos=0;
 WorldPacket(unsigned op,unsigned):opcode(op){}unsigned GetOpcode()const{return opcode;}
 void Initialize(unsigned op,unsigned){opcode=op;data.clear();pos=0;}void rpos(size_t n){pos=n;}
 template<class T>WorldPacket&operator<<(T v){for(unsigned i=0;i<sizeof(T);++i)data.push_back(uint8(uint64(v)>>(8*i)));return *this;}
 template<class T>WorldPacket&operator>>(T&v){assert(pos+sizeof(T)<=data.size());v=0;for(unsigned i=0;i<sizeof(T);++i)v|=T(data[pos++])<<(8*i);return *this;}
 WorldPacket&operator<<(ObjectGuid guid){return *this<<guid.value;}
 WorldPacket&operator<<(PackedWrite packed){uint8 mask=0;for(unsigned i=0;i<8;++i)if(uint8(packed.value>>(8*i)))mask|=uint8(1<<i);*this<<mask;for(unsigned i=0;i<8;++i)if(mask&(1<<i))*this<<uint8(packed.value>>(8*i));return *this;}
 WorldPacket&operator>>(PackedRead packed){uint8 mask;*this>>mask;packed.guid->value=0;for(unsigned i=0;i<8;++i)if(mask&(1<<i)){uint8 part;*this>>part;packed.guid->value|=uint64(part)<<(8*i);}return *this;}
};
struct Unit{ObjectGuid guid;std::vector<WorldPacket>packets;PackedWrite GetPackGUID(){return {guid.value};}ObjectGuid GetObjectGuid(){return guid;}
 void SendMessageToSet(const WorldPacket&packet,bool self){assert(self);packets.push_back(packet);}};
struct SpellEntry{uint32 Id;};
struct Spell{Unit*m_trueCaster;SpellEntry*m_spellInfo;uint8 m_cast_count;void SendInterrupted(SpellCastResult)const;};
__WRITER__
struct PlayerbotAI{Unit*bot;std::vector<unsigned>notifications;void SpellInterrupted(unsigned spell){notifications.push_back(spell);}
 void Handle(const WorldPacket&packet){switch(packet.GetOpcode()){__HANDLER__}}};
int main(){
 for(uint64 guid:{uint64(1),uint64(0x00000000AB00EF01),uint64(0xFFFF000000000001)})
 for(unsigned count:{0u,1u,255u})for(unsigned id:{1u,2061u,66013u}){
  Unit bot;bot.guid.value=guid;SpellEntry entry{id};Spell spell{&bot,&entry,uint8(count)};PlayerbotAI ai{&bot};
  spell.SendInterrupted(SPELL_FAILED_INTERRUPTED);assert(bot.packets.size()==2);
  ai.Handle(bot.packets[0]);assert((ai.notifications==std::vector<unsigned>{id}));
  ai.Handle(bot.packets[1]);assert(ai.notifications.size()==1);
  bot.guid.value^=0x100;ai.Handle(bot.packets[0]);assert(ai.notifications.size()==1);
 }
 std::cout<<"PASS native interruption packet to bot handler, packed GUIDs and cast counters\n";
}
'''.replace('__WRITER__',writer).replace('__HANDLER__',handler)
    with tempfile.TemporaryDirectory(prefix='mantech-spell-failure-packet-') as directory:
        tmp=Path(directory);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+define,'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
