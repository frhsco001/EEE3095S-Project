# STM32 Battleship Embedded Game Server

Authoritative embedded game server firmware targeting the **STM32F051R8T6** ARM Cortex-M0 microcontroller (UCT STM32 Discovery Board). Developed in C using STM32CubeIDE and HAL libraries.

---

### Core States
1. **`STATE_IDLE`**: Default boot and post-disconnect state. Accepts `CONNECT`, `NEW: PVP`, and `NEW: AI`.
2. **`STATE_SETUP`**: Accepts `FLEET: <player>,<coordinates...>`. Evaluates the entire 5-ship fleet atomically on a temporary buffer. If valid, commits the fleet to the board; otherwise returns specific rejection codes (`NACK: BADCOORDS` or `NACK: OCCUPIED`).
3. **`STATE_IN_PROGRESS`**: Active combat phase. Accepts `SHOOT: <player>,<coord>`. Validates target bounds, checks for repeat shots (`NACK: REPEAT`), marks target cell, decrements fleet health, and computes `HIT`, `MISS`, `SUNK`, or `WIN`.
4. **`STATE_GAME_OVER`**: Terminal state. Rejects further shots with `NACK: OUT_OF_STATE,GAME_OVER`. Status LEDs blink at 250ms intervals. Accepts `STATE: 2` (reveals hidden AI fleet to the client), `NEW: ...`, or `DISCONNECT`.

---

## Hardware Interfacing & Pinout

| Peripheral | Port/Pin | Configuration | Purpose |
| :--- | :--- | :--- | :--- |
| **USART1 TX** | `PA9` | AF1 (Push-Pull, High Speed) | 115200 baud, 8 data bits, no parity, 1 stop bit |
| **USART1 RX** | `PA10` | AF1 (Push-Pull, High Speed) | Interrupt-driven single-byte reception (`HAL_UART_Receive_IT`) |
| **Menu Button** | `PA0` | Input with Internal Pull-up | Session reset button with 50ms software debounce |
| **Status Red** | `PB10` | GPIO Output (Low Speed) | Player 2 / AI turn indicator; blinks on AI win |
| **Status Green** | `PB11` | GPIO Output (Low Speed) | Player 1 turn indicator; blinks on P1 win |
| **Health LED 1** | `PB3` | GPIO Output (Low Speed) | Lights up if &ge; 1 ship remains afloat |
| **Health LED 2** | `PB4` | GPIO Output (Low Speed) | Lights up if &ge; 2 ships remain afloat |
| **Health LED 3** | `PB5` | GPIO Output (Low Speed) | Lights up if &ge; 3 ships remain afloat |
| **Health LED 4** | `PB6` | GPIO Output (Low Speed) | Lights up if &ge; 4 ships remain afloat |
| **Health LED 5** | `PB7` | GPIO Output (Low Speed) | Lights up if all 5 ships remain afloat |

---

## Build and Flash Instructions (STM32CubeIDE)

### Prerequisites
* [STM32CubeIDE](https://www.st.com/en/development-tools/stm32cubeide.html) (Version 1.10.0 or later).
* STM32F051 Discovery Board (or compatible STM32F0 board) connected via USB (ST-LINK).

### 1. Import the Project into STM32CubeIDE
1. Launch **STM32CubeIDE**.
2. Go to **File &rarr; Open Projects from File System...** (or **File &rarr; Import... &rarr; General &rarr; Existing Projects into Workspace**).
3. Click **Directory...**, browse to the repository, and select the `server` folder.
4. Ensure the `server` project is checked in the dialog, then click **Finish**.

### 2. Build the Firmware
1. In the **Project Explorer** on the left, click to select the `server` project.
2. Select **Project &rarr; Build Project** from the menu bar (or press `Ctrl+B`).
3. Ensure the build finishes with `0 errors, 0 warnings` in the **Console** panel.

### 3. Flash to the Target Board
1. Connect the STM32 board to your computer via USB (using the ST-Link mini-USB port).
2. Click the **Run** button (green play icon on the toolbar, or press `Ctrl+F11`), or select **Run &rarr; Run**.
3. If prompted with the **Run Configurations** window, keep the default ST-LINK GDB server configuration and click **OK**.
4. The IDE will connect over SWD, flash the firmware into MCU Flash memory, and restart the target.

*(Optional CLI Alternative: If building from the terminal with the Arm GNU Toolchain and Make installed, you can build using `make -f STM32Make.make -j4`).*
