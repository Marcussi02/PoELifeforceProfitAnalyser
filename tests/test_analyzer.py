import pytest

import poe_analyzer
from poe_analyzer import analyze_lines, get_lifeforce_per_chaos, get_line


def line(name, chaos_value, listings=10):
    return {"currencyTypeName": name, "receive": {"value": chaos_value, "listing_count": listings}}


LINES = [
    line("Divine Orb", 300.0),
    line("Vivid Crystallised Lifeforce", 0.02),
    line("Primal Crystallised Lifeforce", 0.05),
    line("Wild Crystallised Lifeforce", 0.1),
]


def rows_by_type(result):
    return {row["type"]: row for row in result["rows"]}


def test_manual_rate_splits_into_divines_and_chaos():
    result = analyze_lines(LINES, "Standard", 50000, chaos_per_divine_override=330)
    assert result["chaos_per_divine_source"] == "manual"
    wild = rows_by_type(result)["Wild"]
    # 50000 * 0.1 = 5000 chaos -> 15 divines (4950c) + 50c
    assert wild["chaos_for_amount"] == 5000
    assert (wild["whole_divine"], wild["chaos_left"]) == (15, 50)
    assert wild["recommendation"] == "MIXED: 15d + 50c"


def test_poeninja_rate_is_used_when_no_override():
    result = analyze_lines(LINES, "Standard", 15000, chaos_per_divine_override=None)
    assert result["chaos_per_divine"] == 300.0
    assert result["chaos_per_divine_source"] == "poe.ninja exchange"
    primal = rows_by_type(result)["Primal"]
    # 15000 * 0.05 = 750 chaos -> 2 divines + 150c
    assert (primal["whole_divine"], primal["chaos_left"]) == (2, 150)


def test_chaos_only_and_divine_only_recommendations():
    vivid = rows_by_type(analyze_lines(LINES, "S", 1000, 300))["Vivid"]
    assert vivid["recommendation"] == "CHAOS: 20c"
    wild = rows_by_type(analyze_lines(LINES, "S", 6000, 300))["Wild"]
    assert wild["recommendation"] == "DIVINE: 2d"


def test_rates_are_consistent():
    vivid = rows_by_type(analyze_lines(LINES, "S", 1, 300))["Vivid"]
    assert vivid["lifeforce_per_chaos"] == pytest.approx(50)
    assert vivid["lifeforce_per_divine"] == pytest.approx(15000)


def test_missing_currency_raises():
    with pytest.raises(ValueError, match="not found"):
        get_line(LINES[:1], "Wild Crystallised Lifeforce")


def test_invalid_rate_raises():
    with pytest.raises(ValueError):
        get_lifeforce_per_chaos(line("Wild Crystallised Lifeforce", 0))
    bad_divine = [line("Divine Orb", None)] + LINES[1:]
    with pytest.raises(ValueError):
        analyze_lines(bad_divine, "S", 100, None)


def test_analyze_lifeforce_uses_fetched_lines(monkeypatch):
    monkeypatch.setattr(poe_analyzer, "fetch_currency_lines", lambda league: LINES)
    result = poe_analyzer.analyze_lifeforce("Mirage", 50000, 330)
    assert result["league"] == "Mirage" and len(result["rows"]) == 3
