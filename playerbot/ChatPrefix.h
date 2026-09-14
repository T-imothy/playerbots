#pragma once
#include <locale>
#include <string_view>

namespace ai { namespace chat {
// The realm does not change the C++ global locale at runtime. Pin its facet
// once per thread: std::toupper(ch, locale) and Boost's default predicate call
// use_facet for each byte, serializing broadcast recipients on MSVC's locale lock.
inline bool HasInsensitivePrefix(std::string_view text, std::string_view prefix)
{
    if (prefix.size() > text.size()) return false;
    if (prefix.empty()) return true;
    static thread_local std::locale const locale;
    static thread_local std::ctype<char> const& facet = std::use_facet<std::ctype<char>>(locale);
    for (size_t i = 0; i < prefix.size(); ++i)
        if (facet.toupper(text[i]) != facet.toupper(prefix[i])) return false;
    return true;
}
}}
