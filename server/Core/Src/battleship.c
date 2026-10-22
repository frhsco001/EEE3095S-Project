#include "battleship.h"

#include <string.h>

#include "protocol.h"

const uint8_t SHIP_LENGTHS[6] = {0, 5, 4, 3, 3, 2};

GameState current_state = STATE_IDLE;
GameMode current_mode = MODE_NONE;

uint8_t current_turn = 1;

uint8_t p1_board[10][10];
ShipState p1_fleet[6];
uint8_t p2_board[10][10];
ShipState p2_fleet[6];

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

    for (int i = 1; i <= 5; i++) {
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
 * @brief Scans a player's board to find the start and end coordinates of a specific ship.
 *
 * Iterates through the 10x10 grid to locate all cells occupied by the specified ship type.
 * Since ships are placed orthogonally, the first and last matches during a sequential
 * scan represent the bounding coordinates of the ship.
 *
 * @param[in]  target_player The identifier of the player whose board is being scanned (1 or 2).
 * @param[in]  ship          The specific ShipType enum to search for.
 * @param[out] x1            Pointer to store the starting column coordinate (0-9).
 * @param[out] y1            Pointer to store the starting row coordinate (0-9).
 * @param[out] x2            Pointer to store the ending column coordinate (0-9).
 * @param[out] y2            Pointer to store the ending row coordinate (0-9).
 */
static void FindShipCoords(uint8_t target_player, ShipType ship, uint8_t* x1, uint8_t* y1, uint8_t* x2, uint8_t* y2) {
    uint8_t (*board)[10] = target_player == 1 ? p1_board : p2_board;
    bool found_first = false;

    for (uint8_t x = 0; x < 10; x++) {
        for (uint8_t y = 0; y < 10; y++) {
            if ((board[x][y] & 0x7F) == ship) {
                if (!found_first) {
                    *x1 = x;
                    *y1 = y;
                    *x2 = x;
                    *y2 = y;
                    found_first = true;
                } else {
                    *x2 = x;
                    *y2 = y;
                }
            }
        }
    }
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
                            // AI_PlaceShips();

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
            uint8_t other_player = (cmd->player == 1) ? 2 : 1;

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
                    uint8_t x1, y1, x2, y2;
                    FindShipCoords(other_player, sunk_ship, &x1, &y1, &x2, &y2);

                    Proto_SendShipResponse("SUNK: ", other_player, sunk_ship, x1, y1, x2, y2);

                    current_turn = current_turn == 1U ? 2U : 1U;
                    break;
                }

                case SHOT_WIN: {
                    uint8_t x1, y1, x2, y2;
                    FindShipCoords(other_player, sunk_ship, &x1, &y1, &x2, &y2);

                    Proto_SendShipResponse("WIN: ", cmd->player, sunk_ship, x1, y1, x2, y2);

                    current_state = STATE_GAME_OVER;
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
            } else {
                Proto_SendResponse("NACK: OUT_OF_STATE,GAME_OVER");
            }
            break;
    }
}

PlaceResult Game_Place(uint8_t player, ShipCoords* fleet, ShipType* err_ship, ShipType* err_overlap) {
    uint8_t temp_board[10][10] = {0};  // Blank canvas for evaluation

    // Evaluate all 5 ships in memory first
    for (int i = 0; i < 5; i++) {
        ShipType ship_type = (ShipType)(i + 1);  // 1 to 5 (Carrier to Patrol)
        uint8_t x1 = fleet[i].x1, y1 = fleet[i].y1, x2 = fleet[i].x2, y2 = fleet[i].y2;

        if (err_ship != NULL) {
            *err_ship = ship_type;
        }

        // Orthogonal and bounds check
        if ((x1 != x2 && y1 != y2) || x1 > 9 || x2 > 9 || y1 > 9 || y2 > 9) {
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
    uint8_t (*board)[10] = player == 1 ? p1_board : p2_board;
    ShipState* p_fleet = player == 1 ? p1_fleet : p2_fleet;

    memcpy(board, temp_board, sizeof(temp_board));

    for (int i = 1; i <= 5; i++) {
        p_fleet[i].is_placed = true;
    }

    return PLACE_OK;
}

ShotResult Game_Shoot(uint8_t player, uint8_t x, uint8_t y, ShipType* sunk_ship) {
    if (x > 9 || y > 9) {
        return SHOT_BAD_COORDS;
    }

    uint8_t target_player = (player == 1) ? 2 : 1;
    uint8_t (*target_board)[10] = target_player == 1 ? p1_board : p2_board;
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

    for (uint8_t i = 1; i < 6; i++) {
        if (fleet[i].hits_taken < fleet[i].length) {
            return SHOT_SUNK;
        }
    }
    return SHOT_WIN;
}
