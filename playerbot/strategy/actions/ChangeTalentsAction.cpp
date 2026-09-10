
#include "playerbot/playerbot.h"
#include "playerbot/Talentspec.h"
#include "ChangeTalentsAction.h"
#include "playerbot/AiFactory.h"

#include <limits>

using namespace ai;

bool ChangeTalentsAction::Execute(Event& event)
{
    Player* requester = event.getOwner() ? event.getOwner() : GetMaster();
    std::ostringstream out;
    TalentSpec botSpec(bot);
    uint8 cls = bot->getClass();
    std::string param = event.getParam();

    if (!param.empty())
    {
        if (param.find("auto") != std::string::npos)
        {
            AutoSelectTalents(bot, &out);
        }
        else  if (param.find("list ") != std::string::npos)
        {
            listPremadePaths(cls,getPremadePaths(cls, param.substr(5)), &out);
        }
        else  if (param.find("list") != std::string::npos)
        {
            listPremadePaths(cls, getPremadePaths(cls, ""), &out);
        }
        else if (param.find("reset") != std::string::npos)
        {
            out << "Reset talents and spec";
            TalentSpec newSpec(bot, "0-0-0");
            newSpec.ApplyTalents(bot, &out);
            sRandomPlayerbotMgr.SetValue(bot->GetGUIDLow(), "specNo", 0);
            sRandomPlayerbotMgr.SetValue(bot->GetGUIDLow(), "specLink", 0);
        }
        else
        {
            bool crop = false;
            bool shift = false;
            if (param.find("do ") != std::string::npos)
            {
                crop = true;
                param = param.substr(3);
            }
            else if (param.find("shift ") != std::string::npos)
            {
                shift = true;
                param = param.substr(6);
            }

            out << "Apply talents [" << param << "] ";
            if (botSpec.CheckTalentLink(param, &out))
            {
                TalentSpec newSpec(bot, param);
                std::string specLink = newSpec.GetTalentLink();

                if (crop)
                {
                    newSpec.CropTalents(bot);
                    out << "becomes: " << newSpec.GetTalentLink();
                }

                if (shift)
                {
                    TalentSpec botSpec(bot);
                    newSpec.ShiftTalents(&botSpec, bot);
                    out << "becomes: " << newSpec.GetTalentLink();
                }

                if (newSpec.CheckTalents(bot, &out))
                {
                    newSpec.ApplyTalents(bot, &out);
                    sRandomPlayerbotMgr.SetValue(bot->GetGUIDLow(), "specNo", 0);
                    sRandomPlayerbotMgr.SetValue(bot->GetGUIDLow(), "specLink", 1, specLink);
                }

                ai->UpdateTalentSpec();
            }
            else
            {
                std::vector<TalentPath*> paths = getPremadePaths(bot->getClass(), param);
                if (paths.size() > 0)
                {
                    out.str("");
                    out.clear();

                    if (paths.size() > 1 && sPlayerbotAIConfig.autoPickTalents != "full")
                    {
                        out << "Found multiple specs: ";
                        listPremadePaths(cls, paths, &out);
                    }
                    else
                    {
                        if (paths.size() > 1)
                            out << "Found " << paths.size() << " possible specs to choose from. ";
                        
                        TalentPath* path = PickPremadePath(paths, sRandomPlayerbotMgr.IsRandomBot(bot));
                        TalentSpec newSpec = *GetBestPremadeSpec(bot, path->id);
                        std::string specLink = newSpec.GetTalentLink();
                        newSpec.CropTalents(bot);
                        newSpec.ApplyTalents(bot, &out);

                        if (newSpec.GetTalentPoints() > 0)
                        {
                            out << "Apply spec " << "|h|cffffffff" << path->name << " " << newSpec.formatSpec(cls);
                            sRandomPlayerbotMgr.SetValue(bot->GetGUIDLow(), "specNo", path->id + 1);
                            sRandomPlayerbotMgr.SetValue(bot->GetGUIDLow(), "specLink", 0);

                            ai->UpdateTalentSpec();
                        }
                    }
                }
            }
        }

        // learn available spells
        ai->DoSpecificAction("auto learn spell");
    }
    else
    {
        botSpec.ApplyTalents(bot, &out);
        out.str("");
        out.clear();

        uint32 specId = sRandomPlayerbotMgr.GetValue(bot->GetGUIDLow(), "specNo") - 1;
        std::string specName = "";
        TalentPath* specPath;
        if (specId)
        {
            specPath = getPremadePath(bot->getClass(), specId);

            if (!specPath)
            {
                ai->TellPlayer(requester, "Default talent spec for this class was not fount. Please check your config",PlayerbotSecurityLevel::PLAYERBOT_SECURITY_ALLOW_ALL, false);
                return false;
            }


            if (specPath->id == specId)
                specName = specPath->name;
        }

        out << "My current talent spec is: " << "|h|cffffffff";

        if (specName != "")
            out << specName << " (" << botSpec.formatSpec(cls) << ")";
        else
            out << chat->formatClass(bot, botSpec.highestTree());

        out << " Link: ";
        out << botSpec.GetTalentLink();
    }

    ai->TellPlayer(requester, out, PlayerbotSecurityLevel::PLAYERBOT_SECURITY_ALLOW_ALL, false);

    return true;
}

std::vector<TalentPath*> ChangeTalentsAction::getPremadePaths(uint8 cls, std::string findName, BotRoles role)
{
    std::vector<TalentPath*> ret;
    for (auto& path : sPlayerbotAIConfig.classSpecs[cls].talentPath)
    {
        if (!findName.empty() && path.name.find(findName) == std::string::npos)
            continue;

        if (role != BotRoles::BOT_ROLE_NONE && !(AiFactory::GetPlayerRoles(cls, path.talentSpec.back().highestTree()) & role))
            continue;

        ret.push_back(&path);
    }

    return ret;
}

bool ChangeTalentsAction::HasPremadeRole(uint8 cls, BotRoles role)
{
    return !getPremadePaths(cls, "", role).empty();
}

std::string ChangeTalentsAction::GetPremadeSpecName(Player* bot)
{
    if (!bot) return "";
    uint32 specNo = sRandomPlayerbotMgr.GetValue(bot->GetGUIDLow(), "specNo");
    if (!specNo) return "";
    TalentPath* path = getPremadePath(bot->getClass(), (int)specNo - 1);
    return path ? path->name : "";
}

bool ChangeTalentsAction::ApplyPremadePath(Player* bot, uint32 pathId, std::ostringstream* out)
{
    if (!bot || bot->GetLevel() < 10) return false;
    TalentPath* path = getPremadePath(bot->getClass(), pathId);
    if (!path || (uint32)path->id != pathId) return false;
    TalentSpec* best = GetBestPremadeSpec(bot, path->id);
    if (!best) return false;
    std::ostringstream ignored;
    std::ostringstream* details = out ? out : &ignored;
    bot->resetTalents(true);
    TalentSpec spec = *best;
    spec.CropTalents(bot);
    spec.ApplyTalents(bot, details);
    const int32 persistentSpecSeconds = 10 * 365 * 24 * 60 * 60;
    sRandomPlayerbotMgr.SetValue(bot->GetGUIDLow(), "specNo", path->id + 1, "", persistentSpecSeconds);
    sRandomPlayerbotMgr.SetValue(bot->GetGUIDLow(), "specLink", 0, "", persistentSpecSeconds);
    if (PlayerbotAI* ai = bot->GetPlayerbotAI())
    {
        ai->DoSpecificAction("auto learn spell");
        ai->UpdateTalentSpec();
        ai->RequestStrategyReset(false);
    }
    return bot->GetFreeTalentPoints() == 0;
}

std::vector<std::string> ChangeTalentsAction::GetPremadeSpecializations(uint8 cls)
{
    std::vector<std::string> result;
    for (TalentPath& path : sPlayerbotAIConfig.classSpecs[cls].talentPath)
    {
        const std::string value = GetPathSpecialization(cls, path.id);
        if (!value.empty() && std::find(result.begin(), result.end(), value) == result.end()) result.push_back(value);
    }
    return result;
}

bool ChangeTalentsAction::ApplyPremadeSpecialization(Player* bot, const std::string& specialization,
    std::ostringstream* out)
{
    if (!bot) return false;
    std::string requested = specialization;
    std::transform(requested.begin(), requested.end(), requested.begin(), ::tolower);
    std::replace(requested.begin(), requested.end(), ' ', '_');
    if (requested == "prot") requested = "protection";
    else if (requested == "ret") requested = "retribution";
    else if (requested == "bm" || requested == "beast") requested = "beast_mastery";
    else if (requested == "marks") requested = "marksmanship";
    else if (requested == "surv") requested = "survival";
    else if (requested == "assass") requested = "assassination";
    else if (requested == "sub") requested = "subtlety";
    else if (requested == "disc") requested = "discipline";
    else if (requested == "elem") requested = "elemental";
    else if (requested == "enhance") requested = "enhancement";
    else if (requested == "resto") requested = "restoration";
    else if (requested == "afflic") requested = "affliction";
    else if (requested == "demo") requested = "demonology";
    else if (requested == "destro") requested = "destruction";
    uint32 fallback = std::numeric_limits<uint32>::max();
    for (TalentPath& path : sPlayerbotAIConfig.classSpecs[bot->getClass()].talentPath)
        if (GetPathSpecialization(bot->getClass(), path.id) == requested)
        {
            if (fallback == std::numeric_limits<uint32>::max()) fallback = path.id;
            std::string name = path.name;
            std::transform(name.begin(), name.end(), name.begin(), ::tolower);
            if (name.find("pve") != std::string::npos) return ApplyPremadePath(bot, path.id, out);
        }
    return fallback != std::numeric_limits<uint32>::max() && ApplyPremadePath(bot, fallback, out);
}

std::string ChangeTalentsAction::GetPathSpecialization(uint8 cls, uint32 pathId)
{
    TalentPath* path = getPremadePath(cls, pathId);
    if (!path || (uint32)path->id != pathId || path->talentSpec.empty()) return "";
    switch (cls)
    {
        case CLASS_DRUID: return path->talentSpec.back().highestTree() == 0 ? "balance" :
            path->talentSpec.back().highestTree() == 1 ? "feral" : "restoration";
        case CLASS_HUNTER: return path->talentSpec.back().highestTree() == 0 ? "beast_mastery" :
            path->talentSpec.back().highestTree() == 1 ? "marksmanship" : "survival";
        case CLASS_MAGE: return path->talentSpec.back().highestTree() == 0 ? "arcane" :
            path->talentSpec.back().highestTree() == 1 ? "fire" : "frost";
        case CLASS_PALADIN: return path->talentSpec.back().highestTree() == 0 ? "holy" :
            path->talentSpec.back().highestTree() == 1 ? "protection" : "retribution";
        case CLASS_PRIEST: return path->talentSpec.back().highestTree() == 0 ? "discipline" :
            path->talentSpec.back().highestTree() == 1 ? "holy" : "shadow";
        case CLASS_ROGUE: return path->talentSpec.back().highestTree() == 0 ? "assassination" :
            path->talentSpec.back().highestTree() == 1 ? "combat" : "subtlety";
        case CLASS_SHAMAN: return path->talentSpec.back().highestTree() == 0 ? "elemental" :
            path->talentSpec.back().highestTree() == 1 ? "enhancement" : "restoration";
        case CLASS_WARLOCK: return path->talentSpec.back().highestTree() == 0 ? "affliction" :
            path->talentSpec.back().highestTree() == 1 ? "demonology" : "destruction";
        case CLASS_WARRIOR: return path->talentSpec.back().highestTree() == 0 ? "arms" :
            path->talentSpec.back().highestTree() == 1 ? "fury" : "protection";
        default: return "";
    }
}

std::string ChangeTalentsAction::GetPathName(uint8 cls, uint32 pathId)
{
    TalentPath* path = getPremadePath(cls, pathId);
    return path && (uint32)path->id == pathId ? path->name : "";
}

std::string ChangeTalentsAction::GetPathWeightName(uint8 cls, uint32 pathId)
{
    const std::string spec = GetPathSpecialization(cls, pathId);
    if (cls == CLASS_PRIEST) return spec == "discipline" ? "disc" : spec;
    if (cls == CLASS_SHAMAN) return spec == "elemental" ? "elem" : spec == "enhancement" ? "enhance" : "resto";
    if (cls == CLASS_PALADIN) return spec == "protection" ? "prot" : spec == "retribution" ? "retrib" : spec;
    if (cls == CLASS_DRUID)
    {
        TalentPath* path = getPremadePath(cls, pathId);
        std::string name = path ? path->name : "";
        std::transform(name.begin(), name.end(), name.begin(), ::tolower);
        return spec == "restoration" ? "resto" : spec == "feral" && name.find("tank") != std::string::npos ? "feraltank" :
            spec == "feral" ? "feraldps" : spec;
    }
    if (cls == CLASS_ROGUE) return spec == "assassination" ? "assas" : spec == "subtlety" ? "subtle" : spec;
    if (cls == CLASS_HUNTER) return spec == "beast_mastery" ? "beast" : spec == "marksmanship" ? "marks" : "surv";
    if (cls == CLASS_WARLOCK) return spec == "affliction" ? "afflic" : spec == "demonology" ? "demo" : "destro";
    if (cls == CLASS_WARRIOR) return spec == "protection" ? "prot" : spec;
    return spec;
}

BotRoles ChangeTalentsAction::GetPathRole(uint8 cls, uint32 pathId)
{
    TalentPath* path = getPremadePath(cls, pathId);
    if (!path || (uint32)path->id != pathId || path->talentSpec.empty()) return BOT_ROLE_NONE;
    return AiFactory::GetPlayerRoles(cls, path->talentSpec.back().highestTree());
}

std::vector<TalentPath*> ChangeTalentsAction::getPremadePaths(Player* bot, TalentSpec* oldSpec)
{
    std::vector<TalentPath*> ret;
    
    for (auto& path : sPlayerbotAIConfig.classSpecs[bot->getClass()].talentPath)
    {
        TalentSpec newSpec = *GetBestPremadeSpec(bot, path.id);
        newSpec.CropTalents(bot);        
        if (oldSpec->isEarlierVersionOf(newSpec))
        {
            ret.push_back(&path);
        }
    }

    return ret;
}

TalentPath* ChangeTalentsAction::getPremadePath(uint8 cls, int id)
{
    for (auto& path : sPlayerbotAIConfig.classSpecs[cls].talentPath)
    {
        if (id == path.id)
        {
            return &path;
        }
    }

    if (sPlayerbotAIConfig.classSpecs[cls].talentPath.empty())
        return nullptr;

    return &sPlayerbotAIConfig.classSpecs[cls].talentPath[0];
}

void ChangeTalentsAction::listPremadePaths(uint8 cls, std::vector<TalentPath*> paths, std::ostringstream* out)
{
    if (paths.size() == 0)
    {
        *out << "No predefined talents found..";
    }

    *out << "|h|cffffffff";

    for (auto path : paths)
    {
        *out << path->name << " (" << path->talentSpec.back().formatSpec(cls) << "), ";
    }

    out->seekp(-2, out->cur);
    *out << ".";
}

TalentPath* ChangeTalentsAction::PickPremadePath(std::vector<TalentPath*> paths, bool useProbability)
{
    int totProbability = 0;
    int curProbability = 0;

    if(paths.size() == 1)
        return paths[0];

    for (auto path : paths)
    {
        totProbability += useProbability ? path->probability : 1;
    }

    totProbability = irand(0, totProbability);

    for (auto path : paths)
    {
        curProbability += (useProbability ? path->probability : 1);
        if (curProbability >= totProbability)
            return path;
    }

    return paths[0];
}

bool ChangeTalentsAction::AutoSelectTalents(Player* bot, std::ostringstream* out, BotRoles role)
{
    //Does the bot have talentpoints?
    if (bot->GetLevel() < 10)
    {
        *out << "No free talent points.";
        return false;
    }

    uint32 specNo = sRandomPlayerbotMgr.GetValue(bot->GetGUIDLow(), "specNo");
    uint32 specId = specNo ? specNo - 1 : 0;
    std::string specLink = sRandomPlayerbotMgr.GetData(bot->GetGUIDLow(), "specLink");
    uint8 cls = bot->getClass();

    //Continue the current spec
    if (specNo > 0)
    {
        TalentSpec newSpec = *GetBestPremadeSpec(bot, specId);
        newSpec.CropTalents(bot);
        newSpec.ApplyTalents(bot, out);
        if (bot->GetPlayerbotAI())
            bot->GetPlayerbotAI()->UpdateTalentSpec();
        if (newSpec.GetTalentPoints() > 0)
        {
            *out << "Upgrading spec " << "|h|cffffffff" << getPremadePath(bot->getClass(), specId)->name << " (" << newSpec.formatSpec(cls) << ")";
        }
    }
    else if (!specLink.empty())
    {
        TalentSpec newSpec(bot, specLink);
        newSpec.CropTalents(bot);
        newSpec.ApplyTalents(bot, out);
        if (bot->GetPlayerbotAI())
            bot->GetPlayerbotAI()->UpdateTalentSpec();
        if (newSpec.GetTalentPoints() > 0)
        {
            *out << "Upgrading saved spec " << "|h|cffffffff" << ChatHelper::formatClass(bot, newSpec.highestTree()) << " (" << newSpec.formatSpec(cls) << ")";
        }
    }

    //Spec was not found or not sufficient
    if (bot->CalculateTalentsPoints() > 0 || (!specNo && specLink.empty()))
    {
        TalentSpec oldSpec(bot);
        int currentTree = oldSpec.highestTree();
        std::vector<TalentPath*> paths;
        
        if (oldSpec.points)
            paths = getPremadePaths(bot, &oldSpec);

        if (paths.size() == 0) //No spec like the old one found. Pick any.
        {
            if (bot->CalculateTalentsPoints() > 0)
                *out << "No specs like the current spec found.";

            paths = getPremadePaths(bot->getClass(), "", role);

            if (paths.empty() && role != BotRoles::BOT_ROLE_NONE)
                paths = getPremadePaths(bot->getClass(), "", BotRoles::BOT_ROLE_NONE);
        }   

        if(paths.size() > 0 && oldSpec.GetTalentPoints() > 0)
        {
            //Check if any spec has the same tree as the current spec.
            bool hasSameTree = false;
            for (auto it : paths)
            {
                if (it->talentSpec.back().highestTree() == currentTree)
                {
                    hasSameTree = true;
                    break;
                }
            }

            if (hasSameTree) //Remove specs that do not end up in the same tree.
            {
                auto it = paths.begin();
                while (it != paths.end()) 
                {
                    TalentPath* path = *it;
                    if (path->talentSpec.back().highestTree() != currentTree) 
                    {
                        it = paths.erase(it);
                    }
                    else 
                    {
                        ++it;
                    }
                }
            }
        }

        if (paths.size() == 0)
        {
            *out << "No predefined talents found for this class.";
            specId = -1;
        }
        else if (paths.size() > 1 && sPlayerbotAIConfig.autoPickTalents != "full" && !sRandomPlayerbotMgr.IsRandomBot(bot))
        {
            *out << "Found multiple specs: ";
            listPremadePaths(cls, paths, out);
        }
        else
        {
            specId = PickPremadePath(paths, sRandomPlayerbotMgr.IsRandomBot(bot))->id;
            TalentSpec newSpec = *GetBestPremadeSpec(bot, specId);
            specLink = newSpec.GetTalentLink();
            newSpec.CropTalents(bot);
            newSpec.ApplyTalents(bot, out);
            if (bot->GetPlayerbotAI())
                bot->GetPlayerbotAI()->UpdateTalentSpec();

            if (paths.size() > 1)
                *out << "Found " << paths.size() << " possible specs to choose from. ";

            *out << "Apply spec " << "|h|cffffffff" << getPremadePath(cls, specId)->name << " " << newSpec.formatSpec(cls);
        }
    }

    const int32 persistentSpecSeconds = 10 * 365 * 24 * 60 * 60;
    sRandomPlayerbotMgr.SetValue(bot->GetGUIDLow(), "specNo", specId + 1, "", persistentSpecSeconds);
    if (!specLink.empty() && specId == -1)
        sRandomPlayerbotMgr.SetValue(bot->GetGUIDLow(), "specLink", 1, specLink, persistentSpecSeconds);
    else
        sRandomPlayerbotMgr.SetValue(bot->GetGUIDLow(), "specLink", 0, "", persistentSpecSeconds);

    return (specNo == 0) ? false : true;
}

//Returns a pre-made talent spec that best suits the bots current talents. 
TalentSpec* ChangeTalentsAction::GetBestPremadeSpec(Player* bot, int specId)
{
    TalentPath* path = getPremadePath(bot->getClass(), specId);
    for (auto& spec : path->talentSpec)
    {
        if (spec.points >= bot->CalculateTalentsPoints())
            return &spec;
    }
    if (path->talentSpec.size())
        return &path->talentSpec.back();

    return &sPlayerbotAIConfig.classSpecs[bot->getClassMask()].baseSpec;
}

bool AutoSetTalentsAction::Execute(Event& event)
{
    Player* requester = event.getOwner() ? event.getOwner() : GetMaster();
    sPlayerbotAIConfig.logEvent(ai, "AutoSetTalentsAction", std::to_string(bot->m_Played_time[PLAYED_TIME_LEVEL]), std::to_string(bot->m_Played_time[PLAYED_TIME_TOTAL]));

    std::ostringstream out;

    if (sPlayerbotAIConfig.autoPickTalents == "no" && !sRandomPlayerbotMgr.IsRandomBot(bot))
    {
        return false;
    }

    if (bot->CalculateTalentsPoints() <= 0)
    {
        return false;
    }

    AutoSelectTalents(bot, &out);

    ai->TellPlayer(requester, out, PlayerbotSecurityLevel::PLAYERBOT_SECURITY_ALLOW_ALL, false);

    return true;
}


