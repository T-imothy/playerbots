#pragma once
#include <sstream>
#include <string>

namespace ai {
struct TacticalCommand {
    std::string intent,mark,id;
    int markIndex=-1;
    bool Parse(std::string const& text) {
        *this={}; markIndex=-1;
        if(text.size()>160) return false;
        std::istringstream in(text);std::string prefix,extra;
        in>>prefix>>intent;
        if(prefix!="action" || (intent!="interrupt" && intent!="cc")) return false;
        if(intent=="cc") {
            in>>mark;
            const char* marks[]={"star","circle","diamond","triangle","moon","square","cross","skull"};
            for(int i=0;i<8;++i) if(mark==marks[i]) markIndex=i;
            if(markIndex<0) return false;
        }
        in>>id;
        if(in>>extra) return false;
        return id.size()<=32 && id.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")==std::string::npos;
    }
};
}
