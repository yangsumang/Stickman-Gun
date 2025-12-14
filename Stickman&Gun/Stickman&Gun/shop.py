from constants import *
from tkinter import *

class Shop:
    def __init__(self, game):
        self.g = game

        self.open = False
        self.bg_img = PhotoImage(file=ImagePath+"Shop.png")
        self.selector_img = PhotoImage(file=ImagePath+"Selector.png")
        self.selector_img_big = self.selector_img.zoom(3).subsample(2)

        self.items = []        
        self.buttons = []        
        self.slot_items = []     
        self.bg_id = None
        self.bg_pos = (WindowWidth*0.5 - 25, WindowHeight*0.5)
        self.info_line = None
        self.choose_slot_mode = False
        self.pending_weapon_key = None
        self.pending_weapon_cost = 0
        self.purchased_weapons = set()
        self.buy_images = {}
        self.buy_order = []
        self.buy_stamp_ids = {}

    def toggle_shop(self):
        if self.open:
            self.close_shop()
        else:
            self.open_shop()

    def open_shop(self):
        g = self.g
        self.open = True

        self.bg_id = g.canvas.create_image(self.bg_pos[0], self.bg_pos[1], image=self.bg_img, anchor="center")
        self.items = []
        self.buttons = []

        self.info_line = g.canvas.create_text(
            700, 530, fill="white", font=g.fonts["info"], text=""
        )
        coords_map = {
            "usp":  (258, 337, 388, 384),
            "uzi":  (443, 338, 574, 386),
            "m1897":(630, 340, 762, 387),
            "m4a1": (815, 342, 945, 390),
            "awp":  (999, 342, 1132, 390),
        }
        weapons_order = ["usp","uzi","m1897","m4a1","awp"]
        for wkey in weapons_order:
            if wkey not in coords_map: continue
            x1,y1,x2,y2 = coords_map[wkey]
            rect = g.canvas.create_rectangle(x1, y1, x2, y2, fill="", outline="")
            self.items.append(rect)
            self.buttons.append({"weapon": wkey, "rect": rect, "text": None})
        self.draw_shop_slots()
        self.redraw_buy_stamps()

    def close_shop(self):
        g = self.g
        self.open = False
        items = [self.bg_id, self.info_line] + self.items + self.slot_items
        for i in items:
            g.canvas.delete(i)
        self.items = []
        self.buttons = []
        self.bg_id = None
        self.info_line = None
        self.slot_items = []
        for iid in self.buy_stamp_ids.values():
            g.canvas.delete(iid)
        self.buy_stamp_ids = {}
        self.choose_slot_mode = False
        self.pending_weapon_key = None
        self.pending_weapon_cost = 0

    def handle_shop_click(self, x, y):
        for btn in self.buttons:
            x1,y1,x2,y2 = self.g.canvas.coords(btn["rect"])
            if x1 <= x <= x2 and y1 <= y <= y2:
                self.buy_weapon(btn["weapon"])
                self.update_shop_button_highlight()
                break

    def draw_shop_slots(self):
        g = self.g
        for it in getattr(self, "slot_items", []):
            g.canvas.delete(it)
        self.slot_items = []
        sel_img = self.selector_img_big
        base_x, base_y = 700, 530
        sel_w, sel_h = sel_img.width(), sel_img.height()
        sel1_x = base_x - sel_w * 0.8
        sel1_y = base_y - sel_h * 0.8
        sel2_x = base_x + sel_w * 0.8
        sel2_y = sel1_y
        sel1_id = g.canvas.create_image(sel1_x, sel1_y, image=sel_img, anchor="center")
        sel2_id = g.canvas.create_image(sel2_x, sel2_y, image=sel_img, anchor="center")
        self.slot_items += [sel1_id, sel2_id]
        w1 = g.weapon_slots.get(1)
        w2 = g.weapon_slots.get(2)
        icon1 = g.weapon_icons.get(w1)
        icon2 = g.weapon_icons.get(w2)
        scale_zoom = 3
        scale_sub = 2
        if icon1:
            try:
                big1 = icon1.zoom(scale_zoom).subsample(scale_sub)
            except Exception:
                big1 = icon1
            icon1_id = g.canvas.create_image(sel1_x, sel1_y, image=big1, anchor="center")
            self.slot_items.append(big1)
            self.slot_items.append(icon1_id)
        if icon2:
            try:
                big2 = icon2.zoom(scale_zoom).subsample(scale_sub)
            except Exception:
                big2 = icon2
            icon2_id = g.canvas.create_image(sel2_x, sel2_y, image=big2, anchor="center")
            self.slot_items.append(big2)
            self.slot_items.append(icon2_id)

    def update_shop_button_highlight(self):
        if self.open and self.bg_img:
            self.draw_shop_slots()
        return

    def buy_weapon(self, weapon_key):
        g = self.g
        if weapon_key in g.weapon_slots.values():
            if self.info_line:
                g.canvas.itemconfigure(self.info_line, text="이미 장착된 무기입니다.")
            return
        cost = self.get_cost(weapon_key)

        empty_slot = 1 if g.weapon_slots[1] is None else (2 if g.weapon_slots[2] is None else None)

        if empty_slot is not None:
            if cost > 0 and g.gold < cost:
                if self.info_line:
                    g.canvas.itemconfigure(self.info_line, text=f"골드 부족! 필요 {cost}G")
                return
            if cost > 0:
                g.gold -= cost
            g.weapon_slots[empty_slot] = weapon_key
            g.current_weapon_slot = empty_slot
            g.player.weapon_name = weapon_key
            g.weapon_ammo[empty_slot] = g.get_weapon_capacity(weapon_key)
            g.update_gold_text()
            self.purchased_weapons.add(weapon_key)
            if weapon_key not in self.buy_order:
                self.buy_order.append(weapon_key)
            msg = f"{WeaponStats[weapon_key]['name']} 장착!"
            g.canvas.itemconfigure(self.info_line, text=msg)
            g.update_weapon_hud()
            self.show_buy_stamp(weapon_key)
            self.draw_shop_slots()
            return
        if cost > 0 and g.gold < cost:
            if self.info_line:
                g.canvas.itemconfigure(self.info_line, text=f"골드 부족! 필요 {cost}G")
            return
        self.choose_slot_mode = True
        self.pending_weapon_key = weapon_key
        self.pending_weapon_cost = cost
        g.canvas.itemconfigure(
            self.info_line,
            text=f"{WeaponStats[weapon_key]['name']} 선택! 바꿀 무기를 선택하세요. ( 1 or 2 )"
        )
        self.draw_shop_slots()

    def replace_weapon_slot(self, slot):
        g = self.g
        if not (self.choose_slot_mode and self.pending_weapon_key):
            return
        wkey = self.pending_weapon_key
        cost = self.pending_weapon_cost

        if cost > 0 and g.gold < cost:
            if self.info_line:
                g.canvas.itemconfigure(self.info_line, text=f"골드가 부족합니다. 필요: {cost}G")
            self.choose_slot_mode = False
            return

        if cost > 0:
            g.gold -= cost
        g.weapon_slots[slot] = wkey
        g.current_weapon_slot = slot
        g.player.weapon_name = wkey
        g.weapon_ammo[slot] = g.get_weapon_capacity(wkey)

        g.update_gold_text()
        self.purchased_weapons.add(wkey)
        if wkey not in self.buy_order:
            self.buy_order.append(wkey)
        if self.info_line:
            g.canvas.itemconfigure(self.info_line, text=f"{WeaponStats[wkey]['name']} 장착!")
        self.choose_slot_mode = False
        g.update_weapon_hud()
        self.show_buy_stamp(wkey)
        self.update_shop_button_highlight()

    def get_cost(self, weapon_key):
        base = WeaponStats[weapon_key]["cost"]
        if weapon_key in self.purchased_weapons:
            return 0
        return base

    def show_buy_stamp(self, weapon_key):
        img = self.get_buy_image(weapon_key)
        if not img:
            return
        self.redraw_buy_stamps()

    def get_buy_image(self, weapon_key):
        if weapon_key in self.buy_images:
            return self.buy_images[weapon_key]
        candidates = [
            f"{weapon_key}Buy.png",
            f"{WeaponStats[weapon_key]['name']}Buy.png",
        ]
        img = None
        for path in candidates:
            try:
                img = PhotoImage(file=ImagePath + path)
                if img:
                    break
            except Exception:
                img = None
        self.buy_images[weapon_key] = img
        return img

    def redraw_buy_stamps(self):
        if not self.open or not self.bg_id:
            return
        for iid in self.buy_stamp_ids.values():
            self.g.canvas.delete(iid)
        self.buy_stamp_ids = {}
        for wkey in self.buy_order:
            img = self.get_buy_image(wkey)
            if not img:
                continue
            x, y = self.bg_pos
            iid = self.g.canvas.create_image(x, y, image=img, anchor="center")
            self.buy_stamp_ids[wkey] = iid