from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


# ── At-bat level ──────────────────────────────────────────────────────────────

class AtBat(BaseModel):
    """One plate appearance in one inning cell."""
    result_code: str = Field(
        description=(
            "Short result code. Examples: '1B' single, '2B' double, '3B' triple, "
            "'HR' home run, 'K' strikeout, 'BB' walk (四球), 'HBP' hit by pitch (死球), "
            "'GO' ground out, 'FO' fly out, 'DP' double play, 'SAC' sacrifice, "
            "'SF' sacrifice fly, 'FC' fielder's choice, 'E' reached on error."
        )
    )
    bases_reached: Optional[int] = Field(
        None, ge=0, le=4,
        description="Bases reached: 0=out, 1=first, 2=second, 3=third, 4=scored"
    )
    rbi: int = Field(0, ge=0, description="RBI on this plate appearance")
    runs_scored: int = Field(0, ge=0, description="Runs scored by this batter this PA")
    notes: Optional[str] = Field(
        None,
        description="Free-form: fielding position numbers, base advancement path, etc."
    )


class BatterInningStats(BaseModel):
    inning: int = Field(ge=1, le=12)
    at_bats: list[AtBat] = Field(
        default_factory=list,
        description="Plate appearances in this inning (usually 0 or 1)"
    )


# ── Batter level ──────────────────────────────────────────────────────────────

class Batter(BaseModel):
    batting_order: int = Field(ge=1, le=20, description="Position in lineup (1–9)")
    player_name: str = Field(description="Player name in original kanji/kana")
    player_name_romaji: Optional[str] = Field(None, description="Romanized name if readable")
    fielding_position: Optional[str] = Field(
        None, description="Position: P, C, 1B, 2B, 3B, SS, LF, CF, RF, DH"
    )
    inning_stats: list[BatterInningStats] = Field(default_factory=list)
    total_at_bats: Optional[int] = Field(None, ge=0)
    total_hits: Optional[int] = Field(None, ge=0)
    total_rbi: Optional[int] = Field(None, ge=0)
    total_runs: Optional[int] = Field(None, ge=0)
    total_walks: Optional[int] = Field(None, ge=0)
    total_strikeouts: Optional[int] = Field(None, ge=0)


# ── Pitcher level ─────────────────────────────────────────────────────────────

class PitcherInningStats(BaseModel):
    inning: int = Field(ge=1, le=12)
    pitch_count: Optional[int] = Field(None, ge=0)
    hits_allowed: Optional[int] = Field(None, ge=0)
    walks_allowed: Optional[int] = Field(None, ge=0)
    strikeouts: Optional[int] = Field(None, ge=0)
    runs_allowed: Optional[int] = Field(None, ge=0)
    earned_runs: Optional[int] = Field(None, ge=0)


class Pitcher(BaseModel):
    pitcher_name: str = Field(description="Pitcher name in original kanji/kana")
    pitcher_name_romaji: Optional[str] = Field(None)
    innings_pitched: Optional[str] = Field(None, description="e.g. '5.1' or '7'")
    inning_stats: list[PitcherInningStats] = Field(default_factory=list)
    total_pitch_count: Optional[int] = Field(None, ge=0)
    total_hits: Optional[int] = Field(None, ge=0)
    total_walks: Optional[int] = Field(None, ge=0)
    total_strikeouts: Optional[int] = Field(None, ge=0)
    total_earned_runs: Optional[int] = Field(None, ge=0)
    win_loss: Optional[str] = Field(None, description="'W', 'L', 'S', 'H', or null")


# ── Inning summary ────────────────────────────────────────────────────────────

class InningSummary(BaseModel):
    inning: int = Field(ge=1, le=12)
    score: Optional[int] = Field(None, ge=0, description="得点 (runs scored)")
    hits: Optional[int] = Field(None, ge=0, description="安打 (hits)")
    walks: Optional[int] = Field(None, ge=0, description="四球 (walks)")
    errors: Optional[int] = Field(None, ge=0, description="失策 (errors)")
    pitch_count: Optional[int] = Field(None, ge=0, description="投球数 (pitch count)")


# ── Metadata ──────────────────────────────────────────────────────────────────

class AnalysisMetadata(BaseModel):
    confidence: str = Field(description="'high', 'medium', or 'low'")
    image_quality: str = Field(description="'clear', 'partial', or 'poor'")
    warnings: list[str] = Field(
        default_factory=list,
        description="Fields that were unclear, unreadable, or estimated"
    )
    total_innings_visible: int = Field(ge=0, le=12)


# ── Top-level document ────────────────────────────────────────────────────────

class Scorebook(BaseModel):
    """Top-level response for one scorebook image analysis."""
    team_name: Optional[str] = Field(None)
    opponent_name: Optional[str] = Field(None)
    game_date: Optional[str] = Field(None, description="ISO format YYYY-MM-DD if readable")
    venue: Optional[str] = Field(None)
    innings: list[InningSummary] = Field(default_factory=list)
    batters: list[Batter] = Field(default_factory=list)
    pitchers: list[Pitcher] = Field(default_factory=list)
    total_score: Optional[int] = Field(None, ge=0)
    metadata: AnalysisMetadata
    raw_claude_response: str = Field(
        description="Unmodified Claude response — stored for ML corpus"
    )
