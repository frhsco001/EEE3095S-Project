#include "ai.h"

#include <stdbool.h>
#include <stdlib.h>

#include "battleship.h"

void AI_Init(uint32_t seed) {
    // Seed the RNG so ship placement and shot selection are reproducible
    srand(seed);
}

void AI_PlaceShips(void) {
    ShipCoords fleet[SHIP_COUNT];
    uint8_t temp_board[BOARD_SIZE][BOARD_SIZE] = {0};

    for (int i = 0; i < SHIP_COUNT; i++) {
        uint8_t length = SHIP_LENGTHS[i + 1];
        bool placed = false;

        while (!placed) {
            uint8_t x = rand() % BOARD_SIZE;
            uint8_t y = rand() % BOARD_SIZE;
            uint8_t dir = rand() % 2;  // 0 = horizontal, 1 = vertical

            // Calculate the ship's end coordinate
            uint8_t x2 = (dir == 0) ? x + length - 1 : x;
            uint8_t y2 = (dir == 1) ? y + length - 1 : y;

            if (x2 >= BOARD_SIZE || y2 >= BOARD_SIZE) continue;

            bool overlap = false;

            for (uint8_t cx = x; cx <= x2; cx++) {
                for (uint8_t cy = y; cy <= y2; cy++) {
                    if (temp_board[cx][cy] != 0) overlap = true;
                }
            }

            if (!overlap) {
                // Mark the cells as occupied so later ships cannot overlap
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
    uint16_t heatmap[BOARD_SIZE][BOARD_SIZE] = {0};
    bool has_active_hits = false;
    uint8_t min_alive_len = SHIP_LENGTHS[SHIP_CARRIER];

    // Find the shortest ship that has not yet been sunk. Used for dynamic parity
    for (uint8_t s = 1; s <= SHIP_COUNT; s++) {
        if (p1_fleet[s].hits_taken < p1_fleet[s].length) {
            if (p1_fleet[s].length < min_alive_len) {
                min_alive_len = SHIP_LENGTHS[s];
            }
        }
    }

    // See if we are currently tracking an unsunk hit (target mode)
    for (uint8_t x = 0; x < BOARD_SIZE; x++) {
        for (uint8_t y = 0; y < BOARD_SIZE; y++) {
            if (p1_board[x][y] & 0x80) {
                uint8_t ship = p1_board[x][y] & 0x7F;

                if (ship != SHIP_NONE &&
                    p1_fleet[ship].hits_taken < p1_fleet[ship].length) {
                    has_active_hits = true;
                }
            }
        }
    }

    // Evaluate every legal placement for every unsunk ship and build
    // a probability heatmap from the resulting overlaps
    for (uint8_t s = 1; s <= SHIP_COUNT; s++) {
        if (p1_fleet[s].hits_taken >= p1_fleet[s].length) continue;

        uint8_t len = SHIP_LENGTHS[s];

        // Evaluate horizontal placements
        for (uint8_t y = 0; y < BOARD_SIZE; y++) {
            for (uint8_t x = 0; x <= BOARD_SIZE - len; x++) {
                bool valid = true;
                uint16_t placement_score = 1;

                for (uint8_t i = 0; i < len; i++) {
                    uint8_t cx = x + i;

                    if (p1_board[cx][y] & 0x80) {
                        uint8_t ship = p1_board[cx][y] & 0x7F;

                        if (ship == SHIP_NONE) {
                            valid = false;
                            break;
                        } else if (p1_fleet[ship].hits_taken >= p1_fleet[ship].length) {
                            valid = false;
                            break;
                        } else {
                            placement_score += 50;
                        }
                    }
                }

                if (valid) {
                    // Add this placement's score to every unfired cell it covers
                    for (uint8_t i = 0; i < len; i++) {
                        if (!(p1_board[x + i][y] & 0x80))
                            heatmap[x + i][y] += placement_score;
                    }
                }
            }
        }

        // Evaluate vertical placements
        for (uint8_t x = 0; x < BOARD_SIZE; x++) {
            for (uint8_t y = 0; y <= BOARD_SIZE - len; y++) {
                bool valid = true;
                uint16_t placement_score = 1;

                for (uint8_t i = 0; i < len; i++) {
                    uint8_t cy = y + i;

                    if (p1_board[x][cy] & 0x80) {
                        uint8_t ship = p1_board[x][cy] & 0x7F;

                        if (ship == SHIP_NONE) {
                            valid = false;
                            break;
                        } else if (p1_fleet[ship].hits_taken >=
                                   p1_fleet[ship].length) {
                            valid = false;
                            break;
                        } else {
                            placement_score += 50;
                        }
                    }
                }

                if (valid) {
                    for (uint8_t i = 0; i < len; i++) {
                        if (!(p1_board[x][y + i] & 0x80))
                            heatmap[x][y + i] += placement_score;
                    }
                }
            }
        }
    }

    // Find the highest-scoring candidate cells
    // Hunting mode uses a parity filter to avoid wasting shots
    uint16_t max_heat = 0;
    uint8_t best_count = 0;

    for (uint8_t x = 0; x < BOARD_SIZE; x++) {
        for (uint8_t y = 0; y < BOARD_SIZE; y++) {
            if (p1_board[x][y] & 0x80) continue;

            if (!has_active_hits && ((x + y) % min_alive_len != 0)) {
                heatmap[x][y] = 0;
            }

            if (heatmap[x][y] > max_heat) {
                max_heat = heatmap[x][y];
                best_count = 1;
            } else if (heatmap[x][y] == max_heat) {
                best_count++;
            }
        }
    }

    // If every score ended up at zero, fall back to any unfired cell
    if (best_count == 0) {
        for (uint8_t x = 0; x < BOARD_SIZE; x++) {
            for (uint8_t y = 0; y < BOARD_SIZE; y++) {
                if (!(p1_board[x][y] & 0x80)) best_count++;
            }
        }
    }

    // Out of the highest scorers, choose randomly
    uint8_t choice = rand() % best_count;
    uint8_t current = 0;

    for (uint8_t x = 0; x < BOARD_SIZE; x++) {
        for (uint8_t y = 0; y < BOARD_SIZE; y++) {
            if (p1_board[x][y] & 0x80) continue;
            if (max_heat > 0 && heatmap[x][y] != max_heat) continue;

            if (current == choice) {
                *out_x = x;
                *out_y = y;
                return;
            }

            current++;
        }
    }
}
