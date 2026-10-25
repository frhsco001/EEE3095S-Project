#ifndef AI_H
#define AI_H

#include <stdint.h>
#include "protocol.h"

/**
 * @brief Initializes the AI random number generator.
 * @param seed A semi-random value.
 */
void AI_Init(uint32_t seed);

/**
 * @brief Generates a valid 5-ship fleet array and commits it via Game_Place.
 */
void AI_PlaceShips(void);

/**
 * @brief Generates a random set of coordinates that have not yet been fired upon.
 * 
 * @param[out] x Pointer to store the selected X coordinate (0-9)
 * @param[out] y Pointer to store the selected Y coordinate (0-9)
 */
void AI_GenerateShot(uint8_t *x, uint8_t *y);

#endif // AI_H