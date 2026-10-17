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
 * @brief Formats and transmits a standard cell response over UART without snprintf.
 *
 * @param[in] prefix  Null-terminated prefix string (e.g., "HIT: " or "MISS: ").
 * @param[in] player  Target player identifier (1 or 2).
 * @param[in] x       Column index (0-9).
 * @param[in] y       Row index (0-9).
 */
static void Proto_SendCellResponse(const char* prefix, uint8_t player, uint8_t x, uint8_t y) {
    char msg[16];
    uint8_t len = 0;

    while (prefix[len] != '\0' && len < 8) {
        msg[len] = prefix[len];
        len++;
    }

    msg[len++] = (char)('0' + player);
    msg[len++] = ',';

    msg[len++] = (char)('A' + x);

    if (y == 9) {
        msg[len++] = '1';
        msg[len++] = '0';
    } else {
        msg[len++] = (char)('1' + y);
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
                Game_ClearBoards();
                current_state = STATE_SETUP;
                current_mode = MODE_AI;
                Proto_SendResponse("OK: NEW_AI");
            } else {
                Proto_SendResponse("NACK: NOGAME");
            }
            break;

        case STATE_SETUP:
            if (cmd->type != CMD_PLACE) {
                Proto_SendResponse("NACK: OUT_OF_STATE,SETUP");
                break;
            }

            if (cmd->player != current_turn) {
                Proto_SendResponse("NACK: NOTURN");
                break;
            }
            PlaceResult place_result = Game_Place(current_turn, cmd->ship, cmd->x, cmd->y, cmd->x2, cmd->y2);

            switch (place_result) {
                case PLACE_BAD_SHIP:
                    Proto_SendResponse("NACK: BADCMD");
                    break;

                case PLACE_BAD_COORDS:
                    Proto_SendResponse("NACK: BADCOORDS");
                    break;

                case PLACE_ALREADY_PLACED:
                    Proto_SendResponse("NACK: PLACED");
                    break;

                case PLACE_OCCUPIED:
                    Proto_SendResponse("NACK: OCCUPIED");
                    break;

                case PLACE_OK:
                    Proto_SendResponse("OK: PLACED");
                    break;

                case PLACE_COMPLETE:
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
                    char msg[] = "SUNK: X,?";

                    msg[6] = (char)('0' + other_player);
                    msg[8] = Proto_ShipTypeToChar(sunk_ship);

                    Proto_SendResponse(msg);

                    current_turn = current_turn == 1U ? 2U : 1U;
                    break;
                }

                case SHOT_WIN: {
                    char msg[] = "WIN: X,?";
                    msg[5] = (char)('0' + cmd->player);
                    msg[7] = Proto_ShipTypeToChar(sunk_ship);

                    Proto_SendResponse(msg);

                    current_state = STATE_GAME_OVER;
                    break;
                }
            }
            break;
    }
}

PlaceResult Game_Place(uint8_t player, ShipType ship_type, uint8_t x1, uint8_t y1, uint8_t x2, uint8_t y2) {
    if (ship_type < SHIP_CARRIER || ship_type > SHIP_PATROL) {
        return PLACE_BAD_SHIP;
    }

    // make sure ship is completely horizontal or vertical
    if ((x1 != x2 && y1 != y2) || x1 > 9 || x2 > 9 || y1 > 9 || y2 > 9) {
        return PLACE_BAD_COORDS;
    }

    ShipState* fleet = player == 1 ? p1_fleet : p2_fleet;
    ShipState* ship = &fleet[ship_type];
    if (ship->is_placed) {
        return PLACE_ALREADY_PLACED;
    }

    uint8_t (*board)[10] = player == 1 ? p1_board : p2_board;

    // Find bounds manually so no need for <stdlib.h> abs()
    uint8_t min_x = (x1 < x2) ? x1 : x2;
    uint8_t max_x = (x1 > x2) ? x1 : x2;
    uint8_t min_y = (y1 < y2) ? y1 : y2;
    uint8_t max_y = (y1 > y2) ? y1 : y2;

    // make the coordinates correspond to the correct ship length
    uint8_t length = (max_x - min_x) + (max_y - min_y) + 1;
    if (length != ship->length) {
        return PLACE_BAD_COORDS;
    }

    // detect collisions
    for (uint8_t x = min_x; x <= max_x; x++) {
        for (uint8_t y = min_y; y <= max_y; y++) {
            if (board[x][y] != SHIP_NONE) {
                return PLACE_OCCUPIED;
            }
        }
    }

    // place ship on the board
    for (uint8_t x = min_x; x <= max_x; x++) {
        for (uint8_t y = min_y; y <= max_y; y++) {
            board[x][y] = ship_type;
        }
    }

    ship->is_placed = true;

    // Check if all ships have been placed
    for (uint8_t i = 1; i < 6; i++) {
        if (!fleet[i].is_placed) {
            return PLACE_OK;
        }
    }

    return PLACE_COMPLETE;
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
