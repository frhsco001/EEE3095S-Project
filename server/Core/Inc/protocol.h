#ifndef __PROTOCOL_H
#define __PROTOCOL_H

#include <stdbool.h>

#include "battleship.h"
#include "main.h"

#define MAX_FRAME_LEN 32
extern char rx_buffer[MAX_FRAME_LEN];
extern volatile uint8_t rx_index;
extern volatile uint8_t frame_ready;

// Valid commands
typedef enum {
    CMD_UNKNOWN,
    CMD_CONNECT,
    CMD_DISCONNECT,
    CMD_NEW_PVP,
    CMD_NEW_AI,  // Not implemented yet
    CMD_PLACE,
    CMD_MOVE,
    CMD_STATE
} CommandType;

typedef struct CommandStruct {
    CommandType type;
    uint8_t player;
    ShipType ship;
    uint8_t x;   // Target X coordinate (0-9 for A-J)
    uint8_t y;   // Target Y coordinate (0-9)
    uint8_t x2;  // Second X coordinate for ship placement
    uint8_t y2;  // Second Y coordinate for ship placement
} CommandStruct;

void Proto_Init(UART_HandleTypeDef* huart);
void Proto_ProcessByte(uint8_t byte);
bool Proto_ParseFrame(const char* frame, CommandStruct* cmd);
void Proto_SendResponse(const char* msg);

ShipType Proto_CharToShipType(char c);
char Proto_ShipTypeToChar(ShipType type);

#endif /* __PROTOCOL_H */