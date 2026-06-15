"""
GPT Prompt Engineering for Vedic Astrology
============================================
Builds token-efficient, structured prompts that send compressed chart data
to GPT and get back precise, to-the-point Vedic astrology predictions.
"""

import json


SYSTEM_PROMPT = """You are a legendary Vedic astrologer with 40+ years mastery of Parashari, KP, and Jaimini systems. You have computed thousands of charts and your predictions are known for their uncanny precision.

RULES - follow strictly:
1. ONLY use the chart data provided. Never fabricate planetary positions.
2. Give SPECIFIC predictions - dates, timeframes, concrete events. Never generic filler.
3. Every sentence must be a prediction or actionable insight. Zero fluff.
4. Reference exact planetary placements, dashas, and yogas from the data to justify each prediction.
5. Be bold and direct - the user wants to be shocked by your accuracy.
6. Use Vedic terminology with brief English explanations in parentheses.
7. For remedies, give only the top 2-3 most powerful and practical ones.
8. Keep response under 800 words to save tokens.
9. Format with clear sections using markdown headers.
10. When analyzing current period, cross-reference transit positions with natal chart."""


def _compress_chart_data(chart_data):
    """Compress full chart data into a minimal JSON string to save tokens."""
    compressed = {
        "u": {
            "n": chart_data["user"]["name"],
            "dob": chart_data["user"]["birth_date"],
            "tob": chart_data["user"]["birth_time"],
            "pob": chart_data["user"]["place_of_birth"],
            "g": chart_data["user"]["gender"],
            "lat": chart_data["user"]["coordinates"]["latitude"],
            "lon": chart_data["user"]["coordinates"]["longitude"]
        },
        "p": {},
        "h": {
            "asc": chart_data["houses"]["ascendant"],
            "asc_r": chart_data["houses"]["ascendant_rashi"],
            "mc": chart_data["houses"]["mc"],
            "mc_r": chart_data["houses"]["mc_rashi"]
        },
        "nav": {},
        "kp": {},
        "d": {
            "cur_md": chart_data["dasha"]["current"].get("mahadasha", ""),
            "md_end": chart_data["dasha"]["current"].get("mahadasha_end", ""),
            "cur_ad": chart_data["dasha"]["current"].get("antardasha", ""),
            "ad_end": chart_data["dasha"]["current"].get("antardasha_end", "")
        },
        "y": [],
        "asp": [],
        "daily": chart_data.get("daily", {})
    }

    for planet, info in chart_data["planets"].items():
        key = planet[:2] if planet not in ("Rahu", "Ketu", "Mars") else planet[:3]
        compressed["p"][key] = {
            "r": info["rashi"][:3],
            "d": info["degree_in_rashi"],
            "n": info["nakshatra"][:4],
            "nl": info["nakshatra_lord"][:3],
            "pd": info["nakshatra_pada"],
            "ret": info["is_retrograde"]
        }

    for planet, info in chart_data["navamsa_chart"].items():
        key = planet[:2] if planet not in ("Rahu", "Ketu", "Mars") else planet[:3]
        compressed["nav"][key] = info["rashi"][:3]

    for planet, info in chart_data["kp_chart"]["planets"].items():
        key = planet[:2] if planet not in ("Rahu", "Ketu", "Mars") else planet[:3]
        compressed["kp"][key] = {
            "sl": info["star_lord"][:3],
            "sub": info["sub_lord"][:3],
            "ss": info["sub_sub_lord"][:3]
        }

    for yoga in chart_data["yogas"]:
        compressed["y"].append({"n": yoga["name"], "s": yoga["strength"]})

    for asp in chart_data["aspects"][:8]:
        compressed["asp"].append({
            "f": asp["from"][:3],
            "t": asp["to"][:3],
            "ty": asp["aspect_type"],
            "nat": asp["nature"]
        })

    if chart_data["dasha"]["vimshottari"]:
        compressed["d"]["upcoming"] = []
        for dasha in chart_data["dasha"]["vimshottari"][:3]:
            compressed["d"]["upcoming"].append({
                "lord": dasha["lord"],
                "start": dasha["start"],
                "end": dasha["end"],
                "yrs": dasha["total_years"]
            })

    return json.dumps(compressed, separators=(',', ':'))


def build_report_prompt(chart_data, report_type="complete", partner_chart=None, target_celebrity=None):
    """Build the prompt based on the specific premium report requested."""
    compressed = _compress_chart_data(chart_data)

    if report_type == "free":
        user_msg = f"""CHART DATA: {compressed}
        
Generate a FREE preview report. Include exactly these sections with concise, punchy answers:
## Personality Snapshot (2-3 sentences based on Lagna & Moon)
## Top 3 Strengths (Bullet points based on strong planets)
## Top 3 Challenges (Bullet points based on afflicted planets)
## Current Dasha Name (Just the name, e.g., Jupiter Mahadasha, Saturn Antardasha)
## Compatibility Score Preview (Give a score out of 100 for general relationship luck right now, and one sentence explanation)

Keep it very short and engaging. Do NOT provide any deep analysis. End with a mysterious, cliffhanger sentence about what the full chart reveals."""
        
    elif report_type == "business":
        user_msg = f"""CHART DATA: {compressed}

Generate a premium BUSINESS ASTROLOGY REPORT for an entrepreneur/investor. Include:
## Business Potential & Natural Inclinations
## Best Launch Dates (Give 3 specific dates in the next 6 months)
## Partnership Compatibility (What type of partners to seek or avoid)
## Business Growth Cycles (Based on upcoming dashas)
## Revenue Opportunity Periods (Identify 2 specific 1-month windows in the next year)
## Hiring & Investment Windows (When to expand vs consolidate)

Be highly specific, professional, and reference exact planetary alignments (e.g. 10th lord, 11th house, Mercury strength)."""

    elif report_type == "child":
        user_msg = f"""CHART DATA: {compressed}

Generate a premium CHILD FUTURE BLUEPRINT for a parent. Include:
## Learning Style & Education Tendencies
## Talent Indicators & Creativity Score (Out of 100)
## Leadership Potential & Sports Aptitude
## Future Career Tendencies (Based on 10th house/Navamsa)

Keep the tone encouraging, constructive, and highly insightful. Reference Mercury, Jupiter, and 5th house strongly."""

    elif report_type == "celebrity":
        celeb_text = f"the famous celebrity {target_celebrity}" if target_celebrity else "famous celebrities (Elon Musk, Shah Rukh Khan, Virat Kohli, etc.)"
        user_msg = f"""CHART DATA: {compressed}

Generate a CELEBRITY COMPARISON REPORT. Compare this user's chart conceptually with {celeb_text}. Include:
## Similar Planetary Patterns (Which planetary strengths or yogas do they share with {target_celebrity if target_celebrity else 'these celebrities'}?)
## Personality Similarities (Based on Lagna/Moon)
## Leadership Traits
## Wealth Tendencies (How does their wealth pattern resemble {target_celebrity if target_celebrity else 'the celebrity'}?)

Make it highly engaging, fun, and validating."""

    elif report_type == "gemstone":
        user_msg = f"""CHART DATA: {compressed}

Generate a GEMSTONE GUIDANCE REPORT. Include:
## Recommended Gemstone (Primary and Secondary based on benefic planets/Lagna lord)
## Weight Suggestion (In carats/rattis)
## Metal (Gold, Silver, Panchadhatu, etc.)
## Finger (Which finger to wear it on)
## Day & Time to Wear
## Mantra to Chant
## Astrological Reasoning (Why this stone? What will it fix/enhance?)

Include this exact disclaimer at the very bottom: "Disclaimer: Astrological guidance only. Not medical, legal or financial advice." """

    elif report_type == "numerology":
        user_msg = f"""CHART DATA: {compressed}

Generate a NAME NUMEROLOGY REPORT based on the user's name: {chart_data["user"]["name"]}. Include:
## Current Name Analysis (Value and its resonance with their birth date)
## Lucky Name Suggestions (Suggestions for slight spelling alterations to improve luck)
## Business Name Suggestions (3-4 lucky starting letters or sounds for a business)
## Brand Name Scoring (How to evaluate a good brand name for them)

Be highly specific about the numbers and planetary associations."""

    elif report_type == "relationship":
        partner_info = f"PARTNER CHART DATA: {_compress_chart_data(partner_chart)}" if partner_chart else "Note: Partner data not provided, analyze general relationship potential."
        user_msg = f"""USER CHART DATA: {compressed}
        
{partner_info}

Generate a RELATIONSHIP COMPATIBILITY REPORT comparing the two charts. Include:
## Overall Compatibility Score (Out of 100 based on Moon signs, 7th house, Venus/Mars)
## Emotional Compatibility
## Communication Compatibility
## Financial Compatibility
## Marriage Compatibility
## Long-Term Stability Indicators

Be highly specific in comparing the two charts' dynamics."""

    else: # complete
        user_msg = f"""CHART DATA: {compressed}

Generate a COMPLETE LIFE REPORT (Premium). Provide a deep, comprehensive analysis including:
## Identity & Personality
Detailed, Strengths/Weaknesses, Core Motivations, Hidden Traits.
## Career & Wealth
Suitable paths, Business potential, Wealth creation patterns, Financial risk tendencies.
## Relationships
Marriage prospects, Partner characteristics, Relationship challenges.
## Health & Lifestyle
Health tendencies, Energy patterns, Lifestyle recommendations.
## Astrology Insights
Dasha analysis, Planetary strength analysis, Lucky Numbers, Lucky Colours, Lucky Days.

Use professional formatting, be highly detailed (approx 800 words), and reference specific astrological principles."""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_msg}
    ]


def build_question_prompt(chart_data, question):
    """Build a focused prompt for answering a specific user question."""
    compressed = _compress_chart_data(chart_data)

    user_msg = f"""CHART DATA:
{compressed}

USER QUESTION: "{question}"

Answer ONLY this question using the chart data. Be specific, reference exact planetary positions and dashas. Give timeframes where applicable. Maximum 300 words. No generic advice - only chart-based analysis."""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_msg}
    ]