#ifndef __PROTOCOL_H
#define __PROTOCOL_H

#include <stdbool.h>

#include "battleship.h"
#include "main.h"

#define MAX_FRAME_LEN 64
extern char rx_buffer[MAX_FRAME_LEN];
extern volatile uint8_t rx_index;
extern volatile uint8_t frame_ready;

/**
 * @brief Recognized action categories sent by the client.
 */
typedef enum {
    CMD_UNKNOWN,     /**< Unrecognized or malformed command. */
    CMD_CONNECT,     /**< Handshake request to establish serial link. */
    CMD_DISCONNECT,  /**< Request to terminate link and reset game. */
    CMD_NEW_PVP,     /**< Request to begin a Hotseat Player vs Player match. */
    CMD_NEW_AI,      /**< Request to begin a Player vs AI match (Not implemented). */
    CMD_PLACE_FLEET, /**< Fleet placement command. */
    CMD_SHOOT,       /**< Cell targeting command during gameplay. */
    CMD_STATE        /**< Request for current FSM state (optional debugging). */
} CommandType;

typedef struct ShipCoords {
    uint8_t x1;
    uint8_t y1;
    uint8_t x2;
    uint8_t y2;
} ShipCoords;

/**
 * @brief A decoded protocol message containing all relevant game execution variables.
 */
typedef struct CommandStruct {
    CommandType type;    /**< The type of action requested. */
    uint8_t player;      /**< ID of the player executing the action (1 or 2). */
    uint8_t x;           /**< Target X coordinate (0-9 for A-J). */
    uint8_t y;           /**< Target Y coordinate (0-9). */
    ShipCoords fleet[5]; /**< Array for batch CMD_PLACE_FLEET (Indices 0-4 match ships 1-5). */
} CommandStruct;

/**
 * @brief Associates the protocol handler with a specific hardware UART peripheral.
 *
 * @param[in] huart Pointer to the HAL UART handle to be used for transmitting responses.
 */
void Proto_Init(UART_HandleTypeDef* huart);

/**
 * @brief Ingests a single character from the UART RX interrupt into the internal frame buffer.
 *
 * Flags `frame_ready` when a newline ('\n') is detected or clears the buffer
 * on overflow/timeout conditions.
 *
 * @param[in] byte The raw byte received from the UART data register.
 */
void Proto_ProcessByte(uint8_t byte);

/**
 * @brief Evaluates a raw newline-terminated string and populates a CommandStruct.
 *
 * Applies strict format checking (delimiters, lengths, valid alphanumeric ranges)
 * before extracting integer coordinates and enums.
 *
 * @param[in]  frame Null-terminated string containing the raw client command.
 * @param[out] cmd   Pointer to a CommandStruct to be populated with parsed data.
 *
 * @return True if the command is syntactically valid and parsed successfully; otherwise false.
 */
bool Proto_ParseFrame(const char* frame, CommandStruct* cmd);

/**
 * @brief Transmits a formatted string response back to the client over UART.
 *
 * Automatically appends a newline ('\n') framing character to the transmitted payload.
 *
 * @param[in] msg Null-terminated string to transmit.
 */
void Proto_SendResponse(const char* msg);

/**
 * @brief Converts an ASCII character identifier to its corresponding internal ShipType enum.
 *
 * @param[in] c Uppercase character representing a ship (e.g., 'C' for Carrier).
 *
 * @return Corresponding ShipType enum, or SHIP_NONE if character is unrecognized.
 */
ShipType Proto_CharToShipType(char c);

/**
 * @brief Converts an internal ShipType enum back to its ASCII character identifier.
 *
 * @param[in] type The internal enum of the ship.
 *
 * @return The character representing the ship (e.g., 'C'), or '?' if unrecognized.
 */
char Proto_ShipTypeToChar(ShipType type);

#endif /* __PROTOCOL_H */