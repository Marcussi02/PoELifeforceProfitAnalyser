import argparse
import math
from typing import Any, Dict, List

import requests

API_URL = "https://poe.ninja/api/data/currencyoverview"
TARGET_LIFEFORCES = {
    "Vivid Crystallised Lifeforce": "Vivid",
    "Primal Crystallised Lifeforce": "Primal",
    "Wild Crystallised Lifeforce": "Wild",
}


def analyze_lifeforce(league: str, amount: float, chaos_per_divine_override: float | None = None) -> Dict[str, Any]:
    lines = fetch_currency_lines(league)
    rate_source = "manual"
    if chaos_per_divine_override is not None:
        chaos_per_divine = float(chaos_per_divine_override)
    else:
        divine_line = get_line(lines, "Divine Orb")
        divine_receive = divine_line.get("receive", {})
        chaos_per_divine = divine_receive.get("value")
        if not isinstance(chaos_per_divine, (int, float)) or chaos_per_divine <= 0:
            raise ValueError("Invalid Divine Orb receive.value (chaos per divine) in API response.")
        rate_source = "poe.ninja exchange"
    rows: List[Dict[str, Any]] = []
    for api_name, short_name in TARGET_LIFEFORCES.items():
        line = get_line(lines, api_name)
        receive_data = line.get("receive", {})
        lifeforce_per_chaos = get_lifeforce_per_chaos(line)  # derived from receive-side exchange rate
        chaos_per_lifeforce = receive_data.get("value")  # sell-side rate: chaos received per lifeforce
        if not isinstance(chaos_per_lifeforce, (int, float)) or chaos_per_lifeforce <= 0:
            raise ValueError(f"Invalid receive.value for {api_name}.")

        divine_per_lifeforce = float(chaos_per_lifeforce) / float(chaos_per_divine)
        chaos_per_lifeforce_from_divine = divine_per_lifeforce * float(chaos_per_divine)
        lifeforce_per_divine = lifeforce_per_chaos * float(chaos_per_divine)
        total_chaos_whole = math.floor(amount * chaos_per_lifeforce_from_divine)
        whole_divine = math.floor(total_chaos_whole / float(chaos_per_divine))
        chaos_left = max(0, total_chaos_whole - int(whole_divine * float(chaos_per_divine)))
        recommendation = (
            f"MIXED: {whole_divine}d + {chaos_left}c"
            if whole_divine > 0 and chaos_left > 0
            else (f"DIVINE: {whole_divine}d" if whole_divine > 0 else f"CHAOS: {chaos_left}c")
        )

        rows.append(
            {
                "type": short_name,
                "lifeforce_per_chaos": lifeforce_per_chaos,
                "lifeforce_per_divine": lifeforce_per_divine,
                "divine_per_lifeforce": divine_per_lifeforce,
                "chaos_per_lifeforce_from_divine": chaos_per_lifeforce_from_divine,
                "chaos_for_amount": total_chaos_whole,
                "whole_divine": whole_divine,
                "chaos_left": chaos_left,
                "recommendation": recommendation,
                "exchange_listings": receive_data.get("listing_count", 0),
            }
        )

    return {
        "league": league,
        "amount": amount,
        "chaos_per_divine": float(chaos_per_divine),
        "chaos_per_divine_source": rate_source,
        "rows": rows,
    }


def fetch_currency_lines(league: str) -> List[Dict[str, Any]]:
    response = requests.get(
        API_URL,
        params={"league": league, "type": "Currency"},
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    lines = data.get("lines", [])
    if not isinstance(lines, list):
        raise ValueError("Unexpected poe.ninja response format: 'lines' is missing.")
    return lines


def get_line(lines: List[Dict[str, Any]], currency_name: str) -> Dict[str, Any]:
    for line in lines:
        if line.get("currencyTypeName") == currency_name:
            return line
    raise ValueError(f"Currency not found in response: {currency_name}")


def get_lifeforce_per_chaos(lifeforce_line: Dict[str, Any]) -> float:
    receive_data = lifeforce_line.get("receive", {})
    chaos_per_lifeforce = receive_data.get("value")
    if not isinstance(chaos_per_lifeforce, (int, float)) or chaos_per_lifeforce <= 0:
        raise ValueError(
            f"Invalid receive.value for {lifeforce_line.get('currencyTypeName', 'unknown lifeforce')}."
        )
    return 1.0 / float(chaos_per_lifeforce)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check whether to sell Vivid/Primal/Wild lifeforce as chaos or divine."
    )
    parser.add_argument(
        "--league",
        default="Mirage",
        help="Path of Exile league name, e.g. Standard, Necropolis, Settlers.",
    )
    parser.add_argument(
        "--amount",
        type=float,
        default=50000,
        help="Lifeforce amount to evaluate for each color.",
    )
    parser.add_argument(
        "--chaos-per-divine",
        type=float,
        default=330.0,
        help="Override exchange rate for divine in chaos (default: 330).",
    )
    parser.add_argument(
        "--use-poeninja-divine-rate",
        action="store_true",
        help="Use Divine Orb rate from poe.ninja exchange instead of --chaos-per-divine.",
    )
    args = parser.parse_args()

    league = args.league.strip() or "Standard"
    chaos_per_divine_override = None if args.use_poeninja_divine_rate else args.chaos_per_divine

    try:
        result = analyze_lifeforce(league, args.amount, chaos_per_divine_override)
    except (requests.RequestException, ValueError) as exc:
        print(f"Error fetching/analyzing market data: {exc}")
        return

    print(f"League: {result['league']}")
    print(
        f"Currency Exchange Rate: 1 Divine ~= {result['chaos_per_divine']:.2f} Chaos "
        f"(source: {result['chaos_per_divine_source']})"
    )
    print(f"Checked amount per color: {result['amount']:,.0f} lifeforce")
    print("-" * 128)
    print(
        f"{'Type':<8} | {'LF/Chaos':>10} | {'LF/Divine':>12} | {'Chaos/LF*':>10} | "
        f"{'Chaos Out':>10} | {'Divine Out':>10} | {'Chaos Left':>10} | {'Best Strategy':>24}"
    )
    print("-" * 128)

    for row in result["rows"]:
        print(
            f"{row['type']:<8} | {row['lifeforce_per_chaos']:>10.4f} | {row['lifeforce_per_divine']:>12.2f} | "
            f"{row['chaos_per_lifeforce_from_divine']:>10.4f} | {row['chaos_for_amount']:>10} | {row['whole_divine']:>10} | "
            f"{row['chaos_left']:>10} | {row['recommendation']:>24}"
        )

    print("-" * 128)
    print("Note: Chaos/LF* is computed from Divine/LF using your chaos-per-divine rate.")


if __name__ == "__main__":
    main()
