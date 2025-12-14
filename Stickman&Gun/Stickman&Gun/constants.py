WindowWidth = 1400
WindowHeight = 800

GroundY = 520

PlayerWidth = 55
PlayerHeight = 110
PlayerMaxHP = 100
PlayerDamageDelay = 0.7
PlayerStartX = WindowWidth * 0.5 - PlayerWidth * 0.5
PlayerStartY = GroundY - PlayerHeight

SWAP_COOLDOWN = 2.0
BULLET_SPEED = 28.0

ImagePath = "image/"

HUDY = int(WindowHeight * 0.05)

MonsterStats = {
    "slime":     {"hp": 30,  "speed": 1.2, "gold": 10, "size": (70, 44)},
    "zombie":    {"hp": 90,  "speed": 0.9, "gold": 18,  "size": (55, 110)},
    "snail":     {"hp": 135,  "speed": 1.0, "gold": 25,  "size": (130, 115)},
    "snake":     {"hp": 180,  "speed": 1.5, "gold": 70,  "size": (180, 187)},
    "kingslime": {"hp": 900, "speed": 0.8, "gold": 400,  "size": (236, 244)},
    "crawler":    {"hp": 10000,  "speed": 1.3, "gold": 10000,  "size": (209, 135)},
}

WeaponStats = {
    "usp":  {"damage": 10, "fire_delay": 2.86,  "name": "USP",  "cost": 0,
                "ammo": 10,  "reload": 2.5},
    "uzi":     {"damage": 15, "fire_delay": 4.45,  "name": "UZI",  "cost": 200,
                "ammo": 25,  "reload": 1.8},
    "m1897":   {"damage": 18, "fire_delay": 1.25,   "name": "M1897","cost": 500,
                "ammo": 7,   "reload": 2.5, "pellets": 5},
    "m4a1":    {"damage": 30, "fire_delay": 5.56,   "name": "M4A1", "cost": 1000,
                "ammo": 40,  "reload": 2.0},
    "awp":     {"damage": 1000, "fire_delay": 0.75,  "name": "AWP",  "cost": 2500,
                "ammo": 8,   "reload": 4.0}
}