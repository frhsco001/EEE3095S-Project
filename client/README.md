# Battleship PC Client & Automated Test Harness

The client software package consists of:
1. **PyQt6 GUI Client**: A thin, responsive desktop application providing a modern retro-tactical interface for Battleship.
2. **Automated Test Harness**: An unattended pytest test suite driving the serial communication link to validate server authority, protocol integrity, rule enforcement, and AI behaviors.

---

## Architecture & Thin Client Design

In strict compliance with the project specifications:
* **Input Locking**: When an action is taken (deploying a fleet or clicking a radar cell), user input is immediately locked until the STM32 returns an authoritative response.
* **State Driven by Confirmation**: Grids, health indicators, logs, and transitions are updated exclusively from valid server messages (`HIT`, `MISS`, `SUNK`, `WIN`, `NACK`).
* **Non-Blocking Serial Worker**: [`SerialWorker`](src/client/core/serial_worker.py) runs on a dedicated `QThread`, managing packet transmission, line reception, auto-reconnection, and emitting Qt signals to the UI.

---

## Directory Structure

```text
client/
├── src/client/
│   ├── core/
│   │   ├── coordinates.py     # Coordinate conversion (e.g. A1 <-> (0, 0))
│   │   └── serial_worker.py   # Dedicated serial I/O QThread with auto-port detection
│   ├── ui/
│   │   ├── screens/
│   │   │   ├── startup.py     # Connection status & mode selection (PVP / AI)
│   │   │   ├── setup.py       # Drag-and-drop / click-to-place ship deployment
│   │   │   ├── pass_device.py # Masking screen for hotseat 2-player transitions
│   │   │   ├── gameplay.py    # Dual radar/fleet combat grid with status logs
│   │   │   └── game_over.py   # Win/loss screen revealing secret enemy positions
│   │   ├── board_utils.py     # Grid rendering and stylesheet utilities
│   │   ├── constants.py       # Ship dimensions, colors, and types
│   │   └── main_window.py     # Screen router and protocol response dispatcher
│   └── main.py                # Application entry point
├── tests/
│   ├── conftest.py            # Session fixture with auto port discovery & CLI override
│   ├── helpers.py             # Reusable command transmitters & setup fast-forwards
│   ├── test_01_protocol.py    # Framing, timeouts, overflows, and syntax validation
│   ├── test_02_placement.py   # Geometry, bounds, and overlap rejection tests
│   ├── test_03_shooting.py    # Hit/miss, turn swaps, repeat shots, and win detection
│   └── test_04_ai.py          # AI state flow, counter-attack timing, and 17-cell fleet sweep
├── pyproject.toml             # Project dependencies and tool configuration
└── uv.lock                    # Locked dependency manifest
```

---

## Prerequisites & Installation

### Option A: Using `uv` (Recommended)
[`uv`](https://docs.astral.sh/uv/) is an extremely fast Python package manager:
```bash
# From the repository root or client/ folder:
cd client
uv sync
```

### Option B: Using Standard Python `venv` + `pip`
Requires Python 3.11+:
```bash
cd client
python -m venv .venv

# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -e .
pip install pytest ruff pyright
```

---

## Running the GUI Client

Connect your programmed STM32 board to your PC via USB, then run:

```bash
uv run client
```
*(Or if using standard venv: `python -m client.main`)*

### Quick Development Shortcuts
For rapid gameplay testing without manually clicking through setup grids, pass development fleet flags:
```bash
# Fast-forwards directly to gameplay against the STM32 AI:
uv run client --dev-p1 A1,A5,B1,B4,C1,C3,D1,D3,E1,E2

# Fast-forwards directly to a 2-player hotseat match:
uv run client --dev-p1 A1,A5,B1,B4,C1,C3,D1,D3,E1,E2 --dev-p2 F1,F5,G1,G4,H1,H3,I1,I3,J1,J2
```

---

## Automated Test Harness (pytest)

The test harness runs unattended tests over the active serial port against the physical STM32 microcontroller.

### Running All Tests
```bash
uv run pytest
```

### Serial Port Auto-Discovery & Custom Port Selection
The test fixture in [`tests/conftest.py`](tests/conftest.py) automatically identifies the connected ST-Link or USB-UART virtual COM port.

If multiple serial devices are connected, or if auto-detection needs to be overridden, specify the port explicitly:

```bash
# Using CLI option:
uv run pytest --port COM4

# Or using environment variable:
set STM32_PORT=COM4   # Windows CMD
$env:STM32_PORT="COM4" # PowerShell
export STM32_PORT=/dev/ttyACM0 # Linux/macOS
uv run pytest
```

### Test Suite Coverage

| Test Module | Test Focus | Key Assertions |
| :--- | :--- | :--- |
| **`test_01_protocol.py`** | Framing & Syntax | Baseline handshake (`CONNECT`, `DISCONNECT`), invalid commands (`NACK: BADCMD`), 500ms inter-byte frame timeout recovery, and buffer overflow protection. |
| **`test_02_placement.py`** | Fleet Deployment | Atomic ship placement, reversed endpoints, board boundary edges, diagonal and invalid-length rejections (`NACK: BADCOORDS`), overlapping ships (`NACK: OCCUPIED`), and turn enforcement (`NACK: NOTURN`). |
| **`test_03_shooting.py`** | Combat Rules | Valid hits and misses, turn locking, repeat shots (`NACK: REPEAT`), out-of-bounds shots, ship destruction (`SUNK`), terminal win sequences (`WIN`), and rejection of moves after game over (`NACK: OUT_OF_STATE,GAME_OVER`). |
| **`test_04_ai.py`** | AI Opponent | AI setup transition, rejection of manual P2 placements, automated counter-attack execution, zero retaliation on invalid/repeat shots, and full 100-cell board sweep verifying valid 17-cell fleet generation. |

---

## Code Quality & Linting

```bash
# Lint and check formatting with Ruff:
uv run ruff check .
uv run ruff format --check .

# Type check with Pyright:
uv run pyright
```

