from __future__ import annotations

import random
import threading
import time
import tkinter as tk
from dataclasses import dataclass

try:
    import winsound
except ImportError:  # pragma: no cover - non-Windows fallback
    winsound = None


WINDOW_WIDTH = 960
WINDOW_HEIGHT = 720
HUD_WIDTH = 220
CELL_SIZE = 24
GRID_WIDTH = 30
GRID_HEIGHT = 28
PLAYFIELD_WIDTH = GRID_WIDTH * CELL_SIZE
PLAYFIELD_HEIGHT = GRID_HEIGHT * CELL_SIZE
FPS = 60
FRAME_MS = int(1000 / FPS)

BG = "#05060A"
PANEL = "#0E1320"
GRID = "#141B2A"
NEON_GREEN = "#6BFF8D"
NEON_MINT = "#B9FFCB"
NEON_BLUE = "#69D7FF"
NEON_RED = "#FF5E7E"
NEON_GOLD = "#FFD166"
TEXT = "#E8F3FF"
DIM = "#8CA2BF"


@dataclass
class MenuItem:
    label: str
    action: str


class RetroSounds:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root

    def play(self, pattern: list[tuple[int, int]]) -> None:
        if winsound is None:
            self.root.bell()
            return

        def worker() -> None:
            for frequency, duration in pattern:
                if frequency <= 0:
                    time.sleep(duration / 1000)
                else:
                    winsound.Beep(frequency, duration)

        threading.Thread(target=worker, daemon=True).start()

    def menu_move(self) -> None:
        self.play([(660, 35), (820, 30)])

    def select(self) -> None:
        self.play([(740, 50), (980, 70)])

    def start(self) -> None:
        self.play([(520, 40), (660, 40), (840, 70)])

    def eat(self) -> None:
        self.play([(1180, 30), (1460, 35)])

    def game_over(self) -> None:
        self.play([(700, 70), (530, 90), (350, 140)])


class CatsSnake:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Cat's Snake")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        self.canvas = tk.Canvas(
            self.root,
            width=WINDOW_WIDTH,
            height=WINDOW_HEIGHT,
            bg=BG,
            highlightthickness=0,
        )
        self.canvas.pack()

        self.sounds = RetroSounds(self.root)
        self.random = random.Random()
        self.menu_items = [
            MenuItem("PLAY GAME", "play"),
            MenuItem("ABOUT", "about"),
            MenuItem("EXIT GAME", "exit"),
        ]
        self.menu_index = 0
        self.state = "menu"
        self.score = 0
        self.best_score = 0
        self.speed_level = 1
        self.move_interval = 0.11
        self.move_timer = 0.0
        self.last_tick = time.perf_counter()

        self.snake: list[tuple[int, int]] = []
        self.direction = (1, 0)
        self.next_direction = (1, 0)
        self.food = (0, 0)
        self.flash_timer = 0.0
        self.message = "PRESS ENTER"

        self.root.bind("<KeyPress>", self.on_key_press)
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)

        self.reset_game()
        self.draw()
        self.tick()

    def reset_game(self) -> None:
        center_x = GRID_WIDTH // 2
        center_y = GRID_HEIGHT // 2
        self.snake = [
            (center_x - 2, center_y),
            (center_x - 1, center_y),
            (center_x, center_y),
        ]
        self.direction = (1, 0)
        self.next_direction = (1, 0)
        self.score = 0
        self.speed_level = 1
        self.move_interval = 0.11
        self.move_timer = 0.0
        self.flash_timer = 0.0
        self.message = "PRESS ARROWS OR WASD"
        self.spawn_food()

    def spawn_food(self) -> None:
        free_cells = [
            (x, y)
            for x in range(GRID_WIDTH)
            for y in range(GRID_HEIGHT)
            if (x, y) not in self.snake
        ]
        self.food = self.random.choice(free_cells)

    def on_key_press(self, event: tk.Event) -> None:
        key = event.keysym.lower()

        if self.state == "menu":
            if key in {"up", "w"}:
                self.menu_index = (self.menu_index - 1) % len(self.menu_items)
                self.sounds.menu_move()
            elif key in {"down", "s"}:
                self.menu_index = (self.menu_index + 1) % len(self.menu_items)
                self.sounds.menu_move()
            elif key in {"return", "space"}:
                self.activate_menu()
            return

        if self.state == "about":
            if key in {"escape", "return", "space"}:
                self.state = "menu"
                self.sounds.menu_move()
            return

        if self.state == "gameover":
            if key in {"return", "space"}:
                self.start_game()
            elif key == "escape":
                self.state = "menu"
            return

        directions = {
            "up": (0, -1),
            "w": (0, -1),
            "down": (0, 1),
            "s": (0, 1),
            "left": (-1, 0),
            "a": (-1, 0),
            "right": (1, 0),
            "d": (1, 0),
        }

        if key in directions:
            new_direction = directions[key]
            if new_direction != (-self.direction[0], -self.direction[1]):
                self.next_direction = new_direction
        elif key == "escape":
            self.state = "menu"

    def activate_menu(self) -> None:
        action = self.menu_items[self.menu_index].action
        self.sounds.select()
        if action == "play":
            self.start_game()
        elif action == "about":
            self.state = "about"
        elif action == "exit":
            self.root.destroy()

    def start_game(self) -> None:
        self.reset_game()
        self.state = "playing"
        self.sounds.start()

    def tick(self) -> None:
        now = time.perf_counter()
        delta = min(now - self.last_tick, 0.05)
        self.last_tick = now

        if self.state == "playing":
            self.move_timer += delta
            self.flash_timer = max(0.0, self.flash_timer - delta)

            while self.move_timer >= self.move_interval:
                self.move_timer -= self.move_interval
                self.step_game()

        self.draw()
        self.root.after(FRAME_MS, self.tick)

    def step_game(self) -> None:
        self.direction = self.next_direction
        head_x, head_y = self.snake[-1]
        dx, dy = self.direction
        new_head = (head_x + dx, head_y + dy)

        hit_wall = not (0 <= new_head[0] < GRID_WIDTH and 0 <= new_head[1] < GRID_HEIGHT)
        hit_self = new_head in self.snake
        if hit_wall or hit_self:
            self.best_score = max(self.best_score, self.score)
            self.state = "gameover"
            self.message = "ENTER = RESTART   ESC = MENU"
            self.sounds.game_over()
            return

        self.snake.append(new_head)
        if new_head == self.food:
            self.score += 10
            self.speed_level = min(12, 1 + self.score // 50)
            self.move_interval = max(0.045, 0.11 - (self.speed_level - 1) * 0.0055)
            self.flash_timer = 0.14
            self.best_score = max(self.best_score, self.score)
            self.spawn_food()
            self.sounds.eat()
        else:
            self.snake.pop(0)

    def draw(self) -> None:
        self.canvas.delete("all")
        self.draw_background()

        if self.state == "menu":
            self.draw_menu()
        elif self.state == "about":
            self.draw_menu()
            self.draw_about_panel()
        else:
            self.draw_game()
            if self.state == "gameover":
                self.draw_game_over()

    def draw_background(self) -> None:
        self.canvas.create_rectangle(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT, fill=BG, outline="")
        self.canvas.create_rectangle(
            26,
            26,
            26 + PLAYFIELD_WIDTH + 18,
            26 + PLAYFIELD_HEIGHT + 18,
            outline=NEON_BLUE,
            width=3,
        )
        self.canvas.create_rectangle(
            PLAYFIELD_WIDTH + 70,
            26,
            WINDOW_WIDTH - 26,
            WINDOW_HEIGHT - 26,
            fill=PANEL,
            outline=NEON_BLUE,
            width=3,
        )

    def draw_logo(self, x: int, y: int, size: int = 34) -> None:
        for offset, color in ((4, "#102338"), (0, NEON_MINT)):
            self.canvas.create_text(
                x + offset,
                y + offset,
                text="CAT'S SNAKE",
                fill=color,
                font=("Courier New", size, "bold"),
                anchor="n",
            )

    def draw_menu(self) -> None:
        self.draw_logo(WINDOW_WIDTH // 2, 68, 36)
        self.canvas.create_text(
            WINDOW_WIDTH // 2,
            145,
            text="RETRO ATARI-STYLE SNAKE",
            fill=DIM,
            font=("Courier New", 16, "bold"),
            anchor="n",
        )

        box_x1 = 250
        box_y1 = 210
        box_x2 = 710
        box_y2 = 510
        self.canvas.create_rectangle(box_x1, box_y1, box_x2, box_y2, outline=NEON_GREEN, width=2)

        for index, item in enumerate(self.menu_items):
            y = 280 + index * 82
            selected = index == self.menu_index
            fill = NEON_GOLD if selected else TEXT
            outline = NEON_GOLD if selected else GRID
            self.canvas.create_rectangle(315, y - 28, 645, y + 28, outline=outline, width=3)
            prefix = ">> " if selected else "   "
            self.canvas.create_text(
                480,
                y,
                text=f"{prefix}{item.label}",
                fill=fill,
                font=("Courier New", 22, "bold"),
                anchor="center",
            )

        self.canvas.create_text(
            WINDOW_WIDTH // 2,
            570,
            text="UP / DOWN TO CHOOSE   ENTER TO SELECT",
            fill=DIM,
            font=("Courier New", 14, "bold"),
            anchor="center",
        )
        self.canvas.create_text(
            WINDOW_WIDTH // 2,
            615,
            text="NO ENGINE FILES. JUST PYTHON, BEEPS, AND BOOPS.",
            fill=NEON_BLUE,
            font=("Courier New", 13, "bold"),
            anchor="center",
        )

    def draw_about_panel(self) -> None:
        x1, y1, x2, y2 = 170, 165, 790, 560
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=PANEL, outline=NEON_RED, width=3)
        lines = [
            "CAT'S SNAKE",
            "",
            "A pure Python retro snake game.",
            "Built with tkinter and Atari-style energy.",
            "",
            "FEATURES",
            "- 60 FPS render loop",
            "- Play / About / Exit menu",
            "- Windows beeps and boops",
            "- Speed ramps up as you score",
            "",
            "PRESS ESC OR ENTER TO GO BACK",
        ]
        for index, line in enumerate(lines):
            color = NEON_MINT if index in {0, 5} else TEXT
            size = 22 if index == 0 else 16
            self.canvas.create_text(
                (x1 + x2) // 2,
                y1 + 40 + index * 28,
                text=line,
                fill=color,
                font=("Courier New", size, "bold" if index in {0, 5} else "normal"),
                anchor="n",
            )

    def draw_game(self) -> None:
        self.canvas.create_rectangle(35, 35, 35 + PLAYFIELD_WIDTH, 35 + PLAYFIELD_HEIGHT, fill="#091017", outline="")

        for x in range(GRID_WIDTH + 1):
            px = 35 + x * CELL_SIZE
            self.canvas.create_line(px, 35, px, 35 + PLAYFIELD_HEIGHT, fill=GRID)
        for y in range(GRID_HEIGHT + 1):
            py = 35 + y * CELL_SIZE
            self.canvas.create_line(35, py, 35 + PLAYFIELD_WIDTH, py, fill=GRID)

        self.draw_food()
        self.draw_snake()
        self.draw_hud()

    def draw_food(self) -> None:
        x, y = self.food
        x1 = 35 + x * CELL_SIZE + 4
        y1 = 35 + y * CELL_SIZE + 4
        x2 = x1 + CELL_SIZE - 8
        y2 = y1 + CELL_SIZE - 8
        pulse = 2 if self.flash_timer > 0 else 0
        self.canvas.create_oval(x1 - pulse, y1 - pulse, x2 + pulse, y2 + pulse, fill=NEON_RED, outline=NEON_GOLD, width=2)

    def draw_snake(self) -> None:
        for index, (x, y) in enumerate(self.snake):
            x1 = 35 + x * CELL_SIZE + 2
            y1 = 35 + y * CELL_SIZE + 2
            x2 = x1 + CELL_SIZE - 4
            y2 = y1 + CELL_SIZE - 4

            if index == len(self.snake) - 1:
                fill = NEON_MINT
                outline = NEON_BLUE
            else:
                fill = NEON_GREEN
                outline = "#2AAD56"

            self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline=outline, width=2)

        head_x, head_y = self.snake[-1]
        eye_x = 35 + head_x * CELL_SIZE + CELL_SIZE // 2
        eye_y = 35 + head_y * CELL_SIZE + CELL_SIZE // 2
        self.canvas.create_oval(eye_x - 5, eye_y - 4, eye_x - 1, eye_y, fill=BG, outline="")
        self.canvas.create_oval(eye_x + 1, eye_y - 4, eye_x + 5, eye_y, fill=BG, outline="")

    def draw_hud(self) -> None:
        base_x = PLAYFIELD_WIDTH + 92
        self.draw_logo(base_x + 76, 58, 20)

        hud_lines = [
            ("SCORE", str(self.score)),
            ("BEST", str(self.best_score)),
            ("ATARI SPEED", str(self.speed_level)),
            ("FPS", str(FPS)),
        ]

        for index, (label, value) in enumerate(hud_lines):
            y = 160 + index * 92
            self.canvas.create_text(base_x, y, text=label, fill=DIM, font=("Courier New", 14, "bold"), anchor="nw")
            self.canvas.create_text(
                base_x,
                y + 28,
                text=value,
                fill=NEON_GOLD if label == "ATARI SPEED" else TEXT,
                font=("Courier New", 28, "bold"),
                anchor="nw",
            )

        controls = [
            "CONTROLS",
            "ARROWS / WASD",
            "ESC = MENU",
            "",
            "GOAL",
            "EAT RED ORBS",
            "DON'T HIT WALLS",
            "DON'T HIT YOURSELF",
        ]
        for index, line in enumerate(controls):
            color = NEON_BLUE if index in {0, 4} else TEXT
            weight = "bold" if index in {0, 4} else "normal"
            self.canvas.create_text(
                base_x,
                500 + index * 23,
                text=line,
                fill=color,
                font=("Courier New", 14, weight),
                anchor="nw",
            )

    def draw_game_over(self) -> None:
        x1, y1, x2, y2 = 145, 235, 610, 455
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=PANEL, outline=NEON_RED, width=3)
        self.canvas.create_text(
            (x1 + x2) // 2,
            y1 + 34,
            text="GAME OVER",
            fill=NEON_RED,
            font=("Courier New", 28, "bold"),
            anchor="n",
        )
        self.canvas.create_text(
            (x1 + x2) // 2,
            y1 + 94,
            text=f"FINAL SCORE  {self.score}",
            fill=TEXT,
            font=("Courier New", 18, "bold"),
            anchor="n",
        )
        self.canvas.create_text(
            (x1 + x2) // 2,
            y1 + 140,
            text=self.message,
            fill=NEON_GOLD,
            font=("Courier New", 14, "bold"),
            anchor="n",
        )

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    CatsSnake().run()
