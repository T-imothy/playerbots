from pathlib import Path
from turtle_cpp_fixture import run
r=Path(__file__).resolve().parents[1]/'playerbot'
s=(r/'EmoteSounds.cpp').read_text(encoding='utf-8');s=s[s.index('EmotesTextSoundEntry const* FindTextSoundEmoteFor('):]
run(r'''#include <map>
#include <tuple>
#include <cassert>
#include <cstdio>
using uint32=unsigned;
struct EmotesTextSoundEntry{uint32 SoundId;};
std::map<std::tuple<uint32,uint32,uint32>,EmotesTextSoundEntry const*> soundIndex;
'''+s+r'''
int main(){EmotesTextSoundEntry goblin{1},elfMale{2},elfFemale{3};soundIndex[{1,9,0}]=&goblin;soundIndex[{1,10,0}]=&elfMale;soundIndex[{1,10,1}]=&elfFemale;
assert(FindTextSoundEmoteFor(1,9,0)==&goblin);assert(FindTextSoundEmoteFor(1,10,0)==&elfMale);assert(FindTextSoundEmoteFor(1,10,1)==&elfFemale);assert(!FindTextSoundEmoteFor(1,9,1));assert(!FindTextSoundEmoteFor(99,10,0));soundIndex.clear();assert(!FindTextSoundEmoteFor(1,10,0));puts("PASS emote race/gender selection and missing-entry/data behavior");}
''')
