from constants import *
from tkinter import *
import math
from PIL import Image, ImageTk

class Player:
    def __init__(self, canvas):
        self.canvas = canvas

        self.x = PlayerStartX
        self.y = PlayerStartY
        self.vy = 0
        self.on_ground = True
        self.speed = 0.01 * WindowWidth

        self.max_hp = 100
        self.hp = 100
        self.last_hit_time = 0


        self.width = PlayerWidth
        self.height = PlayerHeight

        self.weapon_name = "usp"
        self.last_shot_time = 0

        self.hitbox = self.canvas.create_rectangle(
            self.x, self.y, self.x+self.width, self.y+self.height,
            fill="", outline=""
        )

        self.legs_stop_img = PhotoImage(file=ImagePath+"PlayerLegs.png")
        self.walk_frames_left = self.frame_cut(ImagePath+"PlayerLeftWalking.gif")
        self.walk_frames_right = self.frame_cut(ImagePath+"PlayerRightWalking.gif")

        self.legs_jump_left = PhotoImage(file=ImagePath+"PlayerLeftJump.png")
        self.legs_jump_right = PhotoImage(file=ImagePath+"PlayerRightJump.png")
        self.walk_frame_idx = 0
        self.walk_anim_after = None
        self.is_walking = False
        self.walk_dir = "left"
        self.recoil_after_id = None
        self.hand_recoil_after = None
        self.hand_angle = 0
        self.hand_base_angle = 0
        self.hand_current_img = None
        self.muzzle_dir = (1, 0)
        self.current_legs_img = self.legs_stop_img

        self.body_left_img = PhotoImage(file=ImagePath+"PlayerLeftBody.png")
        self.body_right_img = PhotoImage(file=ImagePath+"PlayerRightBody.png")
        self.body_img = self.body_left_img

        self.legs_id = self.canvas.create_image(self.x, self.y, image=self.current_legs_img, anchor="nw")
        self.body_id = self.canvas.create_image(self.x, self.y, image=self.body_img, anchor="nw")

        def load_hand_img(gun):
            l_pil = Image.open(ImagePath+f"{gun}Lefthand.png").convert("RGBA")
            r_pil = Image.open(ImagePath+f"{gun}Righthand.png").convert("RGBA")
            return {"left_pil" : l_pil, "right_pil" : r_pil}

        self.hand_assets = {
            "usp": load_hand_img("USP"),
            "uzi": load_hand_img("UZI"),
            "m1897": load_hand_img("M1897"),
            "m4a1" : load_hand_img("M4A1"),
            "awp" : load_hand_img("AWP")
        }
        self.hand_left_img = self.return_hand_img("left", 0)
        self.hand_right_img = self.return_hand_img("right", 0)
        self.hand_dir = "left"
        self.hand_current_img = self.hand_left_img
        self.hand_id = self.canvas.create_image(self.x, self.y, image=self.hand_left_img, anchor="nw")

        bx1, by1, bx2, by2 = self.hitbox_bbox()
        self.bar_offset_y = -4
        bar_y = by1 - 10 + self.bar_offset_y
        self.bar_pad = 6
        self.bar_shift = -3
        self.hp_bar_bg = self.canvas.create_rectangle(
            bx1 - self.bar_pad + self.bar_shift, bar_y - 5, bx2 + self.bar_pad + self.bar_shift, bar_y + 5, fill="black", outline=""
        )
        self.hp_bar_fg = self.canvas.create_rectangle(
            bx1 - self.bar_pad + self.bar_shift, bar_y - 5, bx2 + self.bar_pad + self.bar_shift, bar_y + 5, fill="lime", outline=""
        )

    def get_weapon_stats(self):
        from constants import WeaponStats
        return WeaponStats[self.weapon_name]

    def update(self, keys, paused=False):
        if paused:
            return
        dx = 0
        if 65 in keys or 37 in keys: dx -= self.speed
        if 68 in keys or 39 in keys: dx += self.speed

        moving = (dx != 0 and self.on_ground)
        if moving:
            new_dir = "left" if dx < 0 else "right"
            if (not self.is_walking) or (new_dir != self.walk_dir):
                self.walk_dir = new_dir
                self.is_walking = True
                self.start_walk_anim()
        elif self.is_walking:
            self.is_walking = False
            self.stop_walk_anim()

        self.move_all(dx, 0)

        x1,y1,x2,y2 = self.canvas.coords(self.hitbox)
        self.x, self.y = x1, y1

        if (87 in keys or 38 in keys or 32 in keys) and self.on_ground:
            self.vy = -24
            self.on_ground = False
            self.set_jump_legs()

        self.vy += 2
        self.move_all(0, self.vy)
        x1,y1,x2,y2 = self.canvas.coords(self.hitbox)

        if y2 >= GroundY:
            self.move_all(0, GroundY - y2)
            self.vy = 0
            self.on_ground = True
            if not self.is_walking:
                self.stop_walk_anim()

        if x1 < 0: self.move_all(-x1, 0)
        elif x2 > WindowWidth: self.move_all(WindowWidth - x2, 0)

        self.update_hand()

    def get_center(self):
        x1,y1,x2,y2 = self.canvas.coords(self.hitbox)
        return ((x1+x2)/2, (y1+y2)/2)

    def get_muzzle_position(self):
        hx, hy = self.canvas.coords(self.hand_id)
        img = self.hand_current_img or self.return_hand_img(self.hand_dir, self.hand_angle)
        if img:
            w, h = img.width(), img.height()
            cx, cy = hx + w * 0.5, hy + h * 0.5
            vx, vy = self.muzzle_dir
            forward_factor = 0.45
            if self.weapon_name == "uzi":
                forward_factor = 0.6
            forward = max(w, h) * forward_factor
            muzzle_x = cx + vx * forward
            muzzle_y = cy - vy * forward - 3
            return (muzzle_x, muzzle_y)

    def set_hand_aim(self, tx, ty):
        if not self.hand_id:
            return
        px, py = self.get_muzzle_position()
        dx = tx - px
        dy = ty - py
        if dx == 0 and dy == 0:
            return
        angle_deg = math.degrees(math.atan2(-dy, dx))
        if self.hand_dir == "left":
            angle_deg += 180
        self.hand_base_angle = angle_deg
        self.hand_angle = angle_deg
        dist = (dx*dx + dy*dy) ** 0.5
        if dist != 0:
            self.muzzle_dir = (dx/dist, dy/dist)
        img = self.return_hand_img(self.hand_dir, self.hand_angle)
        if img and self.hand_id:
            self.hand_current_img = img
            self.canvas.itemconfigure(self.hand_id, image=img)

    def set_body_direction(self, direction: str):
        img = self.body_left_img if direction == "left" else self.body_right_img
        if img is not self.body_img:
            self.body_img = img
            if self.body_id:
                self.canvas.itemconfigure(self.body_id, image=self.body_img)
        self.hand_dir = direction

    def update_hp_bar(self, hp, max_hp):
        x1, y1, x2, y2 = self.hitbox_bbox()
        bar_y = y1 - 10 + self.bar_offset_y
        bar_pad = self.bar_pad
        self.canvas.coords(self.hp_bar_bg, x1 - bar_pad + self.bar_shift, bar_y - 5, x2 + bar_pad + self.bar_shift, bar_y + 5)
        ratio = max(0, min(1, hp / max_hp))
        self.canvas.coords(self.hp_bar_fg, x1 - bar_pad + self.bar_shift, bar_y - 5, x1 + (x2 - x1 + 2 * bar_pad) * ratio + self.bar_shift, bar_y + 5)

    def move_all(self, dx, dy):
        self.canvas.move(self.hitbox, dx, dy)
        self.canvas.move(self.legs_id, dx, dy)
        if self.body_id:
            self.canvas.move(self.body_id, dx, dy)
        if self.hand_id:
            self.canvas.move(self.hand_id, dx, dy)
        self.canvas.move(self.hp_bar_bg, dx, dy)
        self.canvas.move(self.hp_bar_fg, dx, dy)

    def apply_recoil(self, direction: str):
        base = self.hand_base_angle
        angle = base + (30 if direction == "right" else -30)
        body_offset = -4 if direction == "right" else 4

        if self.hand_recoil_after:
            self.canvas.after_cancel(self.hand_recoil_after)
            self.hand_recoil_after = None
        self.hand_angle = angle
        img = self.return_hand_img(self.hand_dir, self.hand_angle)
        if img and self.hand_id:
            self.hand_current_img = img
            self.canvas.itemconfigure(self.hand_id, image=img)
        self.hand_recoil_after = self.canvas.after(100, self.reset_hand_rotation)

        def move_body(dx):
            if self.body_id:
                self.canvas.move(self.body_id, dx, 0)
            if self.hand_id:
                self.canvas.move(self.hand_id, dx, 0)
        if self.recoil_after_id:
            self.canvas.after_cancel(self.recoil_after_id)
            self.recoil_after_id = None
        move_body(body_offset)
        self.recoil_after_id = self.canvas.after(80, lambda: move_body(-body_offset))

    def start_walk_anim(self):
        if self.walk_anim_after is not None:
            self.canvas.after_cancel(self.walk_anim_after)
            self.walk_anim_after = None
        self.walk_frame_idx = 0
        self.advance_walk_frame()

    def stop_walk_anim(self):
        if self.walk_anim_after is not None:
            self.canvas.after_cancel(self.walk_anim_after)
            self.walk_anim_after = None
        self.set_legs_image(self.legs_stop_img)

    def advance_walk_frame(self):
        if not self.is_walking:
            return
        frames = self.walk_frames_left if self.walk_dir == "left" else self.walk_frames_right
        frame = frames[self.walk_frame_idx]
        self.set_legs_image(frame)
        self.walk_frame_idx = (self.walk_frame_idx + 1) % len(frames)
        self.walk_anim_after = self.canvas.after(80, self.advance_walk_frame)

    def frame_cut(self, gif):
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

    def set_legs_image(self, img):
        if img is not self.current_legs_img:
            self.current_legs_img = img
            self.canvas.itemconfigure(self.legs_id, image=img)

    def set_jump_legs(self):
        if self.walk_anim_after is not None:
            self.canvas.after_cancel(self.walk_anim_after)
            self.walk_anim_after = None
        self.is_walking = False
        jump_img = self.legs_jump_left if self.walk_dir == "left" else self.legs_jump_right
        self.set_legs_image(jump_img)

    def hitbox_bbox(self):
        coords = self.canvas.coords(self.legs_id)
        if len(coords) == 4:
            x1, y1, x2, y2 = coords
            return (x1, y1, x2, y2)
        elif len(coords) == 2:
            x, y = coords
            
            w = self.legs_stop_img.width()
            h = self.legs_stop_img.height()
            return (x, y, x + w, y + h)
        return (0, 0, PlayerWidth, PlayerHeight)

    def return_hand_img(self, direction, angle):
        assets = self.hand_assets.get(self.weapon_name, self.hand_assets.get("usp"))
        if assets is None:
            return None
        base_pil = assets["left_pil"] if direction == "left" else assets["right_pil"]
        rotated = base_pil.rotate(angle, expand=True)
        tk_img = ImageTk.PhotoImage(rotated)
        return tk_img

    def reset_hand_rotation(self):
        self.hand_angle = self.hand_base_angle
        img = self.return_hand_img(self.hand_dir, self.hand_angle)
        if img and self.hand_id:
            self.hand_current_img = img
            self.canvas.itemconfigure(self.hand_id, image=img)
        self.hand_recoil_after = None

    def update_hand(self):
        if not self.hand_id or self.weapon_name not in self.hand_assets:
            return
        self.canvas.itemconfigure(self.hand_id, state="normal")
        if self.body_id and self.body_img:
            coords = self.canvas.coords(self.body_id)
            if len(coords) >= 2:
                bx, by = coords[0], coords[1]
            else:
                bx, by = 0, 0
            bw, bh = self.body_img.width(), self.body_img.height()
        else:
            coords = self.canvas.coords(self.hitbox)
            if len(coords) >= 4:
                bx, by = coords[0], coords[1]
            elif len(coords) >= 2:
                bx, by = coords[0], coords[1]
            else:
                bx, by = 0, 0
            bw = self.body_img.width() if self.body_img else PlayerWidth
            bh = self.body_img.height() if self.body_img else PlayerHeight

        img = self.return_hand_img(self.hand_dir, self.hand_angle)
        if img:
            self.canvas.itemconfigure(self.hand_id, image=img)
            self.hand_current_img = img
            hx, hy = img.width(), img.height()
        else:
            hx = hy = 0

        if self.hand_dir == "left":
            hand_x = bx - hx * 0.6
        else:
            hand_x = bx + bw - hx * 0.4
        hand_y = by + (bh - hy) * 0.5
        self.canvas.coords(self.hand_id, hand_x, hand_y)