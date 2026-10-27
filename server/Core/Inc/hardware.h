#ifndef HARDWARE_H
#define HARDWARE_H

#include <stdint.h>

#define HEALTH_LED_MASK \
    (HEALTH_LED_1_Pin | HEALTH_LED_2_Pin | HEALTH_LED_3_Pin | HEALTH_LED_4_Pin | HEALTH_LED_5_Pin)

#define STATUS_LED_MASK (STATUS_RED_Pin | STATUS_GREEN_Pin)

#define ALL_LED_MASK (HEALTH_LED_MASK | STATUS_LED_MASK)

/**
 * @brief Configures GPIO pins for the User Button, Status LEDs, and Health Bar LEDs.
 */
void Hardware_Init(void);

/**
 * @brief Polling function to handle Game Over blinking and Button debouncing.
 */
void Hardware_UpdateState(uint32_t now);

/**
 * @brief Synchronizes all LEDs with the current Game State.
 */
void Hardware_Sync(void);

#endif  // HARDWARE_H