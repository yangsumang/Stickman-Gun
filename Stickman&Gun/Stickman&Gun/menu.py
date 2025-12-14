from tkinter import *
from constants import *
from game import Game

class Menu:
    def __init__(self, window):
        self.window = window

        self.canvas = Canvas(self.window, width=WindowWidth, height=WindowHeight)
        self.canvas.pack(fill=BOTH, expand=True)

        self.bg_img = PhotoImage(file=ImagePath+"Background.png")
        self.canvas.create_image(0, 0, image=self.bg_img, anchor="nw")
        
        self.title_img = PhotoImage(file=ImagePath+"Title.png")
        self.playbutton_img = PhotoImage(file=ImagePath+"PlayButton.png")

        self.draw()
        self.canvas.bind("<Button-1>", self.play_click)

    # 플레이 버튼 좌표 왼쪽위: 544,608  818,707 이 제일 이뻤음
    def draw(self):
        self.canvas.create_image(650, 200, image=self.title_img, anchor="center")
        self.canvas.create_image(544, 608, image=self.playbutton_img, anchor="nw")
    
    def play_click(self, event):
        if 544 <= event.x <= 818 and 608 <= event.y <= 707:
            self.canvas.unbind("<Button-1>")
            self.canvas.destroy()
            self.game = Game(self.window)