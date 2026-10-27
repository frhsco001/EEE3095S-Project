# EEE3095S Serial Game Server: Battleship

An authoritative embedded game server running on a **UCT STM32F051 Discovery Board** paired with a thin **Python (PyQt6)** PC GUI client, communicating over a 115200 baud serial UART link.

---

## Project Overview

In this system, the **STM32 is the referee and sole source of truth**. Battleship was selected specifically to test a **client-untrusted architecture with server-side secrecy**:
* **Server Authority**: The microcontroller completely owns both players' boards, validates all ship placements and shots, manages turn transitions, computes win/sink conditions, and keeps secret ship coordinates hidden until match conclusion.
* **Thin Client**: The PC GUI merely forwards player inputs and renders confirmed server responses (`HIT`, `MISS`, `SUNK`, `WIN`). It cannot validate moves or decide hit/miss outcomes.
* **On-Board AI Opponent (Bonus)**: Implements an autonomous probability heatmap and parity hunting algorithm running entirely on the Cortex-M0 MCU.
* **Hardware Feedback**: Features a debounced hardware reset button, turn status LEDs, and a 5-LED dynamic fleet health bar.

---

## Repository Structure

```text
.
├── client/                     # PC Client & Automated Test Suite
│   ├── src/client/             # PyQt6 GUI Application
│   │   ├── core/               # Serial communication worker & coordinate utilities
│   │   └── ui/                 # Screens (Startup, Setup, Pass-and-Play, Gameplay, GameOver)
│   ├── tests/                  # Automated pytest test harness (driving physical STM32)
│   ├── pyproject.toml          # Python project specification and dependencies
│   └── README.md               # Client installation, run, and testing instructions
│
├── server/                     # STM32F051 Embedded Server Firmware
│   ├── Core/
│   │   ├── Inc/                # Headers (protocol.h, battleship.h, hardware.h, ai.h)
│   │   └── Src/                # Source code (protocol.c, battleship.c, hardware.c, ai.c)
│   ├── Drivers/                # STM32F0xx HAL & CMSIS libraries
│   ├── STM32Make.make          # Standalone GCC Makefile for ARM toolchain
│   ├── Makefile                # CubeMX Makefile
│   └── README.md               # Firmware build, flashing, and pinout
│
└── docs/                       # Project Documentation & Deliverables
    └── report/                 # IEEE Conference Format report LaTeX sources
```

---

## Hardware Configuration & Pinout

The server firmware runs on the **STM32F051R8T6** microcontroller:

| Peripheral | Pin | Type | Function / Behavior |
| :--- | :--- | :--- | :--- |
| **USART1 TX** | `PA9` | Alternate Function | Serial transmit to PC (115200 baud, 8N1) |
| **USART1 RX** | `PA10` | Alternate Function | Serial receive from PC (115200 baud, 8N1) |
| **Menu Button** | `PA0` | Input (Pull-up) | Local session reset (50ms debounce; sends `EVENT: RESET`) |
| **Status Red** | `PB10` | Output (Push-Pull) | P2 / AI Turn indicator; blinks on AI win |
| **Status Green** | `PB11` | Output (Push-Pull) | P1 Turn indicator; blinks on P1 win |
| **Health Bar 1–5** | `PB3`–`PB7` | Output (Push-Pull) | Dynamic fleet health bar (LEDs lit = unsunk ships) |

---

## Quick Start Guide

### 1. Build and Flash the STM32 Firmware (STM32CubeIDE)
1. Open **STM32CubeIDE**.
2. Go to **File &rarr; Open Projects from File System...**, select the `server/` folder, and click **Finish**.
3. Select **Project &rarr; Build Project** (`Ctrl+B`).
4. Connect the STM32 board via USB, then click the **Run** button (`Ctrl+F11`) to flash the firmware.
*(See [`server/README.md`](server/README.md) for detailed IDE setup steps and optional CLI instructions).*

### 2. Set Up the PC Client
Install dependencies using [`uv`](https://docs.astral.sh/uv/) (recommended) or standard Python 3.11+:
```bash
cd client
uv sync
```

### 3. Launch the Battleship GUI
Connect the STM32 board via USB, then run:
```bash
uv run client
```
*(The GUI automatically discovers ST-Link / USB-UART virtual COM ports on startup).*

### 4. Run the Automated Test Suite
With the STM32 connected, execute the test harness:
```bash
uv run pytest
```
*(To target a specific serial port, use `uv run pytest --port COM4` or set the `STM32_PORT` environment variable).*

---

## Authors

* **Scott Faurholm** (frhsco001@myuct.ac.za)
* **EEE3095S Embedded Systems II** &mdash; Department of Electrical Engineering, University of Cape Town.
