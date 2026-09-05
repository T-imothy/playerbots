"""Compile actual changed C++ bodies against controlled interfaces.

Run in an MSVC developer shell with --core pointing to each matching core.
No realm, database, characters, or production files are modified.
"""
import argparse
import subprocess
import tempfile
from pathlib import Path


def block(text, marker):
    start = text.index(marker)
    opening = text.index('{', start)
    depth = 0
    for i in range(opening, len(text)):
        depth += (text[i] == '{') - (text[i] == '}')
        if depth == 0:
            return text[start:i + 1]
    raise ValueError(marker)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--core', type=Path, required=True)
    parser.add_argument('--wrath', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    source = (root / 'playerbot/strategy/actions/CheckMailAction.cpp').read_text()
    mail = block(source, 'bool CheckMailAction::ProcessMail(')
    core_mail = (args.core / 'src/game/Mails/Mail.cpp').read_text()
    replacement = block(core_mail, 'if (m_returnSourceMailId)')
    send = core_mail[core_mail.index('void MailDraft::SendMailTo'):]
    assert send.index('CharacterDatabase.BeginTransaction()') < send.index('if (m_returnSourceMailId)') < send.index('CharacterDatabase.CommitTransaction()')
    travel = (root / 'playerbot/strategy/actions/ChooseTravelTargetAction.cpp').read_text()
    cleanup = block(travel, 'for (auto i = ignoreList.begin();')
    code = r'''
#include <cassert>
#include <ctime>
#include <cstdint>
#include <iostream>
#include <map>
#include <set>
#include <string>
#include <vector>
using uint32 = uint32_t;
enum { HIGHGUID_PLAYER=1, MAIL_NORMAL=0, MAIL_STATE_DELETED=2,
       MAIL_CHECK_MASK_RETURNED=2, MAIL_RETURNED_TO_SENDER=3, MAIL_OK=0 };
struct ObjectGuid {
    uint32 id=0;
    ObjectGuid()=default;
    ObjectGuid(int, uint32 value):id(value){}
    bool operator==(ObjectGuid b) const {return id==b.id;}
    uint32 GetEntry() const {return id;}
    bool operator<(ObjectGuid b) const {return id<b.id;}
};
struct Item { uint32 id; };
struct MailItemInfo {uint32 item_guid;};
struct Mail {
    int state=0, messageType=MAIL_NORMAL;
    std::time_t deliver_time=0;
    uint32 sender=7, mailTemplateId=0, checked=0, money=0, messageID=42, itemTextId=0;
    std::string subject="gift", body="body";
    std::vector<MailItemInfo> items;
};
struct ObjectMgr { uint32 account=100; uint32 GetPlayerAccountIdByGUID(ObjectGuid){return account;} } sObjectMgr;
struct Config {bool random=false; bool IsInRandomAccountList(uint32){return random;} } sPlayerbotAIConfig;
struct Session {uint32 GetAccountId(){return 200;} };
struct Player {
    std::map<uint32,Item> items;
    uint32 removed=0, reported=0;
    Session session;
    ObjectGuid GetObjectGuid(){return {HIGHGUID_PLAYER,9};}
    Item* GetMItem(uint32 id){auto it=items.find(id);return it==items.end()?nullptr:&it->second;}
    void RemoveMItem(uint32 id){items.erase(id);}
    void RemoveMail(uint32 id){removed=id;}
    Session* GetSession(){return &session;}
    void SendMailResult(uint32 id,int,int){reported=id;}
};
struct Capture {uint32 money=0, original=0, receiver=0; std::vector<uint32> items;} capture;
struct MailDraft {
    void SetSubjectAndBody(std::string,std::string){}
    void SetSubjectAndBodyId(std::string,uint32){}
    void AddItem(Item* i){capture.items.push_back(i->id);}
    MailDraft& SetMoney(uint32 n){capture.money=n;return *this;}
    MailDraft& SetReturnSourceMailId(uint32 n){capture.original=n;return *this;}
    void SendReturnToSender(uint32,ObjectGuid,ObjectGuid to){capture.receiver=to.id;}
};
struct CheckMailAction {Player* bot; bool ProcessMail(Mail*);};
__MAIL__
struct Db {
    bool transaction=false; uint32 deletes=0;
    void BeginTransaction(){transaction=true;}
    void PExecute(const char*,uint32 id){assert(transaction && id==42);++deletes;}
} CharacterDatabase;
void replaceSource(uint32 m_returnSourceMailId) { __REPLACE__ }
struct Target {uint32 GetEntry(){return 10;}};
void clearIgnore(std::set<ObjectGuid>& ignoreList, Target* newTarget) { __CLEANUP__ }
int main() {
    Player player; CheckMailAction action{&player};
    auto reset=[&](){player=Player{};capture=Capture{};sObjectMgr.account=100;sPlayerbotAIConfig.random=false;};
    auto preserve=[&](Mail* mail){assert(!action.ProcessMail(mail));assert(player.removed==0 && capture.original==0);delete mail;};
    // Money-only mail must return money instead of deleting it.
    Mail* mail=new Mail;mail->money=12345;
    assert(action.ProcessMail(mail));assert(capture.money==12345 && capture.original==42 && capture.receiver==7);
    assert(player.removed==42 && player.reported==42);
    // All attachments and money travel together. Offline sender has metadata only.
    reset();mail=new Mail;mail->items={{1},{2},{3}};mail->money=99;
    player.items={{1,{1}},{2,{2}},{3,{3}}};
    assert(action.ProcessMail(mail));assert(capture.items.size()==3 && capture.money==99 && player.items.empty());
    // Missing one attachment must preserve every attachment and the original.
    reset();mail=new Mail;mail->items={{1},{2}};player.items={{1,{1}}};preserve(mail);assert(player.items.size()==1);
    reset();mail=new Mail;preserve(mail); // text only
    reset();mail=new Mail;mail->money=9;mail->checked=MAIL_CHECK_MASK_RETURNED;preserve(mail);
    reset();mail=new Mail;mail->money=9;mail->subject="Item(s) you asked for";preserve(mail);
    reset();mail=new Mail;mail->money=9;mail->messageType=3;preserve(mail);
    reset();mail=new Mail;mail->money=9;mail->deliver_time=std::time(nullptr)+3600;preserve(mail);
    reset();mail=new Mail;mail->money=9;sObjectMgr.account=0;preserve(mail);
    reset();mail=new Mail;mail->money=9;sPlayerbotAIConfig.random=true;preserve(mail);
    reset();mail=new Mail;mail->money=9;mail->sender=9;preserve(mail);
    CharacterDatabase.BeginTransaction();replaceSource(0);assert(CharacterDatabase.deletes==0);
    replaceSource(42);assert(CharacterDatabase.deletes==2);
    std::set<ObjectGuid> ignored={{1,10},{1,11},{1,12}};Target target;
    clearIgnore(ignored,&target);assert(ignored.size()==2 && !ignored.count({1,10}));
    clearIgnore(ignored,&target);assert(ignored.size()==2);
    std::cout << "PASS: actual mail bodies, transaction placement, and travel ignore cleanup\n";
}
'''.replace('__MAIL__', mail).replace('__REPLACE__', replacement).replace('__CLEANUP__', cleanup)
    with tempfile.TemporaryDirectory(prefix='mantech-behavior-') as tmp:
        tmp = Path(tmp)
        (tmp/'test.cpp').write_text(code)
        command = ['cl', '/nologo', '/std:c++17', '/EHsc', '/W3', 'test.cpp', '/Fe:test.exe']
        if args.wrath:
            command.insert(1, '/DMANGOSBOT_TWO')
        subprocess.run(command, cwd=tmp, check=True)
        subprocess.run([str(tmp/'test.exe')], cwd=tmp, check=True)


if __name__ == '__main__':
    main()
