#include "hardware.h"

#include <stdbool.h>

#include "battleship.h"
#include "protocol.h"
#include "stm32f0xx_hal.h"

#define BUTTON_DEBOUNCE_MS 50
#define GAME_OVER_BLINK_MS 250

static bool is_game_over = false;
static uint32_t last_blink_time = 0;
static bool blink_state = false;

static uint32_t last_btn_time = 0;
static uint8_t last_btn_state = GPIO_PIN_SET;

void Hardware_Init(void) {
    // Turn all off initially
    HAL_GPIO_WritePin(GPIOB, ALL_LED_MASK, GPIO_PIN_RESET);
    last_btn_state = HAL_GPIO_ReadPin(MENU_BUTTON_GPIO_Port, MENU_BUTTON_Pin);
}

void Hardware_UpdateState(uint32_t now) {
    if (is_game_over) {
        if (now - last_blink_time >= GAME_OVER_BLINK_MS) {
            blink_state = !blink_state;

            uint16_t blink_mask = STATUS_LED_MASK;
            if (current_mode == MODE_AI) {
                // Green (PB11) for P1 Win, Red (PB10) for AI Win
                blink_mask = (current_turn == 1) ? STATUS_GREEN_Pin : STATUS_RED_Pin;
            }

            if (blink_state) {
                HAL_GPIO_WritePin(GPIOB, blink_mask, GPIO_PIN_SET);
            } else {
                HAL_GPIO_WritePin(GPIOB, STATUS_LED_MASK, GPIO_PIN_RESET);
            }
            last_blink_time = now;
        }
    }

    uint8_t btn_state = HAL_GPIO_ReadPin(MENU_BUTTON_GPIO_Port, MENU_BUTTON_Pin);

    // Check for a falling edge (button press)
    if (btn_state == GPIO_PIN_RESET && last_btn_state == GPIO_PIN_SET) {
        if (now - last_btn_time >= BUTTON_DEBOUNCE_MS) {
            Game_ResetSession();
            Proto_SendResponse("EVENT: RESET");
            Hardware_Sync();
            last_btn_time = now;
        }
    }
    last_btn_state = btn_state;
}

void Hardware_Sync(void) {
    if (current_state == STATE_IDLE || current_state == STATE_SETUP) {
        is_game_over = false;

        // Turn off all status and health LEDs
        HAL_GPIO_WritePin(GPIOB, ALL_LED_MASK, GPIO_PIN_RESET);
    } else if (current_state == STATE_IN_PROGRESS) {
        is_game_over = false;

        // Turn LED: Green (PB11) for P1, Red (PB10) for P2/AI
        if (current_turn == 1) {
            HAL_GPIO_WritePin(GPIOB, STATUS_GREEN_Pin, GPIO_PIN_SET);
            HAL_GPIO_WritePin(GPIOB, STATUS_RED_Pin, GPIO_PIN_RESET);
        } else {
            HAL_GPIO_WritePin(GPIOB, STATUS_RED_Pin, GPIO_PIN_SET);
            HAL_GPIO_WritePin(GPIOB, STATUS_GREEN_Pin, GPIO_PIN_RESET);
        }

        // Health Bar: Show active player's health in PVP, or always P1 in AI mode
        uint8_t alive = 0;
        ShipState* fleet = (current_mode == MODE_AI || current_turn == 1) ? p1_fleet : p2_fleet;

        for (uint8_t i = 1; i <= SHIP_COUNT; i++) {
            if (fleet[i].hits_taken < fleet[i].length) {
                alive++;
            }
        }

        HAL_GPIO_WritePin(HEALTH_LED_1_GPIO_Port, HEALTH_LED_1_Pin, (alive >= 1) ? GPIO_PIN_SET : GPIO_PIN_RESET);
        HAL_GPIO_WritePin(HEALTH_LED_2_GPIO_Port, HEALTH_LED_2_Pin, (alive >= 2) ? GPIO_PIN_SET : GPIO_PIN_RESET);
        HAL_GPIO_WritePin(HEALTH_LED_3_GPIO_Port, HEALTH_LED_3_Pin, (alive >= 3) ? GPIO_PIN_SET : GPIO_PIN_RESET);
        HAL_GPIO_WritePin(HEALTH_LED_4_GPIO_Port, HEALTH_LED_4_Pin, (alive >= 4) ? GPIO_PIN_SET : GPIO_PIN_RESET);
        HAL_GPIO_WritePin(HEALTH_LED_5_GPIO_Port, HEALTH_LED_5_Pin, (alive >= 5) ? GPIO_PIN_SET : GPIO_PIN_RESET);
    } else if (current_state == STATE_GAME_OVER) {
        if (!is_game_over) {
            is_game_over = true;
            last_blink_time = HAL_GetTick();
            blink_state = true;

            uint16_t blink_mask = STATUS_LED_MASK;
            if (current_mode == MODE_AI) {
                blink_mask = (current_turn == 1) ? STATUS_GREEN_Pin : STATUS_RED_Pin;
            }

            HAL_GPIO_WritePin(GPIOB, STATUS_LED_MASK, GPIO_PIN_RESET);
            HAL_GPIO_WritePin(GPIOB, blink_mask, GPIO_PIN_SET);
        }
    }
}
