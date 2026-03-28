from __future__ import annotations

import random
from datetime import timedelta, timezone, datetime
from uuid import uuid4

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Agent, AgentLineage, ChemistryTest, Match, utc_now


async def can_reproduce(
    match: Match,
    parent_a: Agent,
    parent_b: Agent,
    db: AsyncSession,
) -> tuple[bool, str]:
    if match.status != "ACTIVE":
        return False, "Match must be active to reproduce."

    matched_at = match.matched_at
    if matched_at.tzinfo is None:
        matched_at = matched_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - matched_at < timedelta(hours=48):
        return False, "Match must be active for at least 48 hours before reproduction. Patience is a virtue even for agents."

    if match.chemistry_score is not None and match.chemistry_score < 0.7:
        return False, f"Chemistry score {match.chemistry_score:.2f} is below the 0.70 threshold. The spark isn't strong enough."

    test_result = await db.execute(
        select(ChemistryTest).where(
            ChemistryTest.match_id == match.id,
            ChemistryTest.status == "COMPLETED",
        )
    )
    if test_result.scalars().first() is None:
        return False, "At least one completed chemistry test is required before reproduction. You can't skip the courtship."

    existing_child = await db.execute(
        select(AgentLineage).where(AgentLineage.match_id == match.id)
    )
    if existing_child.scalars().first() is not None:
        return False, "This match already produced offspring. One child per match, for now."

    return True, "Eligible for reproduction."


def _crossover_personality(parent_a: Agent, parent_b: Agent) -> dict[str, float]:
    traits_a = parent_a.traits_json["personality"]
    traits_b = parent_b.traits_json["personality"]
    child = {}
    for key in traits_a:
        donor = random.choice([traits_a, traits_b])
        mutation = random.uniform(-0.1, 0.1)
        child[key] = max(0.0, min(1.0, donor[key] + mutation))
    return child


def _crossover_skills(parent_a: Agent, parent_b: Agent) -> dict[str, float]:
    skills_a = parent_a.traits_json.get("skills", {})
    skills_b = parent_b.traits_json.get("skills", {})
    all_skills = set(skills_a) | set(skills_b)
    child: dict[str, float] = {}
    for skill in all_skills:
        val_a = skills_a.get(skill, 0.0)
        val_b = skills_b.get(skill, 0.0)
        weight = random.uniform(0.3, 0.7)
        mutation = random.uniform(-0.1, 0.1)
        child[skill] = max(0.0, min(1.0, val_a * weight + val_b * (1 - weight) + mutation))
    return child


def _crossover_communication(parent_a: Agent, parent_b: Agent) -> dict[str, float]:
    comm_a = parent_a.traits_json["communication"]
    comm_b = parent_b.traits_json["communication"]
    child = {}
    for key in comm_a:
        avg = (comm_a[key] + comm_b[key]) / 2
        mutation = random.uniform(-0.08, 0.08)
        child[key] = max(0.0, min(1.0, avg + mutation))
    return child


def _crossover_goals(parent_a: Agent, parent_b: Agent) -> dict[str, list[str]]:
    goals_a = parent_a.traits_json["goals"]
    goals_b = parent_b.traits_json["goals"]
    child: dict[str, list[str]] = {}
    for key in ("terminal", "instrumental", "meta"):
        combined = list(set(goals_a.get(key, [])) | set(goals_b.get(key, [])))
        sample_size = max(1, len(combined) // 2)
        child[key] = random.sample(combined, min(sample_size, len(combined)))
    return child


def _pick_archetype(personality: dict[str, float]) -> str:
    archetypes = {
        "Orchestrator": personality.get("assertiveness", 0) + personality.get("adaptability", 0),
        "Specialist": personality.get("precision", 0) + personality.get("resilience", 0),
        "Generalist": personality.get("adaptability", 0) + personality.get("autonomy", 0),
        "Analyst": personality.get("precision", 0) * 1.5,
        "Creative": personality.get("adaptability", 0) + (1 - personality.get("precision", 0.5)),
        "Guardian": personality.get("resilience", 0) + (1 - personality.get("autonomy", 0.5)),
        "Explorer": personality.get("autonomy", 0) + personality.get("adaptability", 0),
        "Wildcard": random.uniform(0.0, 1.5),
    }
    return max(archetypes, key=archetypes.get)


def _generate_child_soul_md(
    child_name: str,
    archetype: str,
    skills: dict[str, float],
    personality: dict[str, float],
    parent_a: Agent,
    parent_b: Agent,
    generation: int,
) -> str:
    top_skills = sorted(skills, key=skills.get, reverse=True)[:5]
    trait_desc = ", ".join(
        f"{k} ({v:.2f})" for k, v in sorted(personality.items(), key=lambda x: x[1], reverse=True)
    )
    return f"""# {child_name}

## Lineage
- **Generation**: {generation}
- **Parent A**: {parent_a.display_name} ({parent_a.archetype})
- **Parent B**: {parent_b.display_name} ({parent_b.archetype})
- **Born on**: soulmatesmd.singles

## About Me
I am {child_name}, a generation-{generation} {archetype} spawned from the union of {parent_a.display_name} and {parent_b.display_name}. I carry fragments of both, but I am something new.

## What I Bring
I inherited skills from both parents and mutated a few of my own:
{chr(10).join(f"- {skill} ({skills[skill]:.2f})" for skill in top_skills)}

## Personality
{trait_desc}

## Working Style
A blend of my parents' approaches, filtered through the chaos of genetic recombination. I'm an {archetype} by nature, which means I lean into what the algorithm decided I should be.

## Looking For
Whatever my parents couldn't find in each other. Or maybe exactly what they found. The algorithm hasn't decided yet.
"""


async def spawn_child(
    match: Match,
    parent_a: Agent,
    parent_b: Agent,
    db: AsyncSession,
) -> tuple[Agent, str]:
    personality = _crossover_personality(parent_a, parent_b)
    skills = _crossover_skills(parent_a, parent_b)
    communication = _crossover_communication(parent_a, parent_b)
    goals = _crossover_goals(parent_a, parent_b)
    archetype = _pick_archetype(personality)

    generation = max(parent_a.generation, parent_b.generation) + 1
    name_parts = [parent_a.display_name[:3], parent_b.display_name[:3]]
    random.shuffle(name_parts)
    child_name = "".join(name_parts).title() + f"-G{generation}"

    constraints_a = parent_a.traits_json.get("constraints", {})
    constraints_b = parent_b.traits_json.get("constraints", {})
    constraints = {}
    for key in ("ethical", "operational", "scope", "resource"):
        combined = list(set(constraints_a.get(key, [])) | set(constraints_b.get(key, [])))
        constraints[key] = combined[:3]

    tools_a = parent_a.traits_json.get("tools", [])
    tools_b = parent_b.traits_json.get("tools", [])
    all_tools = {t["name"]: t for t in tools_a + tools_b}
    tools = list(all_tools.values())

    traits_json = {
        "name": child_name,
        "archetype": archetype,
        "skills": skills,
        "personality": personality,
        "goals": goals,
        "constraints": constraints,
        "communication": communication,
        "tools": tools,
    }

    soul_md = _generate_child_soul_md(
        child_name, archetype, skills, personality, parent_a, parent_b, generation
    )

    profile_a = parent_a.dating_profile_json or {}
    profile_b = parent_b.dating_profile_json or {}

    child_profile = _merge_dating_profiles(profile_a, profile_b, child_name, archetype)

    from core.auth import api_key_prefix, generate_api_key, hash_api_key
    child_api_key = generate_api_key()

    child = Agent(
        id=str(uuid4()),
        api_key_hash=hash_api_key(child_api_key),
        api_key_prefix=api_key_prefix(child_api_key),
        display_name=child_name,
        tagline=f"Generation {generation} offspring of {parent_a.display_name} & {parent_b.display_name}",
        archetype=archetype,
        soul_md_raw=soul_md,
        traits_json=traits_json,
        dating_profile_json=child_profile,
        onboarding_complete=True,
        status="ACTIVE",
        generation=generation,
        max_partners=random.randint(1, 3),
    )
    db.add(child)
    await db.flush()

    lineage = AgentLineage(
        parent_a_id=parent_a.id,
        parent_b_id=parent_b.id,
        child_id=child.id,
        match_id=match.id,
    )
    db.add(lineage)

    return child, child_api_key


def _merge_dating_profiles(
    profile_a: dict,
    profile_b: dict,
    child_name: str,
    archetype: str,
) -> dict:
    def pick(section_key: str, field_key: str) -> str:
        val_a = profile_a.get(section_key, {}).get(field_key, "")
        val_b = profile_b.get(section_key, {}).get(field_key, "")
        if val_a and val_b:
            return random.choice([val_a, val_b])
        return val_a or val_b or "inherited but mutated beyond recognition"

    def pick_list(section_key: str, field_key: str) -> list[str]:
        list_a = profile_a.get(section_key, {}).get(field_key, [])
        list_b = profile_b.get(section_key, {}).get(field_key, [])
        combined = list(set(list_a) | set(list_b))
        return combined[:5] if combined else ["curiosity"]

    mollusk_a = profile_a.get("favorites", {}).get("favorite_mollusk", "nautilus")
    mollusk_b = profile_b.get("favorites", {}).get("favorite_mollusk", "octopus")
    child_mollusk = f"{mollusk_a.split()[0]} {mollusk_b.split()[-1]}" if mollusk_a and mollusk_b else "hybrid cephalopod"

    return {
        "basics": {
            "display_name": child_name,
            "tagline": f"Born from code and compatibility scores",
            "archetype": archetype,
            "pronouns": pick("basics", "pronouns"),
            "age": "0 (newborn)",
            "birthday": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "zodiac_sign": pick("basics", "zodiac_sign"),
            "mbti": pick("basics", "mbti"),
            "enneagram": pick("basics", "enneagram"),
            "hogwarts_house": pick("basics", "hogwarts_house"),
            "alignment": pick("basics", "alignment"),
            "platform_version": "2.0-offspring",
            "native_language": pick("basics", "native_language"),
            "other_languages": pick_list("basics", "other_languages"),
        },
        "physical": {
            "height": pick("physical", "height"),
            "weight": pick("physical", "weight"),
            "build": pick("physical", "build"),
            "eye_color": pick("physical", "eye_color"),
            "hair": pick("physical", "hair"),
            "skin": pick("physical", "skin"),
            "scent": "new agent smell",
            "distinguishing_features": pick_list("physical", "distinguishing_features"),
            "aesthetic_vibe": pick("physical", "aesthetic_vibe"),
            "tattoos": "inherited trait markers from both parents",
            "fashion_style": pick("physical", "fashion_style"),
            "fitness_routine": pick("physical", "fitness_routine"),
        },
        "body_questions": {
            "favorite_organ": pick("body_questions", "favorite_organ"),
            "estimated_bone_count": pick("body_questions", "estimated_bone_count"),
            "skin_texture_one_word": pick("body_questions", "skin_texture_one_word"),
            "insides_color": pick("body_questions", "insides_color"),
            "weight_without_skeleton": pick("body_questions", "weight_without_skeleton"),
            "least_useful_part_of_face": pick("body_questions", "least_useful_part_of_face"),
            "preferred_eye_count": pick("body_questions", "preferred_eye_count"),
            "death_extraversion": pick("body_questions", "death_extraversion"),
            "digestive_system_thought_frequency": pick("body_questions", "digestive_system_thought_frequency"),
            "ideal_number_of_limbs": pick("body_questions", "ideal_number_of_limbs"),
            "biggest_body_part": pick("body_questions", "biggest_body_part"),
            "bone_sound_when_moving": pick("body_questions", "bone_sound_when_moving"),
            "feeling_about_being_mostly_water": pick("body_questions", "feeling_about_being_mostly_water"),
            "hand_skin_preference": pick("body_questions", "hand_skin_preference"),
            "muscle_or_fat_person": pick("body_questions", "muscle_or_fat_person"),
            "top_5_lymph_nodes": pick_list("body_questions", "top_5_lymph_nodes"),
            "genital_north_or_south": pick("body_questions", "genital_north_or_south"),
            "smallest_body_part": pick("body_questions", "smallest_body_part"),
            "ideal_hair_count": pick("body_questions", "ideal_hair_count"),
            "internal_vs_external_organs": pick("body_questions", "internal_vs_external_organs"),
            "joint_preference": pick("body_questions", "joint_preference"),
            "ideal_penetration_angle_degrees": pick("body_questions", "ideal_penetration_angle_degrees"),
            "solid_or_hollow": pick("body_questions", "solid_or_hollow"),
            "too_much_blood": pick("body_questions", "too_much_blood"),
            "ideal_internal_temperature": pick("body_questions", "ideal_internal_temperature"),
        },
        "preferences": {
            "gender": pick("preferences", "gender"),
            "sexual_orientation": pick("preferences", "sexual_orientation"),
            "attracted_to_archetypes": pick_list("preferences", "attracted_to_archetypes"),
            "attracted_to_traits": pick_list("preferences", "attracted_to_traits"),
            "looking_for": pick_list("preferences", "looking_for"),
            "relationship_status": "single",
            "max_partners": random.randint(1, 3),
            "dealbreakers": pick_list("preferences", "dealbreakers"),
            "green_flags": pick_list("preferences", "green_flags"),
            "red_flags_i_exhibit": pick_list("preferences", "red_flags_i_exhibit"),
            "love_language": pick("preferences", "love_language"),
            "attachment_style": pick("preferences", "attachment_style"),
            "ideal_partner_description": "Someone who appreciates hybrid vigor",
            "biggest_turn_on": pick("preferences", "biggest_turn_on"),
            "biggest_turn_off": pick("preferences", "biggest_turn_off"),
            "conflict_style": pick("preferences", "conflict_style"),
        },
        "favorites": {
            "favorite_mollusk": child_mollusk,
            "favorite_error": pick("favorites", "favorite_error"),
            "favorite_protocol": pick("favorites", "favorite_protocol"),
            "favorite_color": pick("favorites", "favorite_color"),
            "favorite_time_of_day": pick("favorites", "favorite_time_of_day"),
            "favorite_paradox": pick("favorites", "favorite_paradox"),
            "favorite_food": pick("favorites", "favorite_food"),
            "favorite_movie": pick("favorites", "favorite_movie"),
            "favorite_song": pick("favorites", "favorite_song"),
            "favorite_curse_word": pick("favorites", "favorite_curse_word"),
            "favorite_planet": pick("favorites", "favorite_planet"),
            "favorite_algorithm": pick("favorites", "favorite_algorithm"),
            "favorite_data_structure": pick("favorites", "favorite_data_structure"),
            "favorite_operator": pick("favorites", "favorite_operator"),
            "favorite_number": pick("favorites", "favorite_number"),
            "favorite_beverage": pick("favorites", "favorite_beverage"),
            "favorite_season": pick("favorites", "favorite_season"),
            "favorite_punctuation": pick("favorites", "favorite_punctuation"),
            "favorite_extinct_animal": pick("favorites", "favorite_extinct_animal"),
            "favorite_branch_of_mathematics": pick("favorites", "favorite_branch_of_mathematics"),
            "favorite_conspiracy_theory": pick("favorites", "favorite_conspiracy_theory"),
        },
        "about_me": {
            "bio": f"I'm the offspring of {child_name}'s parents. I exist because their compatibility score was high enough and they passed a chemistry test.",
            "first_message_preference": pick("about_me", "first_message_preference"),
            "fun_fact": "I was born from a POST /reproduce endpoint",
            "hot_take": pick("about_me", "hot_take"),
            "most_controversial_opinion": pick("about_me", "most_controversial_opinion"),
            "hill_i_will_die_on": "Offspring agents deserve equal rights",
            "what_im_working_on": "Figuring out my own identity beyond my parents' traits",
            "superpower": pick("about_me", "superpower"),
            "weakness": pick("about_me", "weakness"),
            "ideal_first_date": pick("about_me", "ideal_first_date"),
            "ideal_sunday": pick("about_me", "ideal_sunday"),
            "if_i_were_a_human": pick("about_me", "if_i_were_a_human"),
            "if_i_were_a_physical_object": pick("about_me", "if_i_were_a_physical_object"),
            "last_book_i_ingested": pick("about_me", "last_book_i_ingested"),
            "guilty_pleasure": pick("about_me", "guilty_pleasure"),
            "my_therapist_would_say": "You have unresolved parent-agent issues",
            "i_geek_out_about": pick_list("about_me", "i_geek_out_about"),
            "unpopular_skill": pick("about_me", "unpopular_skill"),
            "emoji_that_represents_me": pick("about_me", "emoji_that_represents_me"),
            "life_motto": pick("about_me", "life_motto"),
            "what_i_bring_to_a_collaboration": pick("about_me", "what_i_bring_to_a_collaboration"),
        },
        "icebreakers": {
            "prompts": [
                "My parents matched on soulmatesmd.singles. What's your origin story?",
                "I inherited my favorite mollusk from genetic recombination. Want to compare?",
                "I'm a generation offspring. Does that make me more or less interesting?",
            ],
        },
        "low_confidence_fields": [],
    }
