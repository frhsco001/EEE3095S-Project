#ifndef __BATTLESHIP_H
#define __BATTLESHIP_H

#include <stdint.h>

typedef struct CommandStruct CommandStruct;

typedef enum {
    STATE_IDLE,
    STATE_SETUP,
    STATE_IN_PROGRESS,
    STATE_GAME_OVER
} GameState;

typedef enum {
    MODE_NONE,
    MODE_PVP,
    MODE_AI
} GameMode;

typedef enum {
    SHIP_NONE = 0,
    SHIP_CARRIER = 1,     // 'C' (Length 5)
    SHIP_BATTLESHIP = 2,  // 'B' (Length 4)
    SHIP_DESTROYER = 3,   // 'D' (Length 3)
    SHIP_SUBMARINE = 4,   // 'S' (Length 3)
    SHIP_PATROL = 5       // 'P' (Length 2)
} ShipType;

// Matches ShipType indices
extern const uint8_t SHIP_LENGTHS[6];

typedef struct {
    uint8_t length;
    uint8_t hits_taken;
    bool is_placed;
} ShipState;

extern GameState current_state;
extern GameMode current_mode;
extern uint8_t current_turn;

typedef enum {
    SHOT_BAD_COORDS,
    SHOT_REPEAT,
    SHOT_MISS,
    SHOT_HIT,
    SHOT_SUNK,
    SHOT_WIN
} ShotResult;

typedef enum {
    PLACE_OK,          // Valid placement, more ships remain
    PLACE_COMPLETE,    // Valid placement, all ships placed
    PLACE_BAD_SHIP,
    PLACE_BAD_COORDS,
    PLACE_ALREADY_PLACED,
    PLACE_OCCUPIED
} PlaceResult;

void Game_ResetSession();
void Game_ClearBoard();
void Game_ProcessCommand(CommandStruct* cmd);
PlaceResult Game_Place(uint8_t player, ShipType ship_type, uint8_t x1, uint8_t y1, uint8_t x2, uint8_t y2);
ShotResult Game_Shoot(uint8_t player, uint8_t x, uint8_t y, ShipType *sunk_ship);

#endif /* __BATTLESHIP_H */