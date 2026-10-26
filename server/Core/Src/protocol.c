#include "protocol.h"

#include <stdint.h>
#include <stdlib.h>
#include <string.h>

static UART_HandleTypeDef* proto_uart = NULL;

char rx_buffer[MAX_FRAME_LEN];
volatile uint8_t rx_index = 0;
volatile uint8_t frame_ready = 0;

void Proto_ProcessByte(uint8_t byte) {
    // Ignore carriage returns if sent by terminal
    if (byte == '\r') {
        return;
    }

    // Check for the newline terminator
    if (byte == '\n') {
        rx_buffer[rx_index] = '\0';  // Null-terminate the string
        frame_ready = 1;
        rx_index = 0;
        return;
    }

    // Store the byte and protect against buffer overflow
    if (rx_index < (MAX_FRAME_LEN - 1)) {
        rx_buffer[rx_index++] = (char)byte;
    } else {
        // Buffer overflow: clear the buffer to recover gracefully
        rx_index = 0;
    }
}

bool Proto_ParseFrame(const char* frame, CommandStruct* cmd) {
    cmd->type = CMD_UNKNOWN;

    // Handle CONNECT
    if (strncmp(frame, "CONNECT", 7) == 0) {
        cmd->type = CMD_CONNECT;
        return true;
    }

    // Handle DISCONNECT
    if (strncmp(frame, "DISCONNECT", 10) == 0) {
        cmd->type = CMD_DISCONNECT;
        return true;
    }

    // Handle STATE
    if (strncmp(frame, "STATE: ", 7) == 0) {
        if (strlen(frame) != 8) return false;

        uint8_t player_id = frame[7] - '0';
        if (player_id < 1 || player_id > 2) return false;

        cmd->type = CMD_STATE;
        cmd->player = player_id;
        return true;
    }

    // Handle NEW (Format: "NEW: PVP" or "NEW: AI")
    if (strncmp(frame, "NEW: ", 5) == 0) {
        if (strncmp(&frame[5], "PVP", 3) == 0) {
            cmd->type = CMD_NEW_PVP;
            return true;
        } else if (strncmp(&frame[5], "AI", 2) == 0) {
            cmd->type = CMD_NEW_AI;
            return true;
        }
        return false;
    }

    // Handle FLEET (Format: "FLEET: <1,2>,<C_S>,<C_E>,<B_S>,<B_E>,<D_S>,<D_E>,<S_S>,<S_E>,<P_S>,<P_E>")
    if (strncmp(frame, "FLEET: ", 7) == 0) {
        int player_id = frame[7] - '0';
        if (player_id < 1 || player_id > 2 || frame[8] != ',') return false;

        cmd->type = CMD_PLACE_FLEET;
        cmd->player = player_id;

        const char* ptr = &frame[9];

        for (int i = 0; i < 5; i++) {
            cmd->fleet[i].x1 = ptr[0] - 'A';
            cmd->fleet[i].y1 = atoi(&ptr[1]) - 1;

            // Advance to next comma
            ptr = strchr(ptr, ',');
            if (ptr == NULL) return false;
            ptr++;  // Skip comma

            cmd->fleet[i].x2 = ptr[0] - 'A';
            cmd->fleet[i].y2 = atoi(&ptr[1]) - 1;

            if (cmd->fleet[i].x1 > 9 || cmd->fleet[i].y1 > 9 ||
                cmd->fleet[i].x2 > 9 || cmd->fleet[i].y2 > 9) {
                return false;
            }

            // Advance to next comma for the next ship (skip on the final iteration)
            if (i < 4) {
                ptr = strchr(ptr, ',');
                if (ptr == NULL) return false;
                ptr++;
            }
        }
        return true;
    }

    // Handle SHOOT (Format: "SHOOT: <1,2>,<A-J><1-10>")
    if (strncmp(frame, "SHOOT: ", 7) == 0) {
        // Minimum valid length is 10: "SHOOT: 1,A1"
        if (strlen(frame) < 10) return false;

        int player_id = frame[7] - '0';
        if (player_id < 1 || player_id > 2 || frame[8] != ',') return false;

        char col_char = frame[9];
        int row_val = atoi(&frame[10]);

        if ((player_id == 1 || player_id == 2) &&
            (col_char >= 'A' && col_char <= 'J') &&
            (row_val >= 1 && row_val <= 10)) {
            cmd->player = player_id;
            cmd->x = col_char - 'A';
            cmd->y = row_val - 1;

            cmd->type = CMD_SHOOT;
            return true;
        }

        return false;
    }

    return false;
}

void Proto_Init(UART_HandleTypeDef* huart) {
    proto_uart = huart;
}

void Proto_SendResponse(const char* msg) {
    if (proto_uart != NULL) {
        HAL_UART_Transmit(proto_uart, (uint8_t*)msg, strlen(msg), HAL_MAX_DELAY);

        uint8_t newline = '\n';
        HAL_UART_Transmit(proto_uart, &newline, 1, HAL_MAX_DELAY);
    }
}

ShipType Proto_CharToShipType(char c) {
    switch (c) {
        case 'C':
            return SHIP_CARRIER;
        case 'B':
            return SHIP_BATTLESHIP;
        case 'D':
            return SHIP_DESTROYER;
        case 'S':
            return SHIP_SUBMARINE;
        case 'P':
            return SHIP_PATROL;
        default:
            return SHIP_NONE;
    }
}

char Proto_ShipTypeToChar(ShipType type) {
    switch (type) {
        case SHIP_CARRIER:
            return 'C';
        case SHIP_BATTLESHIP:
            return 'B';
        case SHIP_DESTROYER:
            return 'D';
        case SHIP_SUBMARINE:
            return 'S';
        case SHIP_PATROL:
            return 'P';
        default:
            return '?';
    }
}
