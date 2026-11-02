import tkinter as tk


class BreakoutGame:
    WIDTH = 800
    HEIGHT = 600
    PADDLE_WIDTH = 110
    PADDLE_HEIGHT = 14
    BALL_RADIUS = 9
    BRICK_ROWS = 5
    BRICK_COLUMNS = 10
    BRICK_GAP = 6
    BRICK_TOP = 70

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("블럭깨기")
        self.root.resizable(False, False)

        self.canvas = tk.Canvas(
            root,
            width=self.WIDTH,
            height=self.HEIGHT,
            background="#101827",
            highlightthickness=0,
        )
        self.canvas.pack()
        self.canvas.focus_set()

        self.keys_down: set[str] = set()
        self.space_down = False
        self.bricks: dict[int, int] = {}

        self.root.bind_all("<KeyPress>", self._on_key_press)
        self.root.bind_all("<KeyRelease>", self._on_key_release)

        self._restart()
        self._update()

    def _restart(self) -> None:
        self.canvas.delete("all")
        self.bricks.clear()

        self.score = 0
        self.lives = 3
        self.state = "playing"
        self.paddle_x = self.WIDTH / 2
        self.ball_x = self.WIDTH / 2
        self.ball_y = self.HEIGHT - 115
        self.ball_vx = 3.2
        self.ball_vy = -4.7

        paddle_y = self.HEIGHT - 48
        self.paddle = self.canvas.create_rectangle(
            self.paddle_x - self.PADDLE_WIDTH / 2,
            paddle_y,
            self.paddle_x + self.PADDLE_WIDTH / 2,
            paddle_y + self.PADDLE_HEIGHT,
            fill="#e7edf5",
            outline="",
        )
        self.ball = self.canvas.create_oval(
            self.ball_x - self.BALL_RADIUS,
            self.ball_y - self.BALL_RADIUS,
            self.ball_x + self.BALL_RADIUS,
            self.ball_y + self.BALL_RADIUS,
            fill="#ffffff",
            outline="",
        )
        self.score_text = self.canvas.create_text(
            16, 16, anchor="nw", fill="#ffffff", font=("맑은 고딕", 13, "bold")
        )
        self.lives_text = self.canvas.create_text(
            self.WIDTH - 16,
            16,
            anchor="ne",
            fill="#ffffff",
            font=("맑은 고딕", 13, "bold"),
        )
        self.overlay = self.canvas.create_text(
            self.WIDTH / 2,
            self.HEIGHT / 2,
            text="",
            fill="#ffffff",
            font=("맑은 고딕", 24, "bold"),
            justify="center",
        )

        self._create_bricks()
        self._update_hud()

    def _create_bricks(self) -> None:
        colors = ("#ff6b6b", "#ff9f43", "#feca57", "#48dbfb", "#5f9df7")
        side_margin = 42
        brick_width = (
            self.WIDTH
            - side_margin * 2
            - self.BRICK_GAP * (self.BRICK_COLUMNS - 1)
        ) / self.BRICK_COLUMNS
        brick_height = 22

        for row in range(self.BRICK_ROWS):
            for column in range(self.BRICK_COLUMNS):
                x1 = side_margin + column * (brick_width + self.BRICK_GAP)
                y1 = self.BRICK_TOP + row * (brick_height + self.BRICK_GAP)
                brick = self.canvas.create_rectangle(
                    x1,
                    y1,
                    x1 + brick_width,
                    y1 + brick_height,
                    fill=colors[row],
                    outline="",
                )
                self.bricks[brick] = 10 * (self.BRICK_ROWS - row)

    def _on_key_press(self, event: tk.Event) -> None:
        key = event.keysym.lower()
        self.keys_down.add(key)

        if key == "space" and not self.space_down:
            self.space_down = True
            if self.state == "playing":
                self.state = "paused"
                self.canvas.itemconfigure(
                    self.overlay, text="일시정지\n스페이스바를 눌러 계속"
                )
            elif self.state == "paused":
                self.state = "playing"
                self.canvas.itemconfigure(self.overlay, text="")
        elif key == "r":
            self._restart()

    def _on_key_release(self, event: tk.Event) -> None:
        key = event.keysym.lower()
        self.keys_down.discard(key)
        if key == "space":
            self.space_down = False

    def _update(self) -> None:
        if self.state == "playing":
            self._move_paddle()
            self._move_ball()

        self._update_hud()
        self.root.after(16, self._update)

    def _move_paddle(self) -> None:
        direction = 0
        if "left" in self.keys_down or "a" in self.keys_down:
            direction -= 1
        if "right" in self.keys_down or "d" in self.keys_down:
            direction += 1

        half_width = self.PADDLE_WIDTH / 2
        self.paddle_x = max(
            half_width,
            min(self.WIDTH - half_width, self.paddle_x + direction * 7),
        )
        paddle_y = self.HEIGHT - 48
        self.canvas.coords(
            self.paddle,
            self.paddle_x - half_width,
            paddle_y,
            self.paddle_x + half_width,
            paddle_y + self.PADDLE_HEIGHT,
        )

    def _move_ball(self) -> None:
        radius = self.BALL_RADIUS
        previous_x, previous_y = self.ball_x, self.ball_y
        self.ball_x += self.ball_vx
        self.ball_y += self.ball_vy

        if self.ball_x - radius <= 0 or self.ball_x + radius >= self.WIDTH:
            self.ball_vx *= -1
            self.ball_x = max(radius, min(self.WIDTH - radius, self.ball_x))
        if self.ball_y - radius <= 0:
            self.ball_vy = abs(self.ball_vy)
            self.ball_y = radius

        paddle_y = self.HEIGHT - 48
        if (
            self.ball_vy > 0
            and self.ball_y + radius >= paddle_y
            and self.ball_y - radius <= paddle_y + self.PADDLE_HEIGHT
            and abs(self.ball_x - self.paddle_x)
            <= self.PADDLE_WIDTH / 2 + radius
        ):
            self.ball_y = paddle_y - radius
            self.ball_vy = -abs(self.ball_vy)
            hit_offset = (self.ball_x - self.paddle_x) / (self.PADDLE_WIDTH / 2)
            self.ball_vx = max(-7, min(7, self.ball_vx + hit_offset * 2.2))

        overlapping = self.canvas.find_overlapping(
            self.ball_x - radius,
            self.ball_y - radius,
            self.ball_x + radius,
            self.ball_y + radius,
        )
        for item in overlapping:
            if item not in self.bricks:
                continue

            x1, y1, x2, y2 = self.canvas.coords(item)
            if previous_y + radius <= y1 or previous_y - radius >= y2:
                self.ball_vy *= -1
            else:
                self.ball_vx *= -1
            self.score += self.bricks.pop(item)
            self.canvas.delete(item)

            if not self.bricks:
                self.state = "won"
                self.canvas.itemconfigure(
                    self.overlay, text="모든 블럭을 깼습니다!\nR 키를 눌러 다시 시작"
                )
            break

        if self.ball_y - radius > self.HEIGHT:
            self.lives -= 1
            if self.lives == 0:
                self.state = "game_over"
                self.canvas.itemconfigure(
                    self.overlay, text="게임 오버\nR 키를 눌러 다시 시작"
                )
            else:
                self.ball_x = self.WIDTH / 2
                self.ball_y = self.HEIGHT - 115
                self.ball_vx = 3.2
                self.ball_vy = -4.7

        self.canvas.coords(
            self.ball,
            self.ball_x - radius,
            self.ball_y - radius,
            self.ball_x + radius,
            self.ball_y + radius,
        )

    def _update_hud(self) -> None:
        self.canvas.itemconfigure(self.score_text, text=f"점수: {self.score}")
        self.canvas.itemconfigure(self.lives_text, text=f"목숨: {self.lives}")


def main() -> None:
    root = tk.Tk()
    BreakoutGame(root)
    root.mainloop()


if __name__ == "__main__":
    main()
