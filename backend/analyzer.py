import os
import base64
import json
import re

import anthropic
from schemas import Scorebook, AnalysisMetadata

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


SYSTEM_PROMPT = """You are an expert in Japanese baseball scorekeeping (野球スコアブック).
You have deep knowledge of both traditional Japanese scorebook notation and standard baseball statistics.

Your task is to analyze scorebook images and extract all visible data into structured JSON.

## Japanese Scorebook Conventions

### At-bat cell notation:
- Diamond shape (◇) in the center of each cell = one plate appearance
- Lines drawn base-to-base inside the diamond = base advancement path
- A filled/colored diamond or circle = run scored
- Numbers near diamond corners = fielder position numbers:
  1=P(投), 2=C(捕), 3=1B(一), 4=2B(二), 5=3B(三), 6=SS(遊), 7=LF(左), 8=CF(中), 9=RF(右)

### Common result symbols:
- K or 振 = strikeout (三振)
- 四 or 四球 or BB = base on balls (walk)
- 死 or 死球 or HBP = hit by pitch
- S or 犠 = sacrifice bunt (犠打)
- SF or 犠飛 = sacrifice fly (犠飛)
- WP = wild pitch (暴投)
- PB = passed ball (捕逸)
- E followed by a number = error (失策), e.g. E6 = error by shortstop
- DP = double play (併殺)

### Result codes to use in JSON:
1B (single), 2B (double), 3B (triple), HR (home run),
K (strikeout), BB (walk), HBP (hit by pitch),
GO (ground out), FO (fly out), LO (line out),
DP (double play), SAC (sacrifice bunt), SF (sacrifice fly),
FC (fielder's choice), E (error), CI (catcher's interference)

### Summary rows at the bottom of the batter grid:
- 安 or 安打 = hits per inning
- 四 or 四球 = walks per inning
- 失 or 失策 = errors per inning
- 得 or 得点 = runs scored per inning
- 投球数 = pitch count per inning

### Pitcher table (usually at the very bottom):
Contains: pitcher name (氏名), result (勝負), save (セーブ),
innings pitched (投球回), batters faced (打者), pitch count (投球数 or 球数),
hits (安打), home runs (本塁打), sacrifice hits (犠打), sacrifice flies (犠飛),
walks (四球), HBP (死球), strikeouts (三振), wild pitches (暴投), balks (ボーク),
runs (失点), earned runs (自責点)

## Output Instructions
1. Extract every visible batter row, preserving kanji/kana names exactly.
2. If a character is ambiguous, write your best guess followed by ? (e.g. "田?").
3. For each inning cell, determine the at-bat result code.
4. Use null for any value you cannot read clearly.
5. Output ONLY valid JSON — no prose, no markdown fences, no explanation.
6. The metadata.warnings list must contain a string for every field you were uncertain about.
"""

USER_PROMPT = """Analyze this Japanese baseball scorebook image and return a single JSON object.

Use exactly this structure (replace values with what you see in the image):

{
  "team_name": null,
  "opponent_name": null,
  "game_date": null,
  "venue": null,
  "innings": [
    {
      "inning": 1,
      "score": null,
      "hits": null,
      "walks": null,
      "errors": null,
      "pitch_count": null
    }
  ],
  "batters": [
    {
      "batting_order": 1,
      "player_name": "選手名",
      "player_name_romaji": null,
      "fielding_position": null,
      "inning_stats": [
        {
          "inning": 1,
          "at_bats": [
            {
              "result_code": "1B",
              "bases_reached": 1,
              "rbi": 0,
              "runs_scored": 0,
              "notes": null
            }
          ]
        }
      ],
      "total_at_bats": null,
      "total_hits": null,
      "total_rbi": null,
      "total_runs": null,
      "total_walks": null,
      "total_strikeouts": null
    }
  ],
  "pitchers": [
    {
      "pitcher_name": "投手名",
      "pitcher_name_romaji": null,
      "innings_pitched": null,
      "inning_stats": [],
      "total_pitch_count": null,
      "total_hits": null,
      "total_walks": null,
      "total_strikeouts": null,
      "total_earned_runs": null,
      "win_loss": null
    }
  ],
  "total_score": null,
  "metadata": {
    "confidence": "medium",
    "image_quality": "clear",
    "warnings": [],
    "total_innings_visible": 9
  },
  "raw_claude_response": "__PLACEHOLDER__"
}

Important:
- Include one entry in "innings" for every inning column visible in the image.
- Include one entry in "batters" for every batter row visible (batting order 1–9, or more for substitutions).
- If a cell is blank (batter did not bat that inning), omit that inning from the batter's inning_stats.
- Output ONLY the JSON object. No other text."""


def _extract_json(text: str) -> dict:
    """Strip optional markdown fences and parse the first JSON object found."""
    # Remove ```json ... ``` or ``` ... ``` fences
    text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()

    # Find the outermost { ... }
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in response")

    # Walk brackets to find matching closing brace
    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])

    raise ValueError("Unbalanced braces in Claude response")


async def analyze_scorebook_image(image_bytes: bytes, media_type: str) -> Scorebook:
    """
    Send image to Claude Vision and return a validated Scorebook.

    This function is the single abstraction point for the vision backend.
    To swap in a fine-tuned local model in the future, replace the body of
    this function (or add a branch on USE_LOCAL_MODEL env var).
    """
    model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
    image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    client = _get_client()
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": USER_PROMPT,
                    },
                ],
            }
        ],
    )

    raw_text = response.content[0].text

    try:
        data = _extract_json(raw_text)
    except (ValueError, json.JSONDecodeError) as exc:
        return Scorebook(
            metadata=AnalysisMetadata(
                confidence="low",
                image_quality="poor",
                warnings=[f"JSON parse failed: {exc}"],
                total_innings_visible=0,
            ),
            raw_claude_response=raw_text,
        )

    # Overwrite the placeholder with the actual raw text for ML corpus use
    data["raw_claude_response"] = raw_text

    return Scorebook(**data)
