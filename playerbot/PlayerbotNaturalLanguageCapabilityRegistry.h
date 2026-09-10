#ifndef _PLAYERBOT_NATURAL_LANGUAGE_CAPABILITY_REGISTRY_H
#define _PLAYERBOT_NATURAL_LANGUAGE_CAPABILITY_REGISTRY_H

#include <map>
#include <string>

enum class LivingCapabilityExecutor
{
    none,
    social,
    partyCombat,
    economy
};

struct LivingCapabilityRegistration
{
    std::string operationKey;
    std::string family;
    std::string riskTier;
    std::string authorityPolicy;
    std::string confirmationClass;
    LivingCapabilityExecutor executor = LivingCapabilityExecutor::none;
};

class PlayerbotNaturalLanguageCapabilityRegistry
{
public:
    static PlayerbotNaturalLanguageCapabilityRegistry& instance();
    const LivingCapabilityRegistration* Resolve(const std::string& operationKey) const;

private:
    PlayerbotNaturalLanguageCapabilityRegistry();
    void Register(const char* key, const char* family, const char* risk, const char* authority,
        const char* confirmation, LivingCapabilityExecutor executor);
    std::map<std::string, LivingCapabilityRegistration> registrations;
};

#define sPlayerbotNaturalLanguageCapabilityRegistry PlayerbotNaturalLanguageCapabilityRegistry::instance()

#endif
