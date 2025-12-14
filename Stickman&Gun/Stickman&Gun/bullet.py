from tkinter import *
from constants import WindowWidth

class Bullet:
    def __init__(self, canvas, x, y, vx, vy, damage):
        self.canvas = canvas
        self.vx = vx
        self.vy = vy
        self.damage = damage
        r = max(3, int(WindowWidth * 0.003))
        self.id = self.canvas.create_oval(x-r, y-r, x+r, y+r, fill="yellow")

    def update(self, paused=False):
        if not paused:
            self.canvas.move(self.id, self.vx, self.vy)

    def get_bbox(self):
        return self.canvas.coords(self.id)

    def destroy(self):
        self.canvas.delete(self.id)