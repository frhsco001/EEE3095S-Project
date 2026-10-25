#include "ai.h"

#include <stdbool.h>
#include <stdlib.h>

#include "battleship.h"

void AI_Init(uint32_t seed) {
    srand(seed);
}

void AI_PlaceShips(void) {
    ShipCoords fleet[5];
    uint8_t temp_board[10][10] = {0};

    for (int i = 0; i < 5; i++) {
        uint8_t length = SHIP_LENGTHS[i + 1];
        bool placed = false;

        while (!placed) {
            uint8_t x = rand() % 10;
            uint8_t y = rand() % 10;
            uint8_t dir = rand() % 2;  // 0 = horizontal, 1 = vertical

            uint8_t x2 = (dir == 0) ? x + length - 1 : x;
            uint8_t y2 = (dir == 1) ? y + length - 1 : y;

            if (x2 > 9 || y2 > 9) continue;

            bool overlap = false;
            for (uint8_t cx = x; cx <= x2; cx++) {
                for (uint8_t cy = y; cy <= y2; cy++) {
                    if (temp_board[cx][cy] != 0) {
                        overlap = true;
                    }
                }
            }

            if (!overlap) {
                // Reserve the space on our temp board
                for (uint8_t cx = x; cx <= x2; cx++) {
                    for (uint8_t cy = y; cy <= y2; cy++) {
                        temp_board[cx][cy] = 1;
                    }
                }

                fleet[i].x1 = x;
                fleet[i].y1 = y;
                fleet[i].x2 = x2;
                fleet[i].y2 = y2;
                placed = true;
            }
        }
    }

    // Commit the generated fleet to Player 2's board
    Game_Place(2, fleet, NULL, NULL);
}

void AI_GenerateShot(uint8_t* out_x, uint8_t* out_y) {
    while (1) {
        uint8_t x = rand() % 10;
        uint8_t y = rand() % 10;

        if ((p1_board[x][y] & 0x80) == 0) {
            *out_x = x;
            *out_y = y;
            break;
        }
    }
}