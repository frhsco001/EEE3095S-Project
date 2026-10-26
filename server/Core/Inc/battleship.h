#ifndef __BATTLESHIP_H
#define __BATTLESHIP_H

#include <stdbool.h>
#include <stdint.h>

/**
 * @brief Forward declaration of the command structure used by the parser.
 */
typedef struct CommandStruct CommandStruct;

typedef struct ShipCoords ShipCoords;

/**
 * @brief Represents the primary states of the game's state machine.
 */
typedef enum {
    STATE_IDLE,        /**< Waiting for a client connection and game initialization. */
    STATE_SETUP,       /**< Players are actively placing their fleets. */
    STATE_IN_PROGRESS, /**< Active gameplay phase; players are exchanging shots. */
    STATE_GAME_OVER    /**< Game concluded; waiting for reset or new game command. */
} GameState;

/**
 * @brief Represents the active game mode.
 */
typedef enum {
    MODE_NONE, /**< No game mode currently selected. */
    MODE_PVP,  /**< Local Hotseat Player vs. Player. */
    MODE_AI    /**< Player vs. Microcontroller AI (Future implementation). */
} GameMode;

/**
 * @brief Identifier for each class of ship in a standard Battleship fleet.
 */
typedef enum {
    SHIP_NONE = 0,       /**< Represents an empty cell. */
    SHIP_CARRIER = 1,    /**< 'C' (Length 5) */
    SHIP_BATTLESHIP = 2, /**< 'B' (Length 4) */
    SHIP_DESTROYER = 3,  /**< 'D' (Length 3) */
    SHIP_SUBMARINE = 4,  /**< 'S' (Length 3) */
    SHIP_PATROL = 5      /**< 'P' (Length 2) */
} ShipType;

extern const uint8_t SHIP_LENGTHS[6];
extern uint8_t p1_board[10][10];
extern uint8_t p2_board[10][10];

/**
 * @brief Tracks the runtime status of an individual ship during the game.
 */
typedef struct {
    uint8_t length;     /**< Total size of the ship in cells. */
    uint8_t hits_taken; /**< Number of times this ship has been hit. */
    bool is_placed;     /**< True if the ship has been successfully locked onto the board. */
    uint8_t x1, y1;     /**< Starting x and y coordinates. */
    uint8_t x2, y2;     /**< Ending x and y coordinates. */
} ShipState;

extern GameState current_state;
extern GameMode current_mode;
extern uint8_t current_turn;

/**
 * @brief Return codes for a shooting action during active gameplay.
 */
typedef enum {
    SHOT_BAD_COORDS, /**< Target coordinates are out of bounds. */
    SHOT_REPEAT,     /**< Target cell has already been fired upon. */
    SHOT_MISS,       /**< Shot landed on an empty cell (water). */
    SHOT_HIT,        /**< Shot hit a ship, but it remains afloat. */
    SHOT_SUNK,       /**< Shot hit and destroyed a ship. */
    SHOT_WIN         /**< Shot destroyed the final remaining ship in the fleet. */
} ShotResult;

/**
 * @brief Return codes for an attempted ship placement during setup.
 */
typedef enum {
    PLACE_OK,         /**< Fleet placed successfully. */
    PLACE_BAD_COORDS, /**< Coordinates are out of bounds, diagonal, or do not match ship length. */
    PLACE_OCCUPIED    /**< One or more target cells are already occupied by another ship. */
} PlaceResult;

/**
 * @brief Hard resets the game state machine, mode, and turn trackers to default.
 */
void Game_ResetSession();

/**
 * @brief Zeroes out both players' boards and resets their fleet tracking structures.
 */
void Game_ClearBoard();

/**
 * @brief Main execution handler for incoming protocol commands.
 *
 * Dispatches the parsed command to the appropriate logic blocks depending on the
 * current state of the FSM (Idle, Setup, or In Progress).
 *
 * @param[in] cmd Pointer to a fully populated CommandStruct from the parser.
 */
void Game_ProcessCommand(CommandStruct* cmd);

/**
 * @brief Validates and executes a fleet placement request on the active board.
 *
 * @param[in] player            The player attempting the placement (1 or 2).
 * @param[in] ship_placements   Coordinates of each of the 5 ships
 *
 * @return Evaluation status of the placement attempt.
 */
PlaceResult Game_Place(uint8_t player, ShipCoords* ship_placements, ShipType* err_ship, ShipType* err_overlap);

/**
 * @brief Processes a single shot on a target player's board.
 *
 * Evaluates coordinates against the opponent's grid, marks the cell as fired upon,
 * increments damage on targeted ships, and detects sinking or fleet elimination.
 *
 * @param[in]  player     ID of the shooting player (1 or 2).
 * @param[in]  x          Target column coordinate (0-9).
 * @param[in]  y          Target row coordinate (0-9).
 * @param[out] sunk_ship  Pointer to store the sunken ship type if the shot results
 *                        in SHOT_SUNK or SHOT_WIN. Pass NULL if this data is not needed.
 *
 * @return Evaluation status of the shot attempt.
 */
ShotResult Game_Shoot(uint8_t player, uint8_t x, uint8_t y, ShipType* sunk_ship);

#endif /* __BATTLESHIP_H */