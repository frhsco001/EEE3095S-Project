#include "protocol.h"

#include <stdint.h>
#include <string.h>
#include <stdlib.h> 

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

    // Handle STATE
    if (strncmp(frame, "STATE", 5) == 0) {
        cmd->type = CMD_STATE;
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

    // Handle PLACE (Format: "PLACE: <1,2>,<A-J><1-10>,<A-J><1-10>")
    if (strncmp(frame, "PLACE: ", 7) == 0) {
        // Minimum valid length is 12: "PLACE: 1,A1,B1"
        if (strlen(frame) < 14) return false;

        int player_id = frame[7] - '0';

        if (frame[8] != ',') return false;

        char col1_char = frame[8];
        int row1_val = atoi(&frame[9]);

        // Use the comma position to handle different length positions (X2 vs X10)
        const char* comma_ptr = strchr(frame, ',');
        if (comma_ptr == NULL) return false;

        // Ensure there is enough string left after the comma (minimum "X1")
        if (strlen(comma_ptr) < 3) return false;

        // Parse second coordinate
        char col2_char = comma_ptr[1];
        int row2_val = atoi(&comma_ptr[2]);

        if (col1_char >= 'A' && col1_char <= 'J' &&
            col2_char >= 'A' && col2_char <= 'J' &&
            row1_val >= 1 && row1_val <= 10 &&
            row2_val >= 1 && row2_val <= 10) {
            cmd->player = player_id;
            cmd->x = col1_char - 'A';
            cmd->y = row1_val - 1;
            cmd->x2 = col2_char - 'A';
            cmd->y2 = row2_val - 1;

            cmd->type = CMD_PLACE;
            return true;
        }

        return false;
    }

    // Handle MOVE (Format: "MOVE: <1,2>,<A-J><1-10>")
    if (strncmp(frame, "MOVE: ", 6) == 0) {
        // Minimum valid length is 10: "MOVE: 1,A1"
        if (strlen(frame) < 10) return false;

        int player_id = frame[6] - '0';

        if (frame[7] != ',') return false;

        char col_char = frame[8];
        int row_val = atoi(&frame[9]);

        if ((player_id == 1 || player_id == 2) &&
            (col_char >= 'A' && col_char <= 'J') &&
            (row_val >= 1 && row_val <= 10)) {
            cmd->player = player_id;
            cmd->x = col_char - 'A';
            cmd->y = row_val - 1;

            cmd->type = CMD_MOVE;
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
        HAL_UART_Transmit(proto_uart, (uint8_t*)"\n", 1, HAL_MAX_DELAY);
    }
}
