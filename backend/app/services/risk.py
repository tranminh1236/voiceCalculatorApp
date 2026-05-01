"""Risk analysis: per-bet payout / loss / recommendation.

Pure function: takes a capture's audio groups + multipliers + provinces,
returns a report with one RiskEntry per parsed audio number. No DB, no I/O.

The recommendation logic flags a bet as 'pass' if its net-if-win is below
a user-set threshold (default 0 = at least break even).
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class AudioGroupInput:
    group_index: int
    multiplier: float
    provinces: list[str]
    parsed_numbers: list[float]


@dataclass(frozen=True)
class RiskInput:
    groups: list[AudioGroupInput]
    threshold: float = 0.0


@dataclass(frozen=True)
class RiskEntry:
    group_index: int
    audio_index: int               # 0-based position within parsed_numbers
    stake: float                   # raw value from audio
    num_provinces: int
    effective_stake: float         # stake × num_provinces
    multiplier: float
    payout_if_hits: float          # stake × multiplier (per single-province hit)
    net_if_hits: float             # payout_if_hits - total_capital
    capital_share: float           # effective_stake / total_capital (0..1)
    recommendation: str            # 'take' | 'pass'


@dataclass(frozen=True)
class RiskReport:
    total_capital: float
    threshold: float
    entries: list[RiskEntry]
    take_count: int
    pass_count: int


def compute_risk(inp: RiskInput) -> RiskReport:
    # Phase 1: compute total_capital
    total_capital = 0.0
    for g in inp.groups:
        n_prov = len(g.provinces)
        for stake in g.parsed_numbers:
            total_capital += stake * n_prov

    # Phase 2: build entries
    entries: list[RiskEntry] = []
    for g in inp.groups:
        n_prov = len(g.provinces)
        for idx, stake in enumerate(g.parsed_numbers):
            effective = stake * n_prov
            payout = stake * g.multiplier  # per single-province hit
            net = payout - total_capital
            share = effective / total_capital if total_capital > 0 else 0.0
            rec = "take" if net >= inp.threshold else "pass"
            entries.append(RiskEntry(
                group_index=g.group_index,
                audio_index=idx,
                stake=stake,
                num_provinces=n_prov,
                effective_stake=effective,
                multiplier=g.multiplier,
                payout_if_hits=payout,
                net_if_hits=net,
                capital_share=share,
                recommendation=rec,
            ))

    take_count = sum(1 for e in entries if e.recommendation == "take")
    pass_count = sum(1 for e in entries if e.recommendation == "pass")
    return RiskReport(
        total_capital=total_capital,
        threshold=inp.threshold,
        entries=entries,
        take_count=take_count,
        pass_count=pass_count,
    )
