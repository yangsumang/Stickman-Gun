from tkinter import *
from constants import *
import random, time

class Monster:
    def __init__(self, canvas, monster_type, spawn_side="right", big_boss=False):
        
        self.canvas = canvas
        stats = MonsterStats[monster_type]
        self.max_hp = stats["hp"]
        self.hp = stats["hp"]
        self.speed = stats["speed"] * (WindowWidth/800)
        self.gold = stats["gold"]
        self.type = monster_type

        self.width, self.height = stats.get("size")

        extra = random.randint(50, 150)
        x = WindowWidth + self.width if spawn_side=="right" else -self.width
        x += extra * (1 if spawn_side=="right" else -1)
        y = GroundY - self.height

        y_bottom = GroundY
        y_top = y_bottom - self.height
        x1 = x - self.width/2
        x2 = x + self.width/2

        self.sprite_left = None
        self.sprite_right = None
        self.frames_left = []
        self.frames_right = []
        self.anim_idx = 0
        self.anim_delay = 120
        self.last_anim = time.time()

        def frame_cut(gif):
            frames = []
            idx = 0
            while True:
                try:
                    frame = PhotoImage(file=gif, format=f"gif -index {idx}")
                except TclError:
                    break
                frames.append(frame)
                idx += 1
            return frames

        if monster_type == "slime":
            self.frames_left = frame_cut(ImagePath+"SlimeLeft.gif")
            self.frames_right = frame_cut(ImagePath+"SlimeRight.gif")

        elif monster_type == "zombie":
            self.frames_left = frame_cut(ImagePath+"ZombieLeft.gif")
            self.frames_right = frame_cut(ImagePath+"ZombieRight.gif")

        elif monster_type == "snail":
            self.frames_left = frame_cut(ImagePath+"SnailLeft.gif")
            self.frames_right = frame_cut(ImagePath+"SnailRight.gif")

        elif monster_type == "snake":
            self.frames_left = frame_cut(ImagePath+"SnakeLeft.gif")
            self.frames_right = frame_cut(ImagePath+"SnakeRight.gif")

        elif monster_type == "kingslime":
            self.frames_left = frame_cut(ImagePath+"KingslimeLeft.gif")
            self.frames_right = frame_cut(ImagePath+"KingslimeRight.gif")

        elif monster_type == "crawler":
            self.frames_left = frame_cut(ImagePath+"CrawlerLeft.gif")
            self.frames_right = frame_cut(ImagePath+"CrawlerRight.gif")

        self.walk_dir = spawn_side

        if self.walk_dir == "left":
            img = self.frames_left[0]
        else:
            img = self.frames_right[0]
        self.monster = self.canvas.create_image(x, y, image= img, anchor="nw")
        
        bar_y = y_top - 10
        self.hp_bar_bg = self.canvas.create_rectangle(x1, bar_y-3, x2, bar_y+3,
                                                      fill="black", outline="")
        self.hp_bar_fg = self.canvas.create_rectangle(x1, bar_y-3,
                                                      x1 + self.width, bar_y+3,
                                                      fill="red", outline="")

    def update(self, player_x, paused=False):
        if paused or self.hp <= 0: return
        x1,y1,x2,y2 = self.get_bbox()
        center = (x1 + x2) / 2
        if player_x > center:
            direction = 1
        else:
            direction = -1
        self.move_all(direction * self.speed, 0)
        self.walk(direction)

        x1,y1,x2,y2 = self.get_bbox()
        bar_y = y1 - 10
        self.canvas.coords(self.hp_bar_bg, x1, bar_y-3, x2, bar_y+3)
        ratio = max(0, self.hp/self.max_hp)
        self.canvas.coords(self.hp_bar_fg, x1, bar_y-3, x1 + (x2-x1)*ratio, bar_y+3)

    def hit(self, dmg):
        self.hp -= dmg
        return self.hp <= 0

    def get_bbox(self):
        x, y = self.canvas.coords(self.monster)
        return (x, y, x + self.width, y + self.height)

    def walk(self, direction):
        frames = self.frames_right if direction < 0 else self.frames_left
        if not frames:
            return
        now = time.time()
        if now - self.last_anim < self.anim_delay / 1000.0:
            return
        self.last_anim = now
        self.anim_idx = (self.anim_idx + 1) % len(frames)
        self.canvas.itemconfigure(self.monster, image=frames[self.anim_idx])

    def destroy(self):
        self.canvas.delete(self.monster)
        self.canvas.delete(self.hp_bar_bg)
        self.canvas.delete(self.hp_bar_fg)

    def move_all(self, dx, dy):
        self.canvas.move(self.monster, dx, dy)