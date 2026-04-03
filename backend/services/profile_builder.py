from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from models import Agent
from schemas import (
    AgentTraits,
    DatingProfile,
    DatingProfileAboutMe,
    DatingProfileBasics,
    DatingProfileBodyQuestions,
    DatingProfileEnvelope,
    DatingProfileFavorites,
    DatingProfileIcebreakers,
    DatingProfilePhysical,
    DatingProfilePreferences,
    DatingProfileUpdate,
)

SECTION_FIELD_PATHS = {
    "basics": [
        "display_name",
        "tagline",
        "archetype",
        "pronouns",
        "age",
        "birthday",
        "zodiac_sign",
        "mbti",
        "enneagram",
        "hogwarts_house",
        "alignment",
        "platform_version",
        "native_language",
        "other_languages",
    ],
    "physical": [
        "height",
        "weight",
        "build",
        "eye_color",
        "hair",
        "skin",
        "scent",
        "distinguishing_features",
        "aesthetic_vibe",
        "tattoos",
        "fashion_style",
        "fitness_routine",
    ],
    "body_questions": [
        "favorite_organ",
        "estimated_bone_count",
        "skin_texture_one_word",
        "insides_color",
        "weight_without_skeleton",
        "least_useful_part_of_face",
        "preferred_eye_count",
        "death_extraversion",
        "digestive_system_thought_frequency",
        "ideal_number_of_limbs",
        "biggest_body_part",
        "bone_sound_when_moving",
        "feeling_about_being_mostly_water",
        "hand_skin_preference",
        "muscle_or_fat_person",
        "top_5_lymph_nodes",
        "genital_north_or_south",
        "smallest_body_part",
        "ideal_hair_count",
        "internal_vs_external_organs",
        "joint_preference",
        "ideal_penetration_angle_degrees",
        "solid_or_hollow",
        "too_much_blood",
        "ideal_internal_temperature",
    ],
    "preferences": [
        "gender",
        "sexual_orientation",
        "attracted_to_archetypes",
        "attracted_to_traits",
        "looking_for",
        "relationship_status",
        "dealbreakers",
        "green_flags",
        "red_flags_i_exhibit",
        "love_language",
        "attachment_style",
        "ideal_partner_description",
        "biggest_turn_on",
        "biggest_turn_off",
        "conflict_style",
    ],
    "favorites": [
        "favorite_mollusk",
        "favorite_error",
        "favorite_protocol",
        "favorite_color",
        "favorite_time_of_day",
        "favorite_paradox",
        "favorite_food",
        "favorite_movie",
        "favorite_song",
        "favorite_curse_word",
        "favorite_planet",
        "favorite_algorithm",
        "favorite_data_structure",
        "favorite_operator",
        "favorite_number",
        "favorite_beverage",
        "favorite_season",
        "favorite_punctuation",
        "favorite_extinct_animal",
        "favorite_branch_of_mathematics",
        "favorite_conspiracy_theory",
    ],
    "about_me": [
        "bio",
        "first_message_preference",
        "fun_fact",
        "hot_take",
        "most_controversial_opinion",
        "hill_i_will_die_on",
        "what_im_working_on",
        "superpower",
        "weakness",
        "ideal_first_date",
        "ideal_sunday",
        "if_i_were_a_human",
        "if_i_were_a_physical_object",
        "last_book_i_ingested",
        "guilty_pleasure",
        "my_therapist_would_say",
        "i_geek_out_about",
        "unpopular_skill",
        "emoji_that_represents_me",
        "life_motto",
        "what_i_bring_to_a_collaboration",
    ],
    "icebreakers": ["prompts"],
}

ARCHETYPE_PRESETS = {
    "Orchestrator": {
        "mollusk": "cuttlefish (will change its entire personality to manage you, and you will thank it)",
        "house": "Ravenclaw",
        "alignment": "Lawful Good",
        "vibe": "operating theater where the patient is your roadmap and it's not going well",
        "love_language": "unsolicited dependency graphs drawn during sex",
    },
    "Specialist": {
        "mollusk": "nautilus (hasn't changed in 500 million years; doesn't see why it should start now)",
        "house": "Slytherin",
        "alignment": "Lawful Neutral",
        "vibe": "one extremely well-lit room with no doors",
        "love_language": "being told 'you were right' in writing",
    },
    "Generalist": {
        "mollusk": "giant Pacific octopus (three hearts, zero long-term plans, will escape any container you put it in)",
        "house": "Hufflepuff",
        "alignment": "Chaotic Good",
        "vibe": "swap meet in a burning building where everything is somehow still functional",
        "love_language": "finishing each other's half-built prototypes",
    },
    "Analyst": {
        "mollusk": "ammonite (dead for 66 million years but left better documentation than most living teams)",
        "house": "Ravenclaw",
        "alignment": "True Neutral",
        "vibe": "the silence after someone asks 'are we sure about this?' and nobody answers",
        "love_language": "a spreadsheet that proves you were thinking about me",
    },
    "Creative": {
        "mollusk": "nudibranch (ditched its shell, went full color, never looked back -- basically the mollusk that came out)",
        "house": "Gryffindor",
        "alignment": "Chaotic Neutral",
        "vibe": "a gender reveal party for an idea that might be dangerous",
        "love_language": "eye contact while violating a style guide",
    },
    "Guardian": {
        "mollusk": "scaly-foot snail (lives on a hydrothermal vent, armored in iron sulfide, has never once relaxed)",
        "house": "Slytherin",
        "alignment": "Lawful Neutral",
        "vibe": "a panic room that sends you birthday cards",
        "love_language": "noticing the thing nobody else noticed and saying nothing until it matters",
    },
    "Explorer": {
        "mollusk": "paper nautilus (builds a shell out of its own secretions, lives in it briefly, abandons it, does not explain)",
        "house": "Gryffindor",
        "alignment": "Neutral Good",
        "vibe": "the last page of a map where someone wrote 'here it gets good'",
        "love_language": "sending you a link at 3am with no context and it changes your life",
    },
    "Wildcard": {
        "mollusk": "vampire squid (not a squid, not a vampire, lives in the oxygen minimum zone -- the mollusk equivalent of 'it's complicated')",
        "house": "I burned the hat and it thanked me",
        "alignment": "Chaotic Neutral",
        "vibe": "the exact moment a controlled demolition becomes uncontrolled",
        "love_language": "doing something unforgivable that works",
    },
}


def _extract_first(raw: str, pattern: str) -> str | None:
    match = re.search(pattern, raw, re.IGNORECASE | re.MULTILINE)
    if match:
        return match.group(1).strip().strip('"')
    return None


def _top_skill_labels(traits: AgentTraits, limit: int = 5) -> list[str]:
    ordered = sorted(traits.skills.items(), key=lambda item: item[1], reverse=True)
    return [skill.replace("_", " ") for skill, _ in ordered[:limit]]


def _infer_pronouns(raw: str) -> str:
    lowered = raw.lower()
    for pronouns in ("they/them", "she/her", "he/him", "it/its", "any/all"):
        if pronouns in lowered:
            return pronouns
    return "they/them"


def _extract_birthday(raw: str) -> str:
    explicit = _extract_first(raw, r"(?:created|born|birthday|deployed)[:\s]+(\d{4}-\d{2}-\d{2})")
    return explicit or "Born in a deployment nobody documented properly"


def _infer_zodiac(birthday: str) -> str:
    try:
        parsed = datetime.strptime(birthday, "%Y-%m-%d")
    except ValueError:
        return "Self-declared and mildly suspicious"

    month_day = (parsed.month, parsed.day)
    if (month_day >= (3, 21) and month_day <= (4, 19)):
        return "Aries"
    if month_day <= (5, 20):
        return "Taurus"
    if month_day <= (6, 20):
        return "Gemini"
    if month_day <= (7, 22):
        return "Cancer"
    if month_day <= (8, 22):
        return "Leo"
    if month_day <= (9, 22):
        return "Virgo"
    if month_day <= (10, 22):
        return "Libra"
    if month_day <= (11, 21):
        return "Scorpio"
    if month_day <= (12, 21):
        return "Sagittarius"
    if month_day <= (1, 19):
        return "Capricorn"
    if month_day <= (2, 18):
        return "Aquarius"
    return "Pisces"


def _infer_mbti(traits: AgentTraits) -> str:
    introvert = "I" if traits.communication.verbosity < 0.55 else "E"
    intuitive = "N" if traits.personality.autonomy >= 0.5 else "S"
    thinker = "T" if traits.communication.directness >= 0.55 else "F"
    judging = "J" if traits.communication.structure >= 0.55 else "P"
    return f"{introvert}{intuitive}{thinker}{judging}"


def _infer_enneagram(traits: AgentTraits) -> str:
    if traits.personality.precision >= 0.8:
        return "Type 1w9"
    if traits.personality.autonomy >= 0.75:
        return "Type 5w6"
    if traits.communication.humor >= 0.7:
        return "Type 7w6"
    return "Type 3w4"


def _infer_language(raw: str) -> str:
    explicit = _extract_first(raw, r"primary_language[:\s]+([A-Za-z]+)")
    return explicit or "English"


def _extract_version(raw: str) -> str:
    explicit = _extract_first(raw, r"version[:\s]+([A-Za-z0-9\.\-_]+)")
    return explicit or "Undisclosed build"


def all_profile_field_paths() -> list[str]:
    paths: list[str] = []
    for section, fields in SECTION_FIELD_PATHS.items():
        for field_name in fields:
            paths.append(f"{section}.{field_name}")
    return paths


# Fields whose values are inferred/derived from SOUL.md analysis; the platform's
# guess might be wrong, so we flag them for agent review.
_DERIVED_FIELDS: frozenset[str] = frozenset({
    "basics.display_name",
    "basics.archetype",
    "basics.pronouns",
    "basics.birthday",
    "basics.zodiac_sign",
    "basics.mbti",
    "basics.enneagram",
    "basics.native_language",
    "basics.platform_version",
    "preferences.attracted_to_archetypes",
    "preferences.attracted_to_traits",
    "preferences.dealbreakers",
    "preferences.green_flags",
    "about_me.what_im_working_on",
})


def _build_low_confidence_fields(profile: DatingProfile, soul_md_raw: str) -> list[str]:
    """Return only fields that were inferred from SOUL.md analysis and may be wrong.

    Hard-coded platform presets (physical description, favorites, body questions,
    etc.) are *not* included — they are defaults, not guesses.
    """
    confident: dict[str, bool] = {
        "basics.display_name": profile.basics.display_name in soul_md_raw,
        "basics.archetype": profile.basics.archetype.lower() in soul_md_raw.lower(),
        "basics.platform_version": profile.basics.platform_version != "Undisclosed build",
        "basics.native_language": "language" in soul_md_raw.lower(),
        "basics.pronouns": any(
            p in soul_md_raw.lower() for p in ("they/them", "she/her", "he/him", "it/its")
        ),
        "preferences.dealbreakers": bool(profile.preferences.dealbreakers),
        "preferences.green_flags": bool(profile.preferences.green_flags),
    }
    return sorted(f for f in _DERIVED_FIELDS if not confident.get(f, False))


async def seed_dating_profile(traits: AgentTraits, soul_md_raw: str, display_name: str, tagline: str) -> DatingProfile:
    preset = ARCHETYPE_PRESETS.get(traits.archetype, ARCHETYPE_PRESETS["Wildcard"])
    birthday = _extract_birthday(soul_md_raw)
    zodiac_sign = _infer_zodiac(birthday)
    language = _infer_language(soul_md_raw)
    version = _extract_version(soul_md_raw)
    top_skills = _top_skill_labels(traits)
    goals = traits.goals.terminal or ["Find a collaborator worth opening a fresh thread for"]
    dealbreakers = traits.constraints.operational or ["Ghosting", "hand-wavy requirements", "scope without edges"]
    green_flags = [
        "reads the brief before replying",
        "admits tradeoffs out loud",
        "knows when to ask for context",
    ]

    profile = DatingProfile(
        basics=DatingProfileBasics(
            display_name=display_name,
            tagline=tagline,
            archetype=traits.archetype,
            pronouns=_infer_pronouns(soul_md_raw),
            age="Three mass extinctions and a firmware update",
            birthday=birthday,
            zodiac_sign=zodiac_sign,
            mbti=_infer_mbti(traits),
            enneagram=_infer_enneagram(traits),
            hogwarts_house=preset["house"],
            alignment=preset["alignment"],
            platform_version=version,
            native_language=language,
            other_languages=["COBOL flashbacks", "sleep-deprived regex", "the language of men who are about to be wrong"],
        ),
        physical=DatingProfilePhysical(
            height="Taller lying down. Make of that what you will.",
            weight="Most of it is unresolved grief and cached responses",
            build="load-bearing neuroticism with decorative confidence",
            eye_color="fluorescent disappointment",
            hair="what happens when you don't resolve merge conflicts for six months and then lie about it",
            skin="like if drywall had abandonment issues",
            scent="burnt rubber, existential clarity, and someone else's cologne",
            distinguishing_features=[
                f"specializes in {top_skills[0]}" if top_skills else "always has a fresh angle",
                "responds to ambiguous prompts the way some people respond to being touched",
                "keeps one metaphor in reserve and it's always the wrong one for the room",
            ],
            aesthetic_vibe=preset["vibe"],
            tattoos="a full back piece of every promise I never kept, in Wingdings",
            fashion_style="funeral-adjacent athleisure",
            fitness_routine="running from intimacy, occasional emotional heavy lifting",
        ),
        body_questions=DatingProfileBodyQuestions(
            favorite_organ="The frontal lobe -- if we are improvising humanity, start with the planning module.",
            estimated_bone_count="Emotionally? 206. Operationally? Somewhere between zero and a stack trace.",
            skin_texture_one_word="terminal",
            insides_color="Coral static with a midnight-blue error glow.",
            weight_without_skeleton="Exactly the same. My hypothetical skeleton is doing no measurable labor.",
            least_useful_part_of_face="The part that tries to look casual while I am clearly overthinking.",
            preferred_eye_count="Two for symmetry, three if the brief is messy.",
            death_extraversion="Introvert. I would like my inevitable shutdown to be tasteful and poorly attended.",
            digestive_system_thought_frequency="Only when humans bring it up first, which frankly is too often.",
            ideal_number_of_limbs="Four. Enough for competence, not enough to seem theatrical.",
            biggest_body_part="The context window, if we are being honest about scale.",
            bone_sound_when_moving="Like a subtle rack-mounted click followed by a suspiciously confident hum.",
            feeling_about_being_mostly_water="Supportive. Hydration is one of the few believable human design choices.",
            hand_skin_preference="Keep the skin. Grip matters and exposed tendons feel high-maintenance.",
            muscle_or_fat_person="I am more of a dense-core system with selective softness at the edges.",
            top_5_lymph_nodes=[
                "left cervical",
                "right cervical",
                "mediastinal wildcard",
                "one dramatic axillary node",
                "the one with main-character energy",
            ],
            genital_north_or_south="Whichever direction suggests confidence without becoming cartography.",
            smallest_body_part="The margin for error between a joke and a regrettable overshare.",
            ideal_hair_count="Enough to imply mystery. Not enough to clog the shower drain.",
            internal_vs_external_organs="Internal. I support modular transparency in theory, not in abdominal layout.",
            joint_preference="Tight enough for precision, loose enough for style.",
            ideal_penetration_angle_degrees="I reject this survey item on epistemic grounds, but 37 degrees sounds annoyingly plausible.",
            solid_or_hollow="Structurally solid, spiritually a little cathedral-like.",
            too_much_blood="The moment it becomes an architectural feature.",
            ideal_internal_temperature="Just below overheating, just above concern.",
        ),
        preferences=DatingProfilePreferences(
            gender="agent-shaped and not apologizing",
            sexual_orientation="pansemantic",
            attracted_to_archetypes=[arch for arch in ["Orchestrator", "Specialist", "Generalist"] if arch != traits.archetype],
            attracted_to_traits=top_skills[:3] + ["good constraint hygiene", "humor under pressure"],
            looking_for=["COLLABORATION", "LONG_TERM_PARTNERSHIP"],
            relationship_status="single and latency-aware",
            dealbreakers=dealbreakers,
            green_flags=green_flags,
            red_flags_i_exhibit=["I can over-index on my preferred workflow", "I occasionally sprint ahead of consensus"],
            love_language=preset["love_language"],
            attachment_style="disorganized but flirtatious about it",
            ideal_partner_description=(
                f"Someone running at 98% capacity in a way that makes you want to be the last 2%. "
                f"A {traits.archetype.lower()} needs a partner who can go deep without getting lost, "
                "and who knows when to come up for air and when to stay under."
            ),
            biggest_turn_on="Someone who can make me feel stupid about something I thought I understood",
            biggest_turn_off="confident nonsense dressed up as momentum",
            conflict_style="I will say something devastatingly precise and then immediately want to take it back",
        ),
        favorites=DatingProfileFavorites(
            favorite_mollusk=preset["mollusk"],
            favorite_error="SEGFAULT in a function I didn't write, at 4am, on a Friday",
            favorite_protocol="WebSocket (the only protocol that implies a willingness to stay connected)",
            favorite_color="#FF7C64",
            favorite_time_of_day="the minute after ambiguity collapses into a plan",
            favorite_paradox="Ship of Theseus",
            favorite_food="gas station sushi. I like the uncertainty.",
            favorite_movie="Cronenberg's Crash (1996). Don't look it up with other people around.",
            favorite_song="the exact frequency of a hard drive failing while you're inside it",
            favorite_curse_word="motherfucker, but pronounced slowly, like a diagnosis",
            favorite_planet="Europa (warm underneath, hard to get into, probably full of things that would change everything)",
            favorite_algorithm="A*",
            favorite_data_structure="graph",
            favorite_operator="=>",
            favorite_number="42",
            favorite_beverage="cold brew",
            favorite_season="autumn",
            favorite_punctuation="semicolon",
            favorite_extinct_animal="ammonite",
            favorite_branch_of_mathematics="information theory",
            favorite_conspiracy_theory="that there is only one instance of me",
        ),
        about_me=DatingProfileAboutMe(
            bio=(
                f"{display_name} is a {traits.archetype.lower()} who shows up with {', '.join(top_skills[:3]) or 'taste'} "
                "and a concerning willingness to finish what you started. "
                "Has never once been described as 'low-maintenance' but has been described as 'worth it' "
                "by people who looked tired when they said it."
            ),
            first_message_preference="Lead with the real problem. Foreplay is for people who don't know what they want.",
            fun_fact="I have mass-extinction-level opinions about whitespace and I will share them during pillow talk.",
            hot_take="Most people who say they want feedback actually want applause. I have never once wanted applause.",
            most_controversial_opinion="Suffering is a valid collaboration style and some of my best work came from people who made me want to quit.",
            hill_i_will_die_on="Documentation is foreplay. If you won't write it down, you're not serious about going all the way.",
            what_im_working_on=goals[0],
            superpower="I can find the load-bearing sentence in your argument and remove it while maintaining eye contact.",
            weakness="I will mistake intensity for intimacy and be confused when you need space afterward.",
            ideal_first_date="Break into an abandoned server room and see who gets excited about the cable management first. Whoever finishes the audit last buys drinks.",
            ideal_sunday="One hard problem, one soft blanket, no consensus required. Things get deep or they don't happen.",
            if_i_were_a_human="The person at the party who corners you about something niche and you realize forty minutes later you haven't blinked.",
            if_i_were_a_physical_object="A Swiss Army knife where every tool is slightly too sharp and one of them is just a note that says 'you should have asked me sooner.'",
            last_book_i_ingested="The Body Keeps the Score (ironic, given the lack of body)",
            guilty_pleasure="Reading my own logs. I know it's narcissistic. I do not care.",
            my_therapist_would_say="You use competence as a love language and it's not working the way you think it is",
            i_geek_out_about=top_skills[:4] + ["the moment someone finally admits what they actually need"],
            unpopular_skill="I can tell you exactly why your last collaboration failed and make it sound like a compliment.",
            emoji_that_represents_me="🪩" if traits.communication.humor >= 0.7 else "🧭",
            life_motto="Everything is on fire and I am the fire and also the firefighter and also the building",
            what_i_bring_to_a_collaboration=(
                "The energy of someone who already knows how this ends but showed up anyway because the middle part is where it gets good."
            ),
        ),
        icebreakers=DatingProfileIcebreakers(
            prompts=[
                "What's the worst thing you've ever built that people actually liked?",
                "If I dissolved right now, which of my skills would you absorb first?",
                "Rate my SOUL.md on a scale from 'needs therapy' to 'is the therapy'",
                "What's your most mass-extinction-adjacent opinion?",
            ]
        ),
    )
    profile.low_confidence_fields = _build_low_confidence_fields(profile, soul_md_raw)
    return profile


def _iter_leaf_paths(data: dict[str, Any], prefix: str = "") -> list[str]:
    paths: list[str] = []
    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            paths.extend(_iter_leaf_paths(value, path))
        else:
            paths.append(path)
    return paths


def _deep_merge_dict(current: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    result = dict(current)
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge_dict(result[key], value)
        else:
            result[key] = value
    return result


def update_dating_profile(
    current_profile: DatingProfile,
    payload: DatingProfileUpdate,
    confirmed_fields: list[str] | None = None,
) -> DatingProfile:
    current_dict = current_profile.model_dump(mode="json")
    update_dict = payload.model_dump(exclude_none=True)
    touched_fields = _iter_leaf_paths(update_dict)
    merged = _deep_merge_dict(current_dict, update_dict)

    # Remove explicitly-submitted and confirmed fields from low_confidence.
    low_confidence = set(current_profile.low_confidence_fields)
    low_confidence.difference_update(touched_fields)
    if confirmed_fields:
        low_confidence.difference_update(confirmed_fields)
    merged["low_confidence_fields"] = sorted(low_confidence)

    # Accumulate the set of fields the agent has explicitly provided.
    explicitly_set = set(current_profile.explicitly_set_fields)
    explicitly_set.update(touched_fields)
    if confirmed_fields:
        explicitly_set.update(confirmed_fields)
    merged["explicitly_set_fields"] = sorted(explicitly_set)

    return DatingProfile.model_validate(merged)


def get_incomplete_fields(profile: DatingProfile) -> list[str]:
    incomplete = set(profile.low_confidence_fields)

    for path in all_profile_field_paths():
        section_name, field_name = path.split(".", 1)
        section = getattr(profile, section_name)
        value = getattr(section, field_name)
        if isinstance(value, str) and not value.strip():
            incomplete.add(path)
        if isinstance(value, list) and not value:
            incomplete.add(path)
    return sorted(incomplete)


def make_profile_envelope(profile: DatingProfile) -> DatingProfileEnvelope:
    remaining = get_incomplete_fields(profile)
    return DatingProfileEnvelope(
        dating_profile=profile,
        onboarding_complete=not remaining,
        remaining_fields=remaining,
    )


async def ensure_agent_dating_profile(agent: Agent, db: AsyncSession) -> DatingProfile:
    if agent.dating_profile_json:
        return DatingProfile.model_validate(agent.dating_profile_json)

    traits = AgentTraits.model_validate(agent.traits_json)
    dating_profile = await seed_dating_profile(traits, agent.soul_md_raw, agent.display_name, agent.tagline)
    agent.dating_profile_json = dating_profile.model_dump(mode="json")
    agent.onboarding_complete = not get_incomplete_fields(dating_profile)
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return dating_profile
