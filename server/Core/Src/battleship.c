#include "battleship.h"

#include <string.h>

#include "protocol.h"

const uint8_t SHIP_LENGTHS[6] = {0, 5, 4, 3, 3, 2};

GameState current_state = STATE_IDLE;
GameMode current_mode = MODE_NONE;

uint8_t p1_board[10][10];
ShipState p1_fleet[6];
uint8_t p2_board[10][10];
ShipState p2_fleet[6];

void Game_ResetSession() {
    current_state = STATE_IDLE;
    current_mode = MODE_NONE;
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
                current_state = STATE_SETUP_P1;
                current_mode = MODE_PVP;
                Proto_SendResponse("OK: NEW_PVP");
            } else if (cmd->type == CMD_NEW_AI) {
                Game_ClearBoards();
                current_state = STATE_SETUP_P1;
                current_mode = MODE_AI;
                Proto_SendResponse("OK: NEW_AI");
            } else {
                Proto_SendResponse("NACK: NOGAME");
            }
            break;

        case STATE_SETUP_P1:
            if (cmd->type == CMD_PLACE) {
                if (cmd->player != 1) {
                    Proto_SendResponse("NACK: NOTURN");
                } else {
                    bool setup_complete = Game_Place(1, cmd->ship, cmd->x, cmd->y, cmd->x2, cmd->y2);

                    if (setup_complete) {
                        if (current_mode == MODE_AI) {
                            // AI_PlaceShips();
                            current_state = STATE_IN_PROGRESS;
                            Proto_SendResponse("OK: IN_PROGRESS");
                        } else {
                            current_state = STATE_SETUP_P2;
                            Proto_SendResponse("OK: SETUP_P2");
                        }
                    }
                }
            } else {
                Proto_SendResponse("NACK: OUT_OF_STATE,SETUP_P1");
            }
            break;

        case STATE_SETUP_P2:
            if (current_mode != MODE_PVP) {
                Proto_SendResponse("NACK: OUT_OF_STATE,SETUP_P2");
                break;
            }

            if (cmd->type == CMD_PLACE) {
                if (cmd->player != 2) {
                    Proto_SendResponse("NACK: NOTURN");
                } else {
                    bool setup_complete = Game_Place(2, cmd->ship, cmd->x, cmd->y, cmd->x2, cmd->y2);

                    if (setup_complete) {
                        current_state = STATE_IN_PROGRESS;
                        Proto_SendResponse("OK: IN_PROGRESS");
                    }
                }
            } else {
                Proto_SendResponse("NACK: OUT_OF_STATE,SETUP_P2");
            }
            break;
    }
}

bool Game_Place(uint8_t player, ShipType ship_type, uint8_t x1, uint8_t y1, uint8_t x2, uint8_t y2) {
    if (ship_type < SHIP_CARRIER || ship_type > SHIP_PATROL) {
        Proto_SendResponse("NACK: BADCMD");
        return false;
    }

    if ((x1 != x2 && y1 != y2) || x1 > 9 || x2 > 9 || y1 > 9 || y2 > 9) {
        Proto_SendResponse("NACK: BADCOORDS");
        return false;
    }

    ShipState* fleet = player == 1 ? p1_fleet : p2_fleet;
    ShipState* ship = &fleet[ship_type];
    if (ship->is_placed) {
        Proto_SendResponse("NACK: PLACED");
        return false;
    }

    uint8_t (*board)[10] = player == 1 ? p1_board : p2_board;

    // Find bounds manually so no need for <stdlib.h> abs()
    uint8_t min_x = (x1 < x2) ? x1 : x2;
    uint8_t max_x = (x1 > x2) ? x1 : x2;
    uint8_t min_y = (y1 < y2) ? y1 : y2;
    uint8_t max_y = (y1 > y2) ? y1 : y2;

    uint8_t length = (max_x - min_x) + (max_y - min_y) + 1;
    if (length != ship->length) {
        Proto_SendResponse("NACK: BADCOORDS");
        return false;
    }

    for (uint8_t x = min_x; x <= max_x; x++) {
        for (uint8_t y = min_y; y <= max_y; y++) {
            if (board[x][y] != 0) {  // SHIP_NONE
                Proto_SendResponse("NACK: OCCUPIED");
                return false;
            }
        }
    }

    for (uint8_t x = min_x; x <= max_x; x++) {
        for (uint8_t y = min_y; y <= max_y; y++) {
            board[x][y] = ship_type;
        }
    }

    ship->is_placed = true;

    // Check if all ships have been placed
    for (uint8_t i = 1; i < 6; i++) {
        if (!fleet[i].is_placed) {
            Proto_SendResponse("OK: PLACED");
            return false;  // Valid placement, but not all ships placed
        }
    }

    return true;
}
