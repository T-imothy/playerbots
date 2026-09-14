"""Exercise actual core chat builders against the unchanged module decoder.

The fixture implements scalar/string packet transport, not a realm session.
Opcode/type constants are distinct fixture values; field order/width, channel
and sender extraction come from production source in the selected core/module.
"""
from pathlib import Path
import argparse,re
p=argparse.ArgumentParser()
p.add_argument('--core',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();r=Path(__file__).resolve().parents[2]
s=(r/'playerbot/PlayerbotAI.cpp').read_text(encoding='utf-8')
start=s.index('    case SMSG_MESSAGECHAT:',s.index('void PlayerbotAI::HandleBotOutgoingPacket'))
end=s.index('            // Most bot-to-bot broadcasts',start)
decoder=s[start:end]
assert decoder.rstrip()==(r/'tests/chat/ChatPacketReference.inc').read_text(encoding='utf-8').rstrip(), 'Packet decoding drift'
source=(a.core/'src/game/Chat/Chat.cpp').read_text(encoding='utf-8')
start=source.index('void ChatHandler::BuildChatPacket(')
end=source.index('\n/// Create an account',start)
builder=source[start:end].replace('ChatHandler::BuildChatPacket','BuildChatPacket')
builder=re.sub(r'/\*=(.*?)\*/',r'=\1',builder)
enums=sorted(set(re.findall(r'\b(?:CHAT_MSG_\w+|SMSG_\w+|LANG_\w+|CHAT_TAG_\w+)\b',builder+decoder)) | {'LANG_ADDON'})
prefix=r'''
#include <cassert>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <string>
#include <vector>
using uint8=uint8_t;using uint32=uint32_t;using uint64=uint64_t;
using ChatMsg=int;using Language=int;using ChatTagFlags=int;
#define MANGOS_ASSERT assert
struct ObjectGuid{uint64 value=0;ObjectGuid()=default;explicit ObjectGuid(uint64 n):value(n){}bool IsEmpty()const{return !value;}bool IsPlayer()const{return true;}bool IsPet()const{return false;}explicit operator bool()const{return value!=0;}};
struct WorldPacket{
 std::vector<uint8> bytes;size_t pos=0;int opcode=0;
 void Initialize(int op){bytes.clear();pos=0;opcode=op;}int GetOpcode()const{return opcode;}
 bool empty()const{return bytes.empty();}size_t size()const{return bytes.size();}void rpos(size_t n){pos=n;}
 template<class T>WorldPacket& operator<<(T n){for(size_t i=0;i<sizeof(T);++i)bytes.push_back(uint8(uint64(n)>>(i*8)));return *this;}
 WorldPacket& operator<<(ObjectGuid n){return *this<<n.value;}
 WorldPacket& operator<<(char const* s){do{bytes.push_back(uint8(*s));}while(*s++);return *this;}
 template<class T>WorldPacket& operator>>(T& n){assert(pos+sizeof(T)<=bytes.size());uint64 v=0;for(size_t i=0;i<sizeof(T);++i)v|=uint64(bytes[pos++])<<(i*8);n=T(v);return *this;}
 WorldPacket& operator>>(ObjectGuid& n){return *this>>n.value;}
 WorldPacket& operator>>(std::string& s){s.clear();for(;;){assert(pos<bytes.size());char c=char(bytes[pos++]);if(!c)break;s+=c;}return *this;}
};
'''
prefix+='enum {CHAT_TAG_NONE=0,CHAT_TAG_GM=1,'+','.join(x for x in enums if x not in ('CHAT_TAG_NONE','CHAT_TAG_GM'))+'};\n'
decode=r'''
bool accepted=false;uint64 sender=0;std::string decodedMessage,decodedChannel;bool active=true;
bool AllowActivity(){return active;}
void Decode(WorldPacket const& packet){switch(packet.GetOpcode()){
'''+decoder+r'''
 accepted=true;sender=guid1.value;decodedMessage=message;decodedChannel=chanName;
 } return; } default:return;}}
'''
main=r'''
int main(){unsigned cases=0;
for(int type:{CHAT_MSG_CHANNEL,CHAT_MSG_SAY,CHAT_MSG_PARTY,CHAT_MSG_YELL,CHAT_MSG_WHISPER,CHAT_MSG_GUILD
#ifdef MANGOSBOT_TWO
,CHAT_MSG_PARTY_LEADER
#endif
})for(auto text:{"hello","Recipient |Hitem:19019:0|h[Thunderfury]|h","d:debug"})for(auto language:{LANG_UNIVERSAL,LANG_ADDON}){
 WorldPacket packet;BuildChatPacket(packet,type,text,language,CHAT_TAG_NONE,ObjectGuid(12345),"Sender",ObjectGuid(67890),"Recipient","World");
 accepted=false;active=true;Decode(packet);assert(accepted&&sender==12345&&decodedMessage==text&&decodedChannel==(type==CHAT_MSG_CHANNEL?"World":""));++cases;
 active=false;accepted=false;Decode(packet);assert(!accepted);++cases;
 active=true;packet.bytes.resize(0x1001);accepted=false;Decode(packet);assert(!accepted);++cases;
}
WorldPacket empty;empty.Initialize(SMSG_MESSAGECHAT);accepted=false;Decode(empty);assert(!accepted);
WorldPacket missing;BuildChatPacket(missing,CHAT_MSG_SAY,"hello",LANG_UNIVERSAL,CHAT_TAG_NONE,ObjectGuid(),"Sender",ObjectGuid(),"Recipient","World");accepted=false;Decode(missing);assert(!accepted);
std::cout<<"PASS "<<cases+2<<" native builder/decoder field, channel, sender, activity and size cases\n";
}
'''
a.output.parent.mkdir(parents=True,exist_ok=True)
a.output.write_text(prefix+builder+decode+main,encoding='utf-8')
