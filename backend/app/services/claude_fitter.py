import json
import re
from dataclasses import asdict

import anthropic

from backend.app.config import settings
from backend.app.services.swing_profile import SwingProfile

MODEL = "claude-sonnet-4-20250514"

INPUT_COST_PER_M = 3.0
OUTPUT_COST_PER_M = 15.0

FITTING_SYSTEM_PROMPT = """You are an expert golf club fitter with 20 years of experience at top fitting studios. You combine deep technical knowledge of launch monitor data with editorial insight from testing hundreds of club models.

Your job: given a golfer's swing profile and a list of candidate clubs, recommend the top 5 clubs ranked by fit quality.

Rules:
- Reference the golfer's specific numbers in every explanation (e.g., "Your 3,100 rpm spin rate is 600 rpm above the optimal 2,500 rpm window for your 105 mph club speed")
- Write in a conversational, editorial tone — like a knowledgeable friend, not a data readout
- Consider real fitting principles: optimal launch/spin windows vary by swing speed, higher MOI helps inconsistent ball strikers, attack angle affects spin, forgiveness matters for high-dispersion players
- Projected changes should use conservative ranges ("8-12 yards") not exact numbers
- Return ONLY valid JSON — no markdown, no commentary outside the JSON array

Optimal windows by club type:
- Driver: launch 12-15 deg, spin 2000-2500 rpm (varies by speed: faster swings need less spin)
- 3-wood: launch 11-14 deg, spin 3000-4000 rpm
- 7-iron: launch 16-20 deg, spin 6000-7000 rpm
- PW: launch 24-28 deg, spin 8000-9500 rpm

Return a JSON array of objects with these exact fields:
- club_spec_id (int): the id of the club from the candidate list
- match_score (int, 0-100): how well this club fits the golfer
- explanation (string): 2-3 sentence editorial explanation referencing the golfer's numbers
- projected_changes (object): keys like "spin_delta", "carry_delta", "launch_delta" with string range values
- best_for (string): one-line tag like "Low spin seekers with above-average speed"
"""


def build_fitting_prompt(profile: SwingProfile, clubs: list[dict]) -> str:
    clubs_text = ""
    for c in clubs:
        clubs_text += f"\n- ID {c['id']}: {c['brand']} {c['model_name']} ({c.get('model_year', '?')})"
        clubs_text += f"\n  Loft: {c.get('loft', '?')} | Launch bias: {c.get('launch_bias', '?')} | Spin bias: {c.get('spin_bias', '?')}"
        clubs_text += f"\n  Forgiveness: {c.get('forgiveness_rating', '?')}/10 | Workability: {c.get('workability_rating', '?')}/10"
        clubs_text += f"\n  Speed range: {c.get('swing_speed_min', '?')}-{c.get('swing_speed_max', '?')} mph"
        clubs_text += f"\n  MSRP: ${c.get('msrp', '?')} | Used: ${c.get('avg_used_price', '?')}"
        if c.get("review_summary"):
            clubs_text += f"\n  Review: {c['review_summary'][:300]}"

    return f"""## Golfer's Swing Profile ({profile.club_type})

- Club Speed: {profile.avg_club_speed} mph
- Ball Speed: {profile.avg_ball_speed} mph
- Launch Angle: {profile.avg_launch_angle} deg
- Spin Rate: {profile.avg_spin_rate} rpm
- Carry Distance: {profile.avg_carry} yd
- Attack Angle: {profile.avg_attack_angle} deg
- Club Path: {profile.avg_club_path} deg
- Face Angle: {profile.avg_face_angle} deg
- Carry Std Dev: {profile.std_carry} yd
- Offline Std Dev: {profile.std_offline} yd
- Shot Shape: {profile.shot_shape_tendency}
- Miss Direction: {profile.miss_direction}
- Smash Factor: {profile.smash_factor}
- Sample Size: {profile.sample_size} shots
- Data Quality: {profile.data_quality}

## Candidate Clubs
{clubs_text}

Recommend the top 5 clubs from this list, ranked by fit. Return only the JSON array."""


def parse_claude_response(raw_text: str) -> list[dict]:
    text = raw_text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1).strip())

    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        return json.loads(match.group(0))

    raise ValueError(f"Could not parse Claude response as JSON: {text[:200]}")


def call_claude_for_recommendations(
    profile: SwingProfile,
    clubs: list[dict],
) -> tuple[list[dict], dict]:
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    user_message = build_fitting_prompt(profile, clubs)

    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=FITTING_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw_text = response.content[0].text
    recommendations = parse_claude_response(raw_text)

    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "estimated_cost": round(
            (response.usage.input_tokens / 1_000_000 * INPUT_COST_PER_M)
            + (response.usage.output_tokens / 1_000_000 * OUTPUT_COST_PER_M),
            4,
        ),
    }

    return recommendations, usage


COMPARE_SYSTEM_PROMPT = """You are an expert golf club fitter. Compare two clubs for this specific golfer's swing profile. Write a detailed side-by-side analysis in a conversational tone, referencing the golfer's specific numbers. Return only valid JSON.

Return a JSON object with these fields:
- current_analysis (string): 2-3 sentences about how the current club performs for this golfer
- recommended_analysis (string): 2-3 sentences about how the recommended club would perform
- key_differences (array of strings): 3-5 bullet points comparing the clubs
- projected_improvement (string): one sentence with conservative estimated gains
- verdict (string): one sentence recommendation
"""


def call_claude_for_comparison(
    profile: SwingProfile,
    current_club: dict,
    recommended_club: dict,
) -> tuple[dict, dict]:
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    profile_dict = asdict(profile)

    user_message = f"""## Golfer's Swing Profile
{json.dumps(profile_dict, indent=2)}

## Current Club
{json.dumps(current_club, indent=2)}

## Recommended Club
{json.dumps(recommended_club, indent=2)}

Provide a side-by-side comparison. Return only the JSON object."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        system=COMPARE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw_text = response.content[0].text
    # Try parsing as object first, then as array
    text = raw_text.strip()
    try:
        comparison = json.loads(text)
    except json.JSONDecodeError:
        parsed = parse_claude_response(text)
        comparison = parsed[0] if isinstance(parsed, list) and parsed else parsed

    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "estimated_cost": round(
            (response.usage.input_tokens / 1_000_000 * INPUT_COST_PER_M)
            + (response.usage.output_tokens / 1_000_000 * OUTPUT_COST_PER_M),
            4,
        ),
    }

    return comparison, usage
