from tkinter import *
import time, random, math
from PIL import Image as PILImage, ImageDraw, ImageFont, ImageTk

from constants import *
from player import Player
from bullet import Bullet
from monster import Monster
from shop import Shop

class Game:
    def __init__(self, window):
        self.window = window

        self.canvas = Canvas(self.window, width=WindowWidth, height=WindowHeight)
        self.canvas.pack(expand=True, fill=BOTH)

        self.window.title("Stickman & Gun")
        self.window.geometry(f"{WindowWidth}x{WindowHeight}")
        self.window.resizable(0, 0)

        self.fonts = {
            "gold": "Times 18 bold",
            "hp_label": "Times 14 bold",
            "hp_text": "Times 14 bold",
            "ammo": "Times 14 bold",
            "small": "Times 12 bold",
            "wave": "Times 40 bold",
            "damage": "Times 14 bold",
            "info": "Times 16 bold",
            "price": "Times 12 bold",
            "tooltip": "Times 16 bold"
        }

        self.bg = PhotoImage(file=ImagePath+"Background.png")
        self.bg_id = self.canvas.create_image(0, 0, image=self.bg, anchor="nw")

        self.casing_left_img = PhotoImage(file=ImagePath+"TanpiLeft.png")
        self.casing_right_img = PhotoImage(file=ImagePath+"TanpiRight.png")

        self.keys = set()
        self.mouse_x = WindowWidth // 2
        self.mouse_y = WindowHeight // 2
        self.shop = Shop(self)
        self.game_over_flag = False
        self.game_clear_flag = False

        self.window.bind("<KeyPress>", self.on_key_press)
        self.window.bind("<KeyRelease>", self.on_key_release)
        self.window.bind("<ButtonPress-1>", self.on_mouse_down)
        self.window.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.window.bind("<Motion>", self.on_mouse_move)
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

        self.shooting = False

        self.gold = 0
        self.wave = 0
        self.max_wave = 20
        self.wave_running = False

        self.next_wave_number = 1
        self.next_wave_time = time.time() + 1.0

        self.hp = PlayerMaxHP
        self.last_hit_time = 0
        self.last_regen_time = time.time()

        gold_x = WindowWidth * 0.01
        gold_y = HUDY
        self.gold_img = PhotoImage(file=ImagePath+"Gold.png")
        self.gold_icon = self.canvas.create_image(gold_x, gold_y, image=self.gold_img, anchor="w")
        gold_text_x = gold_x + 100
        self.gold_text = self.canvas.create_text(
            gold_text_x, gold_y, fill="#F9AB3F", font=self.fonts["gold"],
            text=f"{self.gold}"
        )
        self.selector_bg = None
        self.noselector_bg = None
        self.selector_bg_id = None
        self.noselector_bg_id = None
        self.slot_positions = {}
        self.slot_icons = {"selected": None, "other": None}
        self.slot_icon_type = {"selected": None, "other": None}
        self.weapon_icons = self.load_weapon_icons()
        self.init_weapon_selector()

        self.hud_hp_bar_bg = None
        self.hud_hp_bar_fg = None
        self.hud_hp_text = None

        self.swap_overlay_id = None
        self.swap_overlay_start = 0.0
        self.selector_size = (100, 60)

        self.reload_overlay_id = None
        self.reload_overlay_start = 0.0
        self.reload_overlay_duration = 0.0

        self.wave_clear_id = None
        self.wave_clear_ids = []
        self.wave_clear_until = 0.0

        self.player = Player(self.canvas)
        self.player.update_hp_bar(self.hp, PlayerMaxHP)
        self.init_hud_hp()

        self.weapon_slots = {1: "usp", 2: None}
        self.current_weapon_slot = 1
        self.player.weapon_name = self.weapon_slots[self.current_weapon_slot]
        
        self.weapon_ammo = {1: self.get_weapon_capacity(self.weapon_slots[1]), 2: None}
        self.reload_end = {1: 0.0, 2: 0.0}
        self.last_swap_time = 0.0
        self.update_weapon_hud()

        self.enemies = []
        self.bullets = []  
        self.casings = []
        self.damage_popups = []

        self.next_spawn_side = "left"
        self.pending_spawns = 0

        self.game_loop()

    def on_key_press(self, event):
        if self.shop.open:
            if event.keycode == 83:
                self.shop.toggle_shop()
                return
            if self.shop.choose_slot_mode and event.keycode in (49, 50):
                slot = 1 if event.keycode == 49 else 2
                self.shop.replace_weapon_slot(slot)
                return
            return

        self.keys.add(event.keycode)
        if event.keycode == 83: self.shop.toggle_shop()
        elif event.keycode == 27: self.on_close()
        elif event.keycode == 69: self.toggle_weapon_slot()
        elif event.keycode == 82: self.manual_reload()

    def on_key_release(self, event):
        if event.keycode in self.keys:
            self.keys.remove(event.keycode)

    def on_mouse_move(self, event):
        self.mouse_x, self.mouse_y = event.x, event.y

    def on_mouse_click(self, event):
        if self.shop.open:
            self.shop.handle_shop_click(event.x, event.y)
        else:
            self.shoot_towards(event.x, event.y)

    def on_mouse_down(self, event):
        self.mouse_x = event.x
        self.mouse_y = event.y

        if self.shop.open:
            self.shop.handle_shop_click(event.x, event.y)
            return

        self.shooting = True
        self.shoot_towards(event.x, event.y)

    def on_mouse_up(self, event):
        self.shooting = False

    def on_close(self):
        self.window.destroy()

    def update_weapon_hud(self):
        w1 = self.weapon_slots[1]
        w2 = self.weapon_slots[2]
        name1 = WeaponStats[w1]["name"] if w1 else "-"
        name2 = WeaponStats[w2]["name"] if w2 else "-"
        self.update_weapon_selector()

        self.swap_overlay_start = time.time()
        self.start_swap_overlay()

    def update_gold_text(self):
        if self.gold_text:
            self.canvas.itemconfigure(self.gold_text, text=f"{self.gold}")

    def update_hud_hp(self):
        if not self.hud_hp_bar_fg or not self.hud_hp_text:
            return
        
        coords_bg = self.canvas.coords(self.hud_hp_bar_bg)
        if len(coords_bg) >= 4:
            x1, y1, x2, y2 = coords_bg[0], coords_bg[1], coords_bg[2], coords_bg[3]
            bar_w = x2 - x1
            ratio = max(0, min(1, self.hp / PlayerMaxHP))
            self.canvas.coords(self.hud_hp_bar_fg, x1, y1, x1 + bar_w * ratio, y2)
        self.canvas.itemconfigure(self.hud_hp_text, text=f"{self.hp}/{PlayerMaxHP}")

    def load_weapon_icons(self):
        icons = {}
        for key, stats in WeaponStats.items():
            candidates = [f"{key}.png", f"{stats['name']}.png"]
            img = None
            for path in candidates:
                img = PhotoImage(file=ImagePath+path)
                if img:
                    break
            if img:
                icons[key] = img
        return icons

    def init_weapon_selector(self):
        self.selector_bg = PhotoImage(file=ImagePath+"Selector.png")
        self.noselector_bg = PhotoImage(file=ImagePath+"NoSelector.png")

        def enlarge(img):
            if img:
                try:
                    return img.zoom(3).subsample(2)
                except Exception:
                    return img
            return img
        self.selector_bg = enlarge(self.selector_bg)
        self.noselector_bg = enlarge(self.noselector_bg)

        cx = WindowWidth * 0.5
        cy = HUDY + 30

        base_offset = 80
        if self.selector_bg:
            base_offset = max(base_offset, self.selector_bg.width() * 0.6)
        if self.noselector_bg:
            base_offset = max(base_offset, self.noselector_bg.width() * 0.6)

        other_pos    = (cx - base_offset * 1.5 - 50, cy)
        selected_pos = (cx - base_offset * 0.5 - 25, cy)
        self.slot_positions = {"selected": selected_pos, "other": other_pos}

        if self.noselector_bg:
            self.noselector_bg_id = self.canvas.create_image(other_pos[0], other_pos[1], image=self.noselector_bg, anchor="center")
        if self.selector_bg:
            self.selector_bg_id = self.canvas.create_image(selected_pos[0], selected_pos[1], image=self.selector_bg, anchor="center")

        if self.selector_bg:
            self.selector_size = (self.selector_bg.width(), self.selector_bg.height())
        else:
            self.selector_size = (100, 60)

    def init_hud_hp(self):
        if not self.slot_positions:
            return
        selected_pos = self.slot_positions.get("selected", (WindowWidth * 0.5, HUDY + 30))
        hp_x = selected_pos[0] + (self.selector_bg.width() * 0.5 if self.selector_bg else 60) + 40
        hp_y = selected_pos[1]
        bar_w = 200
        bar_h = 25
        self.hud_hp_label = self.canvas.create_text(hp_x - 20, hp_y, text="HP", fill="black", font=self.fonts["hp_label"])
        self.hud_hp_bar_bg = self.canvas.create_rectangle(
            hp_x, hp_y - bar_h/2, hp_x + bar_w, hp_y + bar_h/2,
            fill="#1a1a1a", outline="black", width=2
        )
        self.hud_hp_bar_fg = self.canvas.create_rectangle(
            hp_x, hp_y - bar_h/2, hp_x + bar_w, hp_y + bar_h/2,
            fill="red", outline=""
        )
        self.hud_hp_text = self.canvas.create_text(
            hp_x + bar_w/2, hp_y, fill="white", font=self.fonts["hp_text"],
            text=f"{self.hp}/{PlayerMaxHP}"
        )
        ammo_y = selected_pos[1] + (self.selector_size[1] * 0.5 if self.selector_bg else 30) + 15
        self.ammo_text = self.canvas.create_text(
            selected_pos[0], ammo_y, fill="white", font=self.fonts["ammo"], text=""
        )

    def update_weapon_selector(self):
        selected_slot = self.current_weapon_slot
        other_slot = 2 if selected_slot == 1 else 1
        mapping = {"selected": selected_slot, "other": other_slot}

        for label, slot in mapping.items():
            key = self.weapon_slots[slot]
            pos = self.slot_positions.get(label, (WindowWidth * 0.5, HUDY + 30))
            icon = self.weapon_icons.get(key) if key else None

            if icon:
                if self.slot_icon_type[label] != "image":
                    if self.slot_icons[label]:
                        self.canvas.delete(self.slot_icons[label])
                    self.slot_icons[label] = self.canvas.create_image(pos[0], pos[1], image=icon, anchor="center")
                    self.slot_icon_type[label] = "image"
                else:
                    self.canvas.itemconfigure(self.slot_icons[label], image=icon)
            else:
                text = "-" if key is None else WeaponStats[key]["name"]
                if self.slot_icon_type[label] != "text":
                    if self.slot_icons[label]:
                        self.canvas.delete(self.slot_icons[label])
                    self.slot_icons[label] = self.canvas.create_text(pos[0], pos[1], text=text, fill="white", font=self.fonts["small"])
                    self.slot_icon_type[label] = "text"
                else:
                    self.canvas.itemconfigure(self.slot_icons[label], text=text)
        self.update_ammo_text()

    def start_swap_overlay(self):
        if self.swap_overlay_id:
            self.canvas.delete(self.swap_overlay_id)
            self.swap_overlay_id = None
        pos = self.slot_positions.get("selected", (WindowWidth * 0.5, HUDY + 30))
        w, h = self.selector_size
        x0 = pos[0] - w * 0.5
        x1 = pos[0] + w * 0.5
        y0 = pos[1] - h * 0.5
        y1 = pos[1] + h * 0.5
        self.swap_overlay_id = self.canvas.create_rectangle(
            x0, y0, x1, y1, fill="#808080", outline="", stipple="gray50"
        )

    def update_swap_overlay(self, now):
        if not self.swap_overlay_id:
            return
        elapsed = now - self.swap_overlay_start
        remain = SWAP_COOLDOWN - elapsed
        if remain <= 0:
            self.canvas.delete(self.swap_overlay_id)
            self.swap_overlay_id = None
            return
        ratio = max(0.0, min(1.0, remain / SWAP_COOLDOWN))
        pos = self.slot_positions.get("selected", (WindowWidth * 0.5, HUDY + 30))
        w, h = self.selector_size
        x0 = pos[0] - w * 0.5
        x1 = pos[0] + w * 0.5

        y1 = pos[1] + h * 0.5
        y0 = y1 - h * ratio
        self.canvas.coords(self.swap_overlay_id, x0, y0, x1, y1)

    def start_reload_overlay(self, duration):
        if self.reload_overlay_id:
            self.canvas.delete(self.reload_overlay_id)
            self.reload_overlay_id = None
        pos = self.slot_positions.get("selected", (WindowWidth * 0.5, HUDY + 30))
        w, h = self.selector_size
        x0 = pos[0] - w * 0.5
        x1 = pos[0] + w * 0.5
        y0 = pos[1] - h * 0.5
        y1 = pos[1] + h * 0.5
        self.reload_overlay_id = self.canvas.create_rectangle(
            x0, y0, x1, y1, fill="#808080", outline="", stipple="gray50"
        )
        self.reload_overlay_start = time.time()
        self.reload_overlay_duration = duration

    def update_reload_overlay(self, now):
        if not self.reload_overlay_id:
            return
        elapsed = now - self.reload_overlay_start
        remain = self.reload_overlay_duration - elapsed
        if remain <= 0:
            self.canvas.delete(self.reload_overlay_id)
            self.reload_overlay_id = None
            return
        ratio = max(0.0, min(1.0, remain / self.reload_overlay_duration))
        pos = self.slot_positions.get("selected", (WindowWidth * 0.5, HUDY + 30))
        w, h = self.selector_size
        x0 = pos[0] - w * 0.5
        x1 = pos[0] + w * 0.5
        y1 = pos[1] + h * 0.5
        y0 = y1 - h * ratio
        self.canvas.coords(self.reload_overlay_id, x0, y0, x1, y1)

    def show_wave_clear(self, wave_num):
        if self.wave_clear_id:
            self.canvas.delete(self.wave_clear_id)
            self.wave_clear_id = None
        for oid in self.wave_clear_ids:
            self.canvas.delete(oid)
        self.wave_clear_ids = []
        txt = f"{wave_num+1}/{self.max_wave}"
        x = WindowWidth * 0.5
        y = WindowHeight * 0.4

        offsets = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        for dx, dy in offsets:
            oid = self.canvas.create_text(x + dx, y + dy, text=txt, fill="black", font=self.fonts["wave"])
            self.wave_clear_ids.append(oid)
        self.wave_clear_id = self.canvas.create_text(x, y, text=txt, fill="white", font=self.fonts["wave"])
        self.wave_clear_until = time.time() + 3.0

    def update_wave_clear(self, now):
        if self.wave_clear_id and now >= self.wave_clear_until:
            self.canvas.delete(self.wave_clear_id)
            self.wave_clear_id = None
            for oid in self.wave_clear_ids:
                self.canvas.delete(oid)
            self.wave_clear_ids = []

    def get_weapon_capacity(self, key):
        if key is None:
            return None
        return WeaponStats.get(key, {}).get("ammo", 0)

    def start_reload(self, slot, now, stats):
        if self.reload_end.get(slot, 0) > now:
            return
        wkey = self.weapon_slots.get(slot)
        cap = self.get_weapon_capacity(wkey) if wkey else None
        self.weapon_ammo[slot] = cap
        self.reload_end[slot] = now + stats.get("reload", 0)
        if slot == self.current_weapon_slot:
            self.start_reload_overlay(stats.get("reload", 0))
            self.update_ammo_text(reloading=True)
        else:
            self.update_ammo_text()

    def manual_reload(self):
        slot = self.current_weapon_slot
        wkey = self.weapon_slots.get(slot)
        if not wkey:
            return
        now = time.time()
        if self.reload_end.get(slot, 0) > now:
            return
        self.ensure_slot_ammo(slot)
        cap = self.get_weapon_capacity(wkey)
        cur = self.weapon_ammo.get(slot, 0)
        if cur is None:
            cur = cap
            self.weapon_ammo[slot] = cur
        if cur >= cap:
            return
        self.start_reload(slot, now, WeaponStats[wkey])

    def check_reload(self, now):
        for slot in (1, 2):
            end = self.reload_end.get(slot, 0)
            if end and now >= end:
                wkey = self.weapon_slots.get(slot)
                cap = self.get_weapon_capacity(wkey) if wkey else None
                self.weapon_ammo[slot] = cap
                self.reload_end[slot] = 0.0
                if slot == self.current_weapon_slot:
                    if self.reload_overlay_id:
                        self.canvas.delete(self.reload_overlay_id)
                        self.reload_overlay_id = None
                    self.update_ammo_text()

    def ensure_slot_ammo(self, slot):
        key = self.weapon_slots.get(slot)
        if key and self.weapon_ammo.get(slot) is None:
            self.weapon_ammo[slot] = self.get_weapon_capacity(key)

    def update_ammo_text(self, reloading=False):
        if not hasattr(self, "ammo_text") or self.ammo_text is None:
            return
        slot = self.current_weapon_slot
        key = self.weapon_slots.get(slot)
        if not key:
            self.canvas.itemconfigure(self.ammo_text, text="")
            return
        cur = self.weapon_ammo.get(slot, 0)
        cap = self.get_weapon_capacity(key)
        if cur is None:
            cur = cap
            self.weapon_ammo[slot] = cur
        if self.reload_end.get(slot, 0) > time.time():
            self.canvas.itemconfigure(self.ammo_text, text="Reloading...")
        else:
            self.canvas.itemconfigure(self.ammo_text, text=f"{cur}/{cap}")

    def select_weapon_slot(self, slot):
        if self.weapon_slots[slot] is None:
            return
        now = time.time()
        if self.reload_end.get(self.current_weapon_slot, 0) > now:
            return
        if now - self.last_swap_time < SWAP_COOLDOWN:
            return
        self.last_swap_time = now
        self.current_weapon_slot = slot
        self.player.weapon_name = self.weapon_slots[slot]
        self.ensure_slot_ammo(slot)
        self.update_weapon_hud()
        if self.shop.open:
            self.shop.update_shop_button_highlight()

    def toggle_weapon_slot(self):
        other = 2 if self.current_weapon_slot == 1 else 1
        if self.weapon_slots[other] is None:
            return
        self.select_weapon_slot(other)

    def game_loop(self):
        self.update()
        self.window.after(33, self.game_loop)

    def update(self):
        if self.game_over_flag or self.game_clear_flag:
            return
        paused = self.shop.open
        now = time.time()

        if (not self.wave_running) and (not self.shop.open) and (self.next_wave_number <= self.max_wave):
            if now >= self.next_wave_time:
                self.start_wave(self.next_wave_number)

        self.player.update(self.keys, paused=paused)

        if (not paused) and self.shooting:
            self.shoot_towards(self.mouse_x, self.mouse_y)
        self.check_reload(now)

        for b in self.bullets[:]:
            b.update(paused)
            x1,y1,x2,y2 = b.get_bbox()
            if x2 < 0 or x1 > WindowWidth or y2 < 0 or y1 > WindowHeight:
                b.destroy()
                self.bullets.remove(b)

        px, _ = self.player.get_center()
        for e in self.enemies:
            e.update(px, paused)

        if not paused:
            self.handle_player_collision()
            self.handle_collisions()
            self.regen_player_hp(now)
            self.update_casings(now)
            self.update_damage_popups(now)
            self.update_swap_overlay(now)
            self.update_reload_overlay(now)
        if self.wave_running and (not self.enemies) and (self.pending_spawns == 0):
            self.wave_running = False
            self.next_wave_number = self.wave + 1
            self.next_wave_time = now + 2.0
            self.show_wave_clear(self.wave)

        self.update_wave_clear(now)

        if (not self.wave_running) and (self.next_wave_number > self.max_wave) and (not self.enemies) and (self.pending_spawns == 0):
            self.game_clear()

    def handle_collisions(self):
        for b in self.bullets[:]:
            bx1, by1, bx2, by2 = b.get_bbox()
            hit = None
            for e in self.enemies:
                ex1, ey1, ex2, ey2 = e.get_bbox()
                if not (bx2 < ex1 or bx1 > ex2 or by2 < ey1 or by1 > ey2):
                    hit = e
                    break
            if hit:
                dmg = b.damage if hasattr(b, "damage") else self.player.get_weapon_stats()["damage"]
                died = hit.hit(dmg)
                bx = (bx1 + bx2) / 2
                by = (by1 + by2) / 2
                self.create_damage_popup(bx, by, dmg)
                b.destroy()
                self.bullets.remove(b)
                if died:
                    self.gold += hit.gold
                    self.update_gold_text()
                    hit.destroy()
                    if hit in self.enemies:
                        self.enemies.remove(hit)

    def handle_player_collision(self):
        now = time.time()
        if now - self.last_hit_time < PlayerDamageDelay:
            return

        player_x1, player_y1, player_x2, player_y2 = self.canvas.coords(self.player.hitbox)

        for e in self.enemies:
            ex1, ey1, ex2, ey2 = e.get_bbox()
            if not (player_x2 < ex1 or player_x1 > ex2 or player_y2 < ey1 or player_y1 > ey2):
                self.hp -= 10
                self.player.update_hp_bar(self.hp, PlayerMaxHP)
                self.update_hud_hp()
                self.last_hit_time = now
                self.last_regen_time = now

                if self.hp <= 0:
                    self.game_over()
                return
                
    def game_over(self):
        if self.game_over_flag:
            return
        self.game_over_flag = True
        keep = set()
        if self.bg_id:
            keep.add(self.bg_id)
        for iid in self.canvas.find_all():
            if iid not in keep:
                self.canvas.delete(iid)

        self.canvas.create_text(
            WindowWidth * 0.5, WindowHeight * 0.4,
            fill="red", font=self.fonts["wave"],
            text="GAME OVER"
        )
        self.canvas.create_text(
            WindowWidth * 0.5, WindowHeight * 0.5,
            fill="white", font=self.fonts["info"],
            text="ESC로 종료"
        )
        self.wave_running = False
        self.shooting = False
        self.enemies.clear()
        self.bullets.clear()
        self.casings.clear()
        self.damage_popups.clear()

    def regen_player_hp(self, now):
        if self.hp >= PlayerMaxHP:
            self.last_regen_time = now
            return
        if now - self.last_hit_time < 3:
            self.last_regen_time = now
            return
        elapsed = now - self.last_regen_time
        if elapsed <= 0:
            return
        heal = int(elapsed * 2)
        if heal <= 0:
            return
        self.hp = min(PlayerMaxHP, self.hp + heal)
        self.last_regen_time = now
        self.player.update_hp_bar(self.hp, PlayerMaxHP)
        self.update_hud_hp()

    def shoot_towards(self, tx, ty):
        now = time.time()
        w = self.player.get_weapon_stats()
        delay = 1.0 / w["fire_delay"] if w.get("fire_delay", 0) > 0 else 999
        if now - self.player.last_shot_time < delay: return
        self.player.last_shot_time = now

        dir_dx = tx - self.player.x
        dir_str = "right" if dir_dx >= 0 else "left"
        self.player.set_body_direction(dir_str)
        self.player.update_hand()

        self.player.set_hand_aim(tx, ty)
        px, py = self.player.get_muzzle_position()

        dx = tx - px
        dy = ty - py
        dist = (dx*dx + dy*dy) ** 0.5
        if dist == 0: return
        vx = dx / dist
        vy = dy / dist

        slot = self.current_weapon_slot
        self.ensure_slot_ammo(slot)
        ammo = self.weapon_ammo.get(slot, 0)
        if ammo is None:
            key = self.weapon_slots.get(slot)
            ammo = self.get_weapon_capacity(key) if key else 0
            self.weapon_ammo[slot] = ammo
        if self.reload_end.get(slot, 0) > now:
            return
        if ammo <= 0:
            self.start_reload(slot, now, w)
            return
        self.weapon_ammo[slot] = ammo - 1
        self.update_ammo_text()

        self.player.apply_recoil(dir_str)
        self.spawn_casing(px, py, vx, vy)

        if self.player.weapon_name == "m1897":
            pellets = w.get("pellets", 5)
            spread = w.get("spread", 0.3)
            for _ in range(pellets):
                angle = random.uniform(-spread, spread)
                cs, sn = math.cos(angle), math.sin(angle)
                vx2 = vx * cs - vy * sn
                vy2 = vx * sn + vy * cs
                bullet = Bullet(self.canvas, px, py, vx2*BULLET_SPEED, vy2*BULLET_SPEED, w["damage"])
                self.bullets.append(bullet)
            if self.weapon_ammo[slot] <= 0:
                self.start_reload(slot, now, w)
        else:
            beam_len = WindowWidth * 1.5
            end_x = px + vx * beam_len
            end_y = py + vy * beam_len

            hit_enemy, hx, hy = self.raycast_enemies(px, py, end_x, end_y)
            if hit_enemy:
                end_x, end_y = hx, hy
            end_x, end_y = self.clip_to_window(px, py, end_x, end_y)

            beam = self.canvas.create_line(px, py, end_x, end_y, fill="yellow", width=3)
            self.window.after(80, lambda: self.canvas.delete(beam))

            if hit_enemy:
                dmg = w["damage"]
                died = hit_enemy.hit(dmg)
                self.create_damage_popup(end_x, end_y, dmg)
                if died:
                    self.gold += hit_enemy.gold
                    self.update_gold_text()
                    hit_enemy.destroy()
                    if hit_enemy in self.enemies:
                        self.enemies.remove(hit_enemy)
            if self.weapon_ammo[slot] <= 0:
                self.start_reload(slot, now, w)

    def spawn_casing(self, px, py, vx, vy):
        speed = random.uniform(0.008, 0.015) * WindowWidth
        angle_base = math.atan2(vy, vx) + math.pi
        angle = angle_base + random.uniform(-1.6, 1.6)
        cvx = math.cos(angle) * speed
        cvy = -math.sin(angle) * speed * random.uniform(0.5, 0.9)

        sx = px - vx * 6
        sy = py - vy * 6

        if self.player.hand_dir == "left":
            img = self.casing_left_img
        else:
            img = self.casing_right_img
        cid = self.canvas.create_image(sx, sy, image=img, anchor="center")
        self.casings.append({"id": cid, "vx": cvx, "vy": cvy, "t": time.time()})

    def update_casings(self, now):
        gravity = 0.003 * WindowHeight
        drag = 0.9
        lifetime = 1.5
        for c in self.casings[:]:
            if now - c["t"] > lifetime:
                self.canvas.delete(c["id"])
                self.casings.remove(c)
                continue
            c["vy"] += gravity
            c["vx"] *= drag
            self.canvas.move(c["id"], c["vx"], c["vy"])
            x1, y1, x2, y2 = self.canvas.bbox(c["id"])
            if x2 < -10 or x1 > WindowWidth + 10 or y1 > WindowHeight + 10:
                self.canvas.delete(c["id"])
                self.casings.remove(c)

    def create_damage_popup(self, x, y, amount):
        txt = self.canvas.create_text(x, y, text=str(amount), fill="red", font=self.fonts["damage"])
        self.damage_popups.append({"id": txt, "start": time.time(), "x": x, "y": y})

    def update_damage_popups(self, now):
        duration = 1.5
        rise_speed = 20
        for p in self.damage_popups[:]:
            elapsed = now - p["start"]
            if elapsed >= duration:
                self.canvas.delete(p["id"])
                self.damage_popups.remove(p)
                continue
            dy = -rise_speed * (now - p["start"])
            self.canvas.coords(p["id"], p["x"], p["y"] + dy)

    def raycast_enemies(self, sx, sy, ex, ey):
        closest = None
        closest_dist2 = float("inf")
        hit_point = None

        for e in self.enemies:
            rect = e.get_bbox()
            if not self.rect_on_screen(rect):
                continue
            hx, hy = self.segment_hit_point(sx, sy, ex, ey, rect)
            if hx is None:
                continue
            d2 = (hx - sx)**2 + (hy - sy)**2
            if d2 < closest_dist2:
                closest_dist2 = d2
                closest = e
                hit_point = (hx, hy)

        if closest and hit_point:
            return closest, hit_point[0], hit_point[1]
        return None, None, None

    def clip_to_window(self, sx, sy, ex, ey):
        if 0 <= ex <= WindowWidth and 0 <= ey <= WindowHeight:
            return ex, ey
        edges = [
            (0, 0, WindowWidth, 0),
            (WindowWidth, 0, WindowWidth, WindowHeight),
            (WindowWidth, WindowHeight, 0, WindowHeight),
            (0, WindowHeight, 0, 0),
        ]
        closest = (ex, ey)
        closest_d2 = float("inf")
        for x1, y1, x2, y2 in edges:
            hit, hx, hy = self.segment_intersection(sx, sy, ex, ey, x1, y1, x2, y2)
            if hit:
                d2 = (hx - sx)**2 + (hy - sy)**2
                if d2 < closest_d2:
                    closest_d2 = d2
                    closest = (hx, hy)
        return closest

    def rect_on_screen(self, rect):
        rx1, ry1, rx2, ry2 = rect
        return not (rx2 < 0 or rx1 > WindowWidth or ry2 < 0 or ry1 > WindowHeight)

    def point_in_rect(self, x, y, rect):
        rx1, ry1, rx2, ry2 = rect
        return (rx1 <= x <= rx2) and (ry1 <= y <= ry2)

    def segment_hit_point(self, x1, y1, x2, y2, rect):
        if self.point_in_rect(x1, y1, rect):
            return x1, y1

        rx1, ry1, rx2, ry2 = rect
        edges = [
            (rx1, ry1, rx2, ry1),
            (rx2, ry1, rx2, ry2),
            (rx2, ry2, rx1, ry2),
            (rx1, ry2, rx1, ry1),
        ]
        closest = None
        closest_dist2 = float("inf")
        for ex1, ey1, ex2, ey2 in edges:
            hit, hx, hy = self.segment_intersection(x1, y1, x2, y2, ex1, ey1, ex2, ey2)
            if hit:
                d2 = (hx - x1)**2 + (hy - y1)**2
                if d2 < closest_dist2:
                    closest_dist2 = d2
                    closest = (hx, hy)
        return closest if closest else (None, None)

    def segment_intersection(self, x1, y1, x2, y2, x3, y3, x4, y4):
        def ccw(ax, ay, bx, by, cx, cy):
            return (cy - ay) * (bx - ax) > (by - ay) * (cx - ax)

        if (x1 == x2 and y1 == y2) or (x3 == x4 and y3 == y4):
            return False, None, None

        d1 = ccw(x1, y1, x3, y3, x4, y4)
        d2 = ccw(x2, y2, x3, y3, x4, y4)
        d3 = ccw(x1, y1, x2, y2, x3, y3)
        d4 = ccw(x1, y1, x2, y2, x4, y4)

        if d1 == d2 or d3 == d4:
            return False, None, None

        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if denom == 0:
            return False, None, None
        px = ((x1*y2 - y1*x2)*(x3 - x4) - (x1 - x2)*(x3*y4 - y3*x4)) / denom
        py = ((x1*y2 - y1*x2)*(y3 - y4) - (y1 - y2)*(x3*y4 - y3*x4)) / denom

        if (min(x1,x2)-1e-6 <= px <= max(x1,x2)+1e-6 and
            min(y1,y2)-1e-6 <= py <= max(y1,y2)+1e-6 and
            min(x3,x4)-1e-6 <= px <= max(x3,x4)+1e-6 and
            min(y3,y4)-1e-6 <= py <= max(y3,y4)+1e-6):
            return True, px, py
        return False, None, None

    def start_wave(self, wave_num):
        self.wave_running = True
        self.wave = wave_num

        monster_types = self.get_wave_monsters(wave_num)
        boss_wave = (wave_num in (10, 20))

        self.enemies = []
        self.pending_spawns = len(monster_types)
        side_counts = {"left": 0, "right": 0}
        for m in monster_types:
            side = self.next_spawn_side
            self.next_spawn_side = "right" if side == "left" else "left"
            delay = side_counts[side] * 2000
            side_counts[side] += 1
            self.window.after(delay, lambda mon=m, s=side: self.spawn_enemy(mon, s, boss_wave))

        if not boss_wave:
            pass

    def get_wave_monsters(self, w):
        if w == 10:
            extras = []
            pool = ["slime", "zombie"]
            extra_count = 6
            for _ in range(extra_count):
                extras.append(random.choice(pool))
            return ["kingslime"] + extras
        if w == 20:
            extras = []
            pool = ["slime", "zombie", "snail", "snake"]
            extra_count = 8
            for _ in range(extra_count):
                extras.append(random.choice(pool))
            return ["crawler"] + extras

        unlocked = []
        if w >= 1: unlocked.append("slime")
        if w >= 6: unlocked.append("zombie")
        if w >= 11: unlocked.append("snail")
        if w >= 16: unlocked.append("snake")

        base = 4
        count = min(base + w // 2, 14)

        if 1 <= w <= 4: main = "slime"
        elif 6 <= w <= 9: main = "zombie"
        elif 11 <= w <= 14: main = "snail"
        elif 16 <= w <= 19: main = "snake"
        else: main = unlocked[0]

        arr = []
        for _ in range(count):
            arr.append(main if random.random() < 0.6 else random.choice(unlocked))
        return arr

    def spawn_enemy(self, monster_type, spawn_side, big_boss):
        enemy = Monster(self.canvas, monster_type, spawn_side=spawn_side, big_boss=big_boss)
        self.enemies.append(enemy)
        if self.pending_spawns > 0:
            self.pending_spawns -= 1

    def game_clear(self):
        if self.game_clear_flag:
            return
        self.game_clear_flag = True
        self.wave_running = False
        self.shooting = False
        keep = set()
        if self.bg_id:
            keep.add(self.bg_id)
        for attr in ("hitbox", "legs_id", "body_id", "hand_id", "hp_bar_bg", "hp_bar_fg"):
            val = getattr(self.player, attr, None)
            if val:
                keep.add(val)
        for iid in self.canvas.find_all():
            if iid not in keep:
                self.canvas.delete(iid)

        msg = "GAME CLEAR!"
        offsets = [(-2,0),(2,0),(0,-2),(0,2)]
        x = WindowWidth * 0.5
        y = WindowHeight * 0.4
        for dx, dy in offsets:
            self.canvas.create_text(x+dx, y+dy, text=msg, fill="black", font=self.fonts["wave"])
        self.canvas.create_text(x, y, text=msg, fill="white", font=self.fonts["wave"])
        self.canvas.create_text(
            x, WindowHeight * 0.5,
            fill="white", font=self.fonts["info"],
            text="ESC로 종료"
        )