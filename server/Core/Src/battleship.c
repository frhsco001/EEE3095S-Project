#include "battleship.h"

#include <string.h>

#include "ai.h"
#include "protocol.h"
#include "hardware.h"

const uint8_t SHIP_LENGTHS[SHIP_STATE_COUNT] = {0, 5, 4, 3, 3, 2};

GameState current_state = STATE_IDLE;
GameMode current_mode = MODE_NONE;

uint8_t current_turn = 1;

uint8_t p1_board[BOARD_SIZE][BOARD_SIZE];
ShipState p1_fleet[SHIP_STATE_COUNT];
uint8_t p2_board[BOARD_SIZE][BOARD_SIZE];
ShipState p2_fleet[SHIP_STATE_COUNT];

static bool ai_seeded = false;

static void SeedAIOnce(void) {
    if (ai_seeded) {
        return;
    }

    uint32_t seed = HAL_GetTick() ^ SysTick->VAL;

    AI_Init(seed);
    ai_seeded = true;
}

void Game_ResetSession() {
    current_state = STATE_IDLE;
    current_mode = MODE_NONE;
    current_turn = 1;
}

void Game_ClearBoards() {
    memset(p1_board, 0, sizeof(p1_board));
    memset(p1_fleet, 0, sizeof(p1_fleet));

    memset(p2_board, 0, sizeof(p2_board));
    memset(p2_fleet, 0, sizeof(p2_fleet));

    for (int i = 1; i <= SHIP_COUNT; i++) {
        p1_fleet[i].length = SHIP_LENGTHS[i];
        p2_fleet[i].length = SHIP_LENGTHS[i];
    }
}

/**
 * @brief Helper function to append a formatted coordinate (e.g., "A1" or "J10") to a buffer.
 *
 * @param[out] buf   Pointer to the character buffer being written to.
 * @param[in]  index The current write index in the buffer.
 * @param[in]  x     Column index (0-9).
 * @param[in]  y     Row index (0-9).
 *
 * @return The new buffer index after the coordinate has been appended.
 */
static uint8_t AppendCoord(char* buf, uint8_t index, uint8_t x, uint8_t y) {
    buf[index++] = (char)('A' + x);

    if (y == 9) {
        buf[index++] = '1';
        buf[index++] = '0';
    } else {
        buf[index++] = (char)('1' + y);
    }

    return index;
}

/**
 * @brief Formats and transmits a standard single-cell protocol response over UART.
 *
 * @param[in] prefix  Null-terminated prefix string to prepend (e.g., "HIT: " or "MISS: ").
 * @param[in] player  Target player identifier (1 or 2).
 * @param[in] x       Target column index (0-9).
 * @param[in] y       Target row index (0-9).
 */
static void Proto_SendCellResponse(const char* prefix, uint8_t player, uint8_t x, uint8_t y) {
    char msg[16];
    uint8_t len = 0;

    while (prefix[len] != '\0') {
        msg[len] = prefix[len];
        len++;
    }

    msg[len++] = (char)('0' + player);
    msg[len++] = ',';

    len = AppendCoord(msg, len, x, y);
    msg[len] = '\0';

    Proto_SendResponse(msg);
}

/**
 * @brief Formats and transmits a SUNK or WIN protocol response including ship bounds.
 *
 * @param[in] prefix  Null-terminated prefix string to prepend (e.g., "SUNK: " or "WIN: ").
 * @param[in] player  Target player identifier (1 or 2).
 * @param[in] ship    The ShipType that was destroyed.
 * @param[in] x1      The starting column index of the ship (0-9).
 * @param[in] y1      The starting row index of the ship (0-9).
 * @param[in] x2      The ending column index of the ship (0-9).
 * @param[in] y2      The ending row index of the ship (0-9).
 */
static void Proto_SendShipResponse(const char* prefix, uint8_t player, ShipType ship, uint8_t x1, uint8_t y1, uint8_t x2, uint8_t y2) {
    char msg[32];
    uint8_t len = 0;

    while (prefix[len] != '\0') {
        msg[len] = prefix[len];
        len++;
    }

    msg[len++] = (char)('0' + player);
    msg[len++] = ',';
    msg[len++] = Proto_ShipTypeToChar(ship);
    msg[len++] = ',';

    len = AppendCoord(msg, len, x1, y1);
    msg[len++] = ',';
    len = AppendCoord(msg, len, x2, y2);

    msg[len] = '\0';

    Proto_SendResponse(msg);
}

/**
 * @brief Formats and transmits the full board layout for a given player.
 *
 * Format: STATUS: <Player>,<C_Start>,<C_End>,<B_Start>,<B_End>,...
 */
static void Proto_SendStatusResponse(uint8_t player) {
    char msg[64];
    uint8_t len = 0;
    const char* prefix = "STATUS: ";

    while (prefix[len] != '\0') {
        msg[len] = prefix[len];
        len++;
    }

    msg[len++] = (char)('0' + player);

    ShipState* fleet = (player == 1) ? p1_fleet : p2_fleet;

    for (uint8_t i = 1; i <= SHIP_COUNT; i++) {
        msg[len++] = ',';
        len = AppendCoord(msg, len, fleet[i].x1, fleet[i].y1);
        msg[len++] = ',';
        len = AppendCoord(msg, len, fleet[i].x2, fleet[i].y2);
    }

    msg[len] = '\0';
    Proto_SendResponse(msg);
}

void Game_ProcessCommand(CommandStruct* cmd) {
    if (cmd->type == CMD_CONNECT || cmd->type == CMD_DISCONNECT) {
        Game_ResetSession();
        Proto_SendResponse("OK");
        return;
    }
    switch (current_state) {
        case STATE_IDLE:
            if (cmd->type == CMD_NEW_PVP) {
                Game_ClearBoards();
                current_state = STATE_SETUP;
                current_mode = MODE_PVP;
                Proto_SendResponse("OK: NEW_PVP");
            } else if (cmd->type == CMD_NEW_AI) {
                SeedAIOnce();
                Game_ClearBoards();
                current_state = STATE_SETUP;
                current_mode = MODE_AI;
                Proto_SendResponse("OK: NEW_AI");
            } else {
                Proto_SendResponse("NACK: NOGAME");
            }
            break;

        case STATE_SETUP:
            if (cmd->type != CMD_PLACE_FLEET) {
                Proto_SendResponse("NACK: OUT_OF_STATE,SETUP");
                break;
            }

            if (cmd->player != current_turn) {
                Proto_SendResponse("NACK: NOTURN");
                break;
            }

            ShipType err_ship = SHIP_NONE;
            ShipType err_overlap = SHIP_NONE;
            PlaceResult place_result = Game_Place(current_turn, cmd->fleet, &err_ship, &err_overlap);

            switch (place_result) {
                case PLACE_BAD_COORDS: {
                    char msg[] = "NACK: BADCOORDS,?";
                    msg[16] = Proto_ShipTypeToChar(err_ship);
                    Proto_SendResponse(msg);
                    break;
                }

                case PLACE_OCCUPIED: {
                    char msg[] = "NACK: OCCUPIED,?,?";
                    msg[15] = Proto_ShipTypeToChar(err_ship);
                    msg[17] = Proto_ShipTypeToChar(err_overlap);
                    Proto_SendResponse(msg);
                    break;
                }

                case PLACE_OK:
                    if (current_turn == 1) {
                        if (current_mode == MODE_AI) {
                            AI_PlaceShips();

                            current_turn = 1;
                            current_state = STATE_IN_PROGRESS;
                            Proto_SendResponse("OK: IN_PROGRESS");
                        } else {
                            current_turn = 2;
                            Proto_SendResponse("OK: SETUP_P2");
                        }
                    } else {
                        current_turn = 1;
                        current_state = STATE_IN_PROGRESS;
                        Proto_SendResponse("OK: IN_PROGRESS");
                    }
                    break;
            }

            break;

        case STATE_IN_PROGRESS:
            if (cmd->type != CMD_SHOOT) {
                Proto_SendResponse("NACK: OUT_OF_STATE,IN_PROGRESS");
                break;
            }

            if (cmd->player != current_turn) {
                Proto_SendResponse("NACK: NOTURN");
                break;
            }
            ShipType sunk_ship = SHIP_NONE;

            ShotResult shot_result = Game_Shoot(
                cmd->player,
                cmd->x,
                cmd->y,
                &sunk_ship);
            uint8_t other_player = (current_turn == 1) ? 2 : 1;

            switch (shot_result) {
                case SHOT_BAD_COORDS:
                    Proto_SendResponse("NACK: BADCOORDS");
                    break;

                case SHOT_REPEAT:
                    Proto_SendResponse("NACK: REPEAT");
                    break;

                case SHOT_MISS:
                    Proto_SendCellResponse("MISS: ", other_player, cmd->x, cmd->y);

                    current_turn = current_turn == 1U ? 2U : 1U;
                    break;

                case SHOT_HIT:
                    Proto_SendCellResponse("HIT: ", other_player, cmd->x, cmd->y);

                    current_turn = current_turn == 1U ? 2U : 1U;
                    break;

                case SHOT_SUNK: {
                    ShipState* sunk_state = (other_player == 1) ? &p1_fleet[sunk_ship] : &p2_fleet[sunk_ship];
                    Proto_SendShipResponse(
                        "SUNK: ",
                        other_player,
                        sunk_ship,
                        sunk_state->x1, sunk_state->y1,
                        sunk_state->x2, sunk_state->y2);

                    current_turn = current_turn == 1U ? 2U : 1U;
                    break;
                }

                case SHOT_WIN: {
                    ShipState* sunk_state = (other_player == 1) ? &p1_fleet[sunk_ship] : &p2_fleet[sunk_ship];
                    Proto_SendShipResponse(
                        "WIN: ",
                        current_turn,
                        sunk_ship,
                        sunk_state->x1, sunk_state->y1,
                        sunk_state->x2, sunk_state->y2);

                    current_state = STATE_GAME_OVER;
                    break;
                }
            }
            if (current_mode == MODE_AI && current_turn == 2 && current_state == STATE_IN_PROGRESS) {
                uint8_t ai_x, ai_y;
                AI_GenerateShot(&ai_x, &ai_y);

                sunk_ship = SHIP_NONE;
                shot_result = Game_Shoot(2, ai_x, ai_y, &sunk_ship);

                switch (shot_result) {
                    case SHOT_MISS:
                        Proto_SendCellResponse("MISS: ", 1, ai_x, ai_y);
                        current_turn = 1;
                        break;

                    case SHOT_HIT:
                        Proto_SendCellResponse("HIT: ", 1, ai_x, ai_y);
                        current_turn = 1;
                        break;

                    case SHOT_SUNK: {
                        ShipState* sunk_state = &p1_fleet[sunk_ship];
                        Proto_SendShipResponse(
                            "SUNK: ", 1, sunk_ship,
                            sunk_state->x1, sunk_state->y1,
                            sunk_state->x2, sunk_state->y2);

                        current_turn = 1;
                        break;
                    }

                    case SHOT_WIN: {
                        ShipState* sunk_state = &p1_fleet[sunk_ship];
                        Proto_SendShipResponse(
                            "WIN: ", 2, sunk_ship,
                            sunk_state->x1, sunk_state->y1,
                            sunk_state->x2, sunk_state->y2);

                        current_state = STATE_GAME_OVER;
                        break;
                    }

                    default:
                        break;
                }
            }
            break;
        case STATE_GAME_OVER:
            if (cmd->type == CMD_NEW_PVP) {
                Game_ClearBoards();
                current_turn = 1;
                current_state = STATE_SETUP;
                current_mode = MODE_PVP;
                Proto_SendResponse("OK: NEW_PVP");
            } else if (cmd->type == CMD_NEW_AI) {
                Game_ClearBoards();
                current_turn = 1;
                current_state = STATE_SETUP;
                current_mode = MODE_AI;
                Proto_SendResponse("OK: NEW_AI");
            } else if (cmd->type == CMD_STATE) {
                Proto_SendStatusResponse(cmd->player);
            } else {
                Proto_SendResponse("NACK: OUT_OF_STATE,GAME_OVER");
            }
            break;
    }

    Hardware_Sync();
}

PlaceResult Game_Place(uint8_t player, ShipCoords* fleet, ShipType* err_ship, ShipType* err_overlap) {
    uint8_t temp_board[BOARD_SIZE][BOARD_SIZE] = {0};  // Blank canvas for evaluation

    // Evaluate all 5 ships in memory first
    for (int i = 0; i < SHIP_COUNT; i++) {
        ShipType ship_type = (ShipType)(i + 1);  // 1 to 5 (Carrier to Patrol)
        uint8_t x1 = fleet[i].x1, y1 = fleet[i].y1, x2 = fleet[i].x2, y2 = fleet[i].y2;

        if (err_ship != NULL) {
            *err_ship = ship_type;
        }

        // Orthogonal and bounds check
        if ((x1 != x2 && y1 != y2) ||
            x1 >= BOARD_SIZE || x2 >= BOARD_SIZE ||
            y1 >= BOARD_SIZE || y2 >= BOARD_SIZE) {
            return PLACE_BAD_COORDS;
        }

        uint8_t min_x = (x1 < x2) ? x1 : x2;
        uint8_t max_x = (x1 > x2) ? x1 : x2;
        uint8_t min_y = (y1 < y2) ? y1 : y2;
        uint8_t max_y = (y1 > y2) ? y1 : y2;

        uint8_t length = (max_x - min_x) + (max_y - min_y) + 1;
        if (length != SHIP_LENGTHS[ship_type]) {
            return PLACE_BAD_COORDS;
        }

        // Draw onto temp_board and check for overlapping ships
        for (uint8_t x = min_x; x <= max_x; x++) {
            for (uint8_t y = min_y; y <= max_y; y++) {
                if (temp_board[x][y] != SHIP_NONE) {
                    if (err_overlap != NULL) {
                        *err_overlap = temp_board[x][y];
                    }
                    return PLACE_OCCUPIED;
                }
                temp_board[x][y] = ship_type;
            }
        }
    }

    // The entire fleet is valid. Commit the transaction.
    uint8_t (*board)[BOARD_SIZE] = player == 1 ? p1_board : p2_board;
    ShipState* p_fleet = player == 1 ? p1_fleet : p2_fleet;

    memcpy(board, temp_board, sizeof(temp_board));

    for (int i = 0; i < SHIP_COUNT; i++) {
        uint8_t ship_idx = i + 1;
        p_fleet[ship_idx].is_placed = true;

        p_fleet[ship_idx].x1 = fleet[i].x1;
        p_fleet[ship_idx].y1 = fleet[i].y1;
        p_fleet[ship_idx].x2 = fleet[i].x2;
        p_fleet[ship_idx].y2 = fleet[i].y2;
    }

    return PLACE_OK;
}

ShotResult Game_Shoot(uint8_t player, uint8_t x, uint8_t y, ShipType* sunk_ship) {
    if (x >= BOARD_SIZE || y >= BOARD_SIZE) {
        return SHOT_BAD_COORDS;
    }

    uint8_t target_player = (player == 1) ? 2 : 1;
    uint8_t (*target_board)[BOARD_SIZE] = target_player == 1 ? p1_board : p2_board;
    uint8_t target_cell = target_board[x][y];

    // cell has previously been fired on
    if (target_cell & 0x80) {
        return SHOT_REPEAT;
    }
    target_board[x][y] |= 0x80;      // mark cell as fired on
    if (target_cell == SHIP_NONE) {  // empty, unhit
        return SHOT_MISS;
    }
    // mask out the hit bit to get the ship type
    ShipType hit_ship = target_cell & 0x7F;
    ShipState* fleet = target_player == 1 ? p1_fleet : p2_fleet;
    ShipState* ship = &fleet[hit_ship];

    ship->hits_taken++;

    if (ship->hits_taken < ship->length) {
        return SHOT_HIT;
    }

    if (sunk_ship != NULL) {
        *sunk_ship = hit_ship;
    }

    for (uint8_t i = 1; i < SHIP_STATE_COUNT; i++) {
        if (fleet[i].hits_taken < fleet[i].length) {
            return SHOT_SUNK;
        }
    }
    return SHOT_WIN;
}
