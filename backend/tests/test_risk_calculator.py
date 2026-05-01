from app.services.risk import compute_risk, RiskInput, AudioGroupInput


def test_single_group_single_number():
    """1 group × 1 đài × 1 số stake 10 với multiplier 80 → payout 800, capital 10, net +790."""
    inp = RiskInput(
        groups=[
            AudioGroupInput(
                group_index=1,
                multiplier=80.0,
                provinces=["HN"],
                parsed_numbers=[10.0],
            )
        ],
        threshold=0.0,
    )
    report = compute_risk(inp)
    assert report.total_capital == 10.0
    assert len(report.entries) == 1
    e = report.entries[0]
    assert e.group_index == 1
    assert e.stake == 10.0
    assert e.effective_stake == 10.0
    assert e.payout_if_hits == 800.0
    assert e.net_if_hits == 790.0
    assert e.capital_share == 1.0
    assert e.recommendation == "take"


def test_multi_provinces_multiplies_stake():
    """1 group × 2 đài × 1 số stake 10 → effective_stake = 20."""
    inp = RiskInput(
        groups=[AudioGroupInput(group_index=1, multiplier=80.0, provinces=["HN", "DNG"], parsed_numbers=[10.0])],
        threshold=0.0,
    )
    report = compute_risk(inp)
    assert report.total_capital == 20.0
    assert report.entries[0].effective_stake == 20.0
    # payout still per-province (1 đài hit)
    assert report.entries[0].payout_if_hits == 10.0 * 80.0


def test_pass_when_net_below_threshold():
    """5 stake × 80 multiplier = 400 payout. Capital 5+50=55. Net = 400-55 = 345 (take).
    But add another high-stake group: capital = 55 + 1000 = 1055. Net for the 5-stake = 400 - 1055 = -655 → pass."""
    inp = RiskInput(
        groups=[
            AudioGroupInput(group_index=1, multiplier=80.0, provinces=["HN"], parsed_numbers=[5.0, 50.0]),
            AudioGroupInput(group_index=2, multiplier=82.0, provinces=["HN"], parsed_numbers=[1000.0]),
        ],
        threshold=0.0,
    )
    report = compute_risk(inp)
    assert report.total_capital == 5 + 50 + 1000
    by_stake = {e.stake: e for e in report.entries}
    # stake 5: payout 400, net 400 - 1055 = -655 → pass
    assert by_stake[5.0].net_if_hits == 400.0 - 1055.0
    assert by_stake[5.0].recommendation == "pass"
    # stake 50: payout 4000, net 4000 - 1055 = 2945 → take
    assert by_stake[50.0].net_if_hits == 4000.0 - 1055.0
    assert by_stake[50.0].recommendation == "take"
    # stake 1000 in đề×82: payout 82000, net = 82000-1055 = 80945 → take
    assert by_stake[1000.0].net_if_hits == 82000.0 - 1055.0
    assert by_stake[1000.0].recommendation == "take"


def test_threshold_above_zero_makes_more_passes():
    """With threshold=500 and a small bet that nets just +100 → pass."""
    inp = RiskInput(
        groups=[AudioGroupInput(group_index=1, multiplier=10.0, provinces=["HN"], parsed_numbers=[100.0])],
        threshold=500.0,
    )
    report = compute_risk(inp)
    e = report.entries[0]
    assert e.payout_if_hits == 1000.0
    assert e.net_if_hits == 900.0
    assert e.recommendation == "take"  # 900 ≥ 500

    inp2 = RiskInput(
        groups=[AudioGroupInput(group_index=1, multiplier=10.0, provinces=["HN"], parsed_numbers=[100.0])],
        threshold=950.0,
    )
    e2 = compute_risk(inp2).entries[0]
    assert e2.recommendation == "pass"  # 900 < 950


def test_capital_share_sums_to_one():
    inp = RiskInput(
        groups=[
            AudioGroupInput(group_index=1, multiplier=80.0, provinces=["HN"], parsed_numbers=[10.0, 30.0]),
            AudioGroupInput(group_index=2, multiplier=82.0, provinces=["HN", "KH"], parsed_numbers=[20.0]),
        ],
        threshold=0.0,
    )
    report = compute_risk(inp)
    total_share = sum(e.capital_share for e in report.entries)
    assert abs(total_share - 1.0) < 1e-9


def test_empty_groups_returns_zero():
    inp = RiskInput(groups=[], threshold=0.0)
    r = compute_risk(inp)
    assert r.total_capital == 0.0
    assert r.entries == []


def test_zero_stake_entry_is_skipped_in_capital_share():
    """A 0-stake entry shouldn't break capital_share computation."""
    inp = RiskInput(
        groups=[AudioGroupInput(group_index=1, multiplier=80.0, provinces=["HN"], parsed_numbers=[0.0, 10.0])],
        threshold=0.0,
    )
    r = compute_risk(inp)
    assert r.total_capital == 10.0
    by_stake = {e.stake: e for e in r.entries}
    assert by_stake[0.0].capital_share == 0.0
    assert by_stake[10.0].capital_share == 1.0


def test_repeated_number_in_group_each_counts_separately():
    """Rule '2a + 2c': same number read twice → 2 separate entries (each with own stake)."""
    inp = RiskInput(
        groups=[AudioGroupInput(group_index=1, multiplier=80.0, provinces=["HN"], parsed_numbers=[10.0, 10.0])],
        threshold=0.0,
    )
    r = compute_risk(inp)
    assert r.total_capital == 20.0
    assert len(r.entries) == 2
    assert all(e.stake == 10.0 for e in r.entries)


def test_entry_order_preserves_group_then_audio_order():
    inp = RiskInput(
        groups=[
            AudioGroupInput(group_index=1, multiplier=80.0, provinces=["HN"], parsed_numbers=[10.0, 20.0]),
            AudioGroupInput(group_index=2, multiplier=82.0, provinces=["HN"], parsed_numbers=[5.0]),
        ],
        threshold=0.0,
    )
    r = compute_risk(inp)
    # Output entries follow input audio_group order, then audio_index within group
    assert [(e.group_index, e.audio_index, e.stake) for e in r.entries] == [
        (1, 0, 10.0), (1, 1, 20.0), (2, 0, 5.0),
    ]


def test_summary_counts():
    inp = RiskInput(
        groups=[AudioGroupInput(group_index=1, multiplier=80.0, provinces=["HN"], parsed_numbers=[10.0, 5.0])],
        threshold=0.0,
    )
    r = compute_risk(inp)
    # take_count + pass_count == len(entries)
    assert r.take_count + r.pass_count == len(r.entries)
