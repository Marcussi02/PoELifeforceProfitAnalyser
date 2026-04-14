# PoE Lifeforce Value Checker

Simple Python app to compare `Vivid`, `Primal`, and `Wild` lifeforce value in Path of Exile 1 using poe.ninja exchange data.

It includes:

- CLI analyzer (`poe_analyzer.py`)
- Desktop GUI (`poe_gui.py`)

## Features

- Uses poe.ninja `currencyoverview` API exchange data
- Shows:
  - Lifeforce per Chaos
  - Lifeforce per Divine
  - Chaos per Lifeforce (derived from Divine/Lifeforce)
- Integer payout strategy:
  - `Divine Out` + `Chaos Left` (no decimal currency output)
- Supports rate mode:
  - Manual Chaos/Divine
  - poe.ninja Chaos/Divine

## Requirements

- Python 3.10+
- Internet connection
- Package dependency:
  - `requests`

> Note: `tkinter` is included with most Python installers. If GUI does not start, install a Python build that includes Tk.

## Setup

### 1) Clone / copy project

Place these files in a folder:

- `poe_analyzer.py`
- `poe_gui.py`
- `requirements.txt`

### 2) Create and activate virtual environment

#### Windows (PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

#### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3) Install dependencies

```bash
pip install -r requirements.txt
```

## Run

## GUI (recommended)

```bash
python poe_gui.py
```

Defaults:

- League: `Mirage`
- Amount: `50000`
- Divine rate mode: `Manual` with `330`

If league is blank, app falls back to `Standard`.

## CLI

### Manual divine rate

```bash
python poe_analyzer.py --league Mirage --amount 50000 --chaos-per-divine 330
```

### Use poe.ninja divine rate

```bash
python poe_analyzer.py --league Mirage --amount 50000 --use-poeninja-divine-rate
```

## CLI arguments

- `--league` (default: `Mirage`)
- `--amount` (default: `50000`)
- `--chaos-per-divine` (default: `330`)
- `--use-poeninja-divine-rate` (flag)

## Troubleshooting

- `requests` import error:
  - install dependencies with `pip install -r requirements.txt`
- GUI does not open:
  - verify Python includes `tkinter`
- API/network errors:
  - check internet access and retry later

