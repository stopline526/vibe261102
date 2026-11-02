"""제비우스 스타일 종스크롤 슈팅 게임 (pygame)

조작법
  방향키 / WASD : 이동
  Z / Space     : 공중 공격 (누르고 있으면 연사)
  X             : 지상 폭탄 (조준점 위치에 떨어짐)
  P             : 일시정지
  Enter         : 시작 / 다시 하기
  Esc           : 종료

P 아이템을 먹으면 총알이 2 -> 4 -> 8 -> 16발로 늘어나고, 격추되면 한 단계 줄어든다.

그림과 소리 파일 없이 모든 그래픽과 효과음을 코드로 만든다.
"""

import math
import random
from array import array
from collections import deque

import pygame

WIDTH, HEIGHT = 480, 640
FPS = 60
TILE = 20
SCROLL_SPEED = 60
AREA_DURATION = 45
SIGHT_DISTANCE = 150
BOMB_FLIGHT_TIME = 0.45
BOMB_SPLASH = 20
FIRE_INTERVAL = 0.12
BOMB_INTERVAL = 0.35
RESPAWN_DELAY = 1.2
INVULNERABLE_TIME = 2.0
START_LIVES = 3
EXTEND_SCORE = 20000
ITEM_DROP_CHANCE = 0.1
ITEM_MAX_BONUS = 500

# 단계별 (총알 수, 총알 사이 간격, 총알 사이 각도)
SHOT_LEVELS = [
    (2, 16, 0.0),
    (4, 8, 0.06),
    (8, 4, 0.07),
    (16, 3, 0.05),
]

SAMPLE_RATE = 22050
MASTER_VOLUME = 0.5

WHITE = (240, 240, 245)
BLACK = (10, 10, 16)
RED = (230, 60, 60)
ORANGE = (250, 160, 50)
YELLOW = (250, 225, 90)
SILVER = (195, 200, 215)
STEEL = (110, 118, 135)
DARK_STEEL = (66, 72, 86)
CYAN = (90, 220, 240)

GRASS = (74, 128, 66)
FOREST = (44, 92, 52)
SAND = (186, 170, 118)
WATER = (52, 104, 170)
WATER_LIGHT = (78, 132, 196)


def distance(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)


class SoundBank:
    """효과음을 코드로 합성해 둔다. 오디오 장치가 없으면 소리 없이 진행한다."""

    def __init__(self):
        self.sounds = {}
        mixer_settings = pygame.mixer.get_init()
        if not mixer_settings or mixer_settings[1] != -16:
            return
        self.rate, _, self.channels = mixer_settings
        pygame.mixer.set_num_channels(16)
        self.sounds = {
            "shot": self.make([(1400, 500, 0.06)], 0.16, "square"),
            "bomb": self.make([(700, 180, 0.3)], 0.25),
            "bomb_hit": self.make([(180, 50, 0.3)], 0.5, "noise"),
            "explode": self.make([(320, 70, 0.22)], 0.4, "noise"),
            "block": self.make([(1800, 1500, 0.05)], 0.25, "square"),
            "item": self.make([(520, 520, 0.07), (780, 780, 0.07), (1040, 1040, 0.13)], 0.4, "square"),
            "extend": self.make([(660, 660, 0.1), (880, 880, 0.1), (1320, 1320, 0.22)], 0.4, "square"),
            "player_down": self.make([(600, 40, 0.8)], 0.6, "noise"),
            "boss_alert": self.make([(440, 660, 0.25), (440, 660, 0.25), (440, 660, 0.25)], 0.35, "square"),
            "boss_down": self.make([(260, 30, 1.2)], 0.7, "noise"),
            "game_over": self.make([(440, 440, 0.2), (349, 349, 0.2), (262, 262, 0.45)], 0.4, "square"),
        }

    def make(self, notes, volume, wave="sine"):
        """(시작 주파수, 끝 주파수, 길이) 음들을 이어 붙여 소리 하나를 만든다."""
        samples = array("h")
        for start, end, duration in notes:
            count = int(self.rate * duration)
            phase = 0.0
            noise = 0.0
            for i in range(count):
                p = i / count
                frequency = start + (end - start) * p
                phase += frequency / self.rate
                if wave == "noise":
                    # 주파수가 높을수록 자주 바뀌는 잡음이라 폭발음처럼 들린다
                    if phase >= 1:
                        phase -= 1
                        noise = random.uniform(-1, 1)
                    value = noise
                elif wave == "square":
                    value = 1 if phase % 1 < 0.5 else -1
                else:
                    value = math.sin(phase * math.tau)
                # 끝에서 잦아들게 해 딸깍거리는 소리를 막는다
                level = int(value * volume * MASTER_VOLUME * (1 - p) ** 0.7 * 32767)
                samples.extend([level] * self.channels)
        return pygame.mixer.Sound(buffer=samples.tobytes())

    def play(self, name):
        sound = self.sounds.get(name)
        if sound:
            sound.play()


class Controls:
    """한 프레임의 입력. 키보드와 게임 로직을 분리한다."""

    def __init__(self, dx=0, dy=0, fire=False, bomb=False):
        self.dx = dx
        self.dy = dy
        self.fire = fire
        self.bomb = bomb


class Terrain:
    """줄 단위로 만들어 아래로 흘려보내는 지형."""

    def __init__(self):
        self.river_x = random.uniform(100, WIDTH - 100)
        self.river_width = 50.0
        self.forest_x = random.uniform(0, WIDTH)
        self.offset = 0.0
        self.rows = deque()
        for _ in range(HEIGHT // TILE + 2):
            self.rows.append(self._make_row())

    def _make_row(self):
        # 강과 숲의 중심을 조금씩 움직여 이어지는 지형을 만든다
        self.river_x = min(WIDTH + 60, max(-60, self.river_x + random.uniform(-14, 14)))
        self.river_width = min(90, max(25, self.river_width + random.uniform(-5, 5)))
        self.forest_x = (self.forest_x + random.uniform(-16, 16)) % WIDTH

        surface = pygame.Surface((WIDTH, TILE))
        surface.fill(GRASS)
        for x in range(0, WIDTH, TILE):
            cx = x + TILE / 2
            river = abs(cx - self.river_x)
            if river < self.river_width:
                pygame.draw.rect(surface, WATER, (x, 0, TILE, TILE))
                if random.random() < 0.15:
                    pygame.draw.line(surface, WATER_LIGHT, (x + 3, 10), (x + 14, 10))
            elif river < self.river_width + TILE:
                pygame.draw.rect(surface, SAND, (x, 0, TILE, TILE))
            elif abs(cx - self.forest_x) < 70 and random.random() < 0.8:
                pygame.draw.rect(surface, FOREST, (x, 0, TILE, TILE))
                pygame.draw.circle(surface, GRASS, (x + random.randint(4, 16), random.randint(4, 16)), 2)
        return surface, self.river_x, self.river_width

    def is_land(self, x):
        # 새 지상 목표가 놓이는 맨 위 줄 기준으로 판단한다
        _, river_x, river_width = self.rows[0]
        return abs(x - river_x) > river_width + TILE + 16

    def update(self, dt):
        self.offset += SCROLL_SPEED * dt
        while self.offset >= TILE:
            self.offset -= TILE
            self.rows.pop()
            self.rows.appendleft(self._make_row())

    def draw(self, screen):
        y = self.offset - TILE
        for surface, _, _ in self.rows:
            screen.blit(surface, (0, y))
            y += TILE


class Player:
    RADIUS = 6

    def __init__(self):
        self.x = WIDTH / 2
        self.y = HEIGHT - 70
        self.speed = 240
        self.fire_timer = 0.0
        self.bomb_timer = 0.0
        self.invulnerable = INVULNERABLE_TIME

    @property
    def sight(self):
        return self.x, self.y - SIGHT_DISTANCE

    def update(self, game, dt, controls):
        length = math.hypot(controls.dx, controls.dy) or 1
        self.x += controls.dx / length * self.speed * dt
        self.y += controls.dy / length * self.speed * dt
        self.x = min(WIDTH - 18, max(18, self.x))
        self.y = min(HEIGHT - 24, max(SIGHT_DISTANCE + 40, self.y))

        self.fire_timer -= dt
        self.bomb_timer -= dt
        self.invulnerable = max(0, self.invulnerable - dt)

        if controls.fire and self.fire_timer <= 0:
            self.fire_timer = FIRE_INTERVAL
            count, spacing, spread = SHOT_LEVELS[game.shot_level]
            for i in range(count):
                offset = i - (count - 1) / 2
                game.shots.append(Shot(self.x + offset * spacing, self.y - 14, offset * spread))
            game.sounds.play("shot")
        if controls.bomb and self.bomb_timer <= 0:
            self.bomb_timer = BOMB_INTERVAL
            game.bombs.append(Bomb(self.x, self.y, *self.sight, scrolls=game.boss is None))
            game.sounds.play("bomb")

    def draw(self, screen):
        # 무적 시간에는 깜빡인다
        if self.invulnerable > 0 and int(self.invulnerable * 12) % 2:
            return
        x, y = self.x, self.y
        pygame.draw.polygon(screen, DARK_STEEL, [(x - 18, y + 12), (x, y - 6), (x + 18, y + 12), (x, y + 6)])
        pygame.draw.polygon(screen, SILVER, [(x, y - 20), (x + 8, y + 12), (x, y + 16), (x - 8, y + 12)])
        pygame.draw.polygon(screen, RED, [(x, y - 8), (x + 4, y + 4), (x - 4, y + 4)])
        pygame.draw.circle(screen, CYAN, (int(x), int(y - 10)), 3)


class Shot:
    SPEED = 620

    def __init__(self, x, y, angle=0.0):
        self.x = x
        self.y = y
        self.dir_x = math.sin(angle)
        self.dir_y = -math.cos(angle)

    def update(self, dt):
        self.x += self.dir_x * self.SPEED * dt
        self.y += self.dir_y * self.SPEED * dt

    def offscreen(self):
        return self.y < -20 or self.x < -20 or self.x > WIDTH + 20

    def draw(self, screen):
        tail = (self.x - self.dir_x * 14, self.y - self.dir_y * 14)
        pygame.draw.line(screen, YELLOW, (self.x, self.y), tail, 4)


class Item:
    """먹으면 총알이 늘어나는 P 아이템."""

    RADIUS = 13
    PICKUP_RADIUS = 24

    def __init__(self, x, y):
        self.x = min(WIDTH - 30, max(30, x))
        self.base_x = self.x
        self.y = y
        self.t = 0.0

    def update(self, dt):
        self.t += dt
        self.y += SCROLL_SPEED * 1.5 * dt
        self.x = self.base_x + math.sin(self.t * 2.5) * 20

    def offscreen(self):
        return self.y > HEIGHT + 20

    def draw(self, screen, font):
        pos = (int(self.x), int(self.y))
        color = CYAN if int(self.t * 6) % 2 else YELLOW
        pygame.draw.circle(screen, BLACK, pos, self.RADIUS + 2)
        pygame.draw.circle(screen, color, pos, self.RADIUS)
        label = font.render("P", True, BLACK)
        screen.blit(label, label.get_rect(center=pos))


class Bomb:
    """조준점으로 날아가 도착하는 순간 터지는 폭탄."""

    def __init__(self, x, y, target_x, target_y, scrolls):
        self.start_x = x
        self.start_y = y
        self.target_x = target_x
        self.target_y = target_y
        self.scrolls = scrolls
        self.t = 0.0

    @property
    def landed(self):
        return self.t >= BOMB_FLIGHT_TIME

    def update(self, dt):
        self.t += dt
        # 지상 목표는 지형과 함께 흐르므로 낙하 지점도 같이 흘려 조준을 맞춘다
        if self.scrolls:
            self.target_y += SCROLL_SPEED * dt

    def draw(self, screen):
        p = min(1, self.t / BOMB_FLIGHT_TIME)
        x = self.start_x + (self.target_x - self.start_x) * p
        y = self.start_y + (self.target_y - self.start_y) * p
        radius = max(2, int(6 - 4 * p))
        pygame.draw.circle(screen, ORANGE, (int(x), int(y)), radius)
        pygame.draw.circle(screen, WHITE, (int(x), int(y)), max(1, radius - 2))


class EnemyBullet:
    RADIUS = 4

    def __init__(self, x, y, vx, vy):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt

    def offscreen(self):
        return not (-10 < self.x < WIDTH + 10 and -10 < self.y < HEIGHT + 10)

    def draw(self, screen, blink):
        color = WHITE if blink else ORANGE
        pygame.draw.circle(screen, RED, (int(self.x), int(self.y)), self.RADIUS + 1)
        pygame.draw.circle(screen, color, (int(self.x), int(self.y)), self.RADIUS - 1)


class Explosion:
    def __init__(self, x, y, size=24, drifts=False):
        self.x = x
        self.y = y
        self.size = size
        self.drifts = drifts
        self.t = 0.0
        self.duration = 0.35 + size / 200

    @property
    def done(self):
        return self.t >= self.duration

    def update(self, dt):
        self.t += dt
        if self.drifts:
            self.y += SCROLL_SPEED * dt

    def draw(self, screen):
        p = self.t / self.duration
        radius = max(1, int(self.size * (0.3 + 0.7 * p)))
        surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        alpha = int(255 * (1 - p))
        pygame.draw.circle(surface, (*ORANGE, alpha), (radius, radius), radius)
        pygame.draw.circle(surface, (*YELLOW, alpha), (radius, radius), max(1, int(radius * 0.6)))
        screen.blit(surface, (self.x - radius, self.y - radius))


class AirEnemy:
    radius = 13
    score = 30
    destructible = True

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.t = 0.0
        self.alive = True

    def update(self, game, dt):
        self.t += dt

    def offscreen(self):
        return self.y > HEIGHT + 40 or self.y < -80 or self.x < -60 or self.x > WIDTH + 60


class Toroid(AirEnemy):
    """좌우로 흔들리며 내려오는 고리."""

    def __init__(self, x, y):
        super().__init__(x, y)
        self.base_x = x
        self.phase = random.uniform(0, math.tau)

    def update(self, game, dt):
        super().update(game, dt)
        self.y += 150 * dt
        self.x = self.base_x + math.sin(self.t * 3 + self.phase) * 60

    def draw(self, screen):
        width = int(abs(math.cos(self.t * 6)) * 11) + 3
        rect = pygame.Rect(self.x - width, self.y - 12, width * 2, 24)
        pygame.draw.ellipse(screen, SILVER, rect)
        pygame.draw.ellipse(screen, RED, rect, 2)


class Torkan(AirEnemy):
    """내려와서 한 발 쏘고 되돌아간다."""

    score = 50

    def __init__(self, x, y):
        super().__init__(x, y)
        self.stop_y = random.uniform(100, 280)
        self.phase = "down"
        self.wait = 0.5

    def update(self, game, dt):
        super().update(game, dt)
        if self.phase == "down":
            self.y += 220 * dt
            if self.y >= self.stop_y:
                self.phase = "wait"
        elif self.phase == "wait":
            self.wait -= dt
            if self.wait <= 0:
                game.fire_at_player(self.x, self.y)
                self.phase = "up"
        else:
            self.y -= 280 * dt

    def offscreen(self):
        return self.phase == "up" and self.y < -40

    def draw(self, screen):
        x, y = self.x, self.y
        pygame.draw.polygon(screen, STEEL, [(x - 15, y - 9), (x + 15, y - 9), (x, y + 14)])
        pygame.draw.polygon(screen, CYAN, [(x - 6, y - 5), (x + 6, y - 5), (x, y + 5)])


class Zoshi(AirEnemy):
    """플레이어를 쫓아오며 총을 쏜다."""

    score = 70
    radius = 12

    def __init__(self, x, y):
        super().__init__(x, y)
        self.angle = math.pi / 2
        self.fire_timer = random.uniform(0.8, 1.6)
        self.chase_time = 3.0

    def update(self, game, dt):
        super().update(game, dt)
        self.chase_time -= dt
        if self.chase_time > 0 and game.player:
            wanted = math.atan2(game.player.y - self.y, game.player.x - self.x)
            diff = (wanted - self.angle + math.pi) % math.tau - math.pi
            self.angle += max(-2.0 * dt, min(2.0 * dt, diff))
        self.x += math.cos(self.angle) * 170 * dt
        self.y += math.sin(self.angle) * 170 * dt
        self.fire_timer -= dt
        if self.fire_timer <= 0:
            self.fire_timer = random.uniform(1.2, 2.2)
            game.fire_at_player(self.x, self.y)

    def draw(self, screen):
        points = []
        for i in range(8):
            r = 14 if i % 2 == 0 else 6
            angle = self.t * 5 + i * math.pi / 4
            points.append((self.x + math.cos(angle) * r, self.y + math.sin(angle) * r))
        pygame.draw.polygon(screen, RED, points)
        pygame.draw.circle(screen, YELLOW, (int(self.x), int(self.y)), 4)


class Bacura(AirEnemy):
    """부술 수 없는 회전판. 총알을 막고 부딪히면 위험하다."""

    radius = 20
    score = 0
    destructible = False

    def update(self, game, dt):
        super().update(game, dt)
        self.y += SCROLL_SPEED * 1.4 * dt

    def draw(self, screen):
        height = int(abs(math.sin(self.t * 3)) * 16) + 3
        rect = pygame.Rect(self.x - 24, self.y - height, 48, height * 2)
        pygame.draw.rect(screen, DARK_STEEL, rect)
        pygame.draw.rect(screen, SILVER, rect, 2)


class GroundTarget:
    radius = 15
    score = 100
    drops_item = False

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.t = 0.0
        self.alive = True

    def update(self, game, dt):
        self.t += dt
        self.y += SCROLL_SPEED * dt

    def offscreen(self):
        return self.y > HEIGHT + 40 or self.x < -40 or self.x > WIDTH + 40


class Barra(GroundTarget):
    """움직이지 않는 돔."""

    def draw(self, screen):
        pos = (int(self.x), int(self.y))
        pygame.draw.circle(screen, DARK_STEEL, pos, 15)
        pygame.draw.circle(screen, SILVER, pos, 10)
        pygame.draw.circle(screen, STEEL, pos, 5)


class Zolbak(GroundTarget):
    """회전하는 레이더. 점수가 높고 부수면 반드시 아이템이 나온다."""

    score = 200
    drops_item = True

    def draw(self, screen):
        pos = (int(self.x), int(self.y))
        pygame.draw.circle(screen, DARK_STEEL, pos, 14)
        angle = self.t * 4
        end = (self.x + math.cos(angle) * 13, self.y + math.sin(angle) * 13)
        pygame.draw.line(screen, CYAN, pos, end, 3)
        pygame.draw.circle(screen, RED, pos, 3)


class Logram(GroundTarget):
    """플레이어를 향해 쏘는 포대."""

    score = 300

    def __init__(self, x, y):
        super().__init__(x, y)
        self.fire_timer = random.uniform(0.6, 1.8)

    def update(self, game, dt):
        super().update(game, dt)
        self.fire_timer -= dt
        if self.fire_timer <= 0 and self.y < HEIGHT - 120:
            self.fire_timer = random.uniform(1.6, 2.6)
            game.fire_at_player(self.x, self.y)

    def draw(self, screen):
        rect = pygame.Rect(self.x - 14, self.y - 14, 28, 28)
        pygame.draw.rect(screen, DARK_STEEL, rect)
        pygame.draw.rect(screen, STEEL, rect.inflate(-8, -8))
        pygame.draw.circle(screen, RED, (int(self.x), int(self.y)), 4)


class Grobda(GroundTarget):
    """옆으로 달리는 탱크. 맞히기 어렵고 점수가 가장 높다."""

    score = 400

    def __init__(self, x, y):
        super().__init__(x, y)
        self.direction = 1 if x < WIDTH / 2 else -1

    def update(self, game, dt):
        super().update(game, dt)
        self.x += self.direction * 45 * dt

    def draw(self, screen):
        x, y = self.x, self.y
        pygame.draw.rect(screen, BLACK, (x - 15, y - 11, 30, 22))
        pygame.draw.rect(screen, STEEL, (x - 12, y - 8, 24, 16))
        pygame.draw.circle(screen, DARK_STEEL, (int(x), int(y)), 6)
        pygame.draw.line(screen, DARK_STEEL, (x, y), (x + self.direction * 16, y), 3)


class BossPart:
    def __init__(self, dx, dy, radius, hp, score):
        self.dx = dx
        self.dy = dy
        self.radius = radius
        self.hp = hp
        self.score = score
        self.fire_timer = random.uniform(0.5, 2.0)

    @property
    def alive(self):
        return self.hp > 0


class Boss:
    """구역 끝의 거대 요새. 폭탄으로만 공격할 수 있고 중심 핵을 부수면 끝난다."""

    def __init__(self, area):
        self.x = WIDTH / 2
        self.y = -90.0
        self.t = 0.0
        self.core = BossPart(0, 0, 22, 4 + area * 2, 2000)
        self.turrets = [
            BossPart(-62, -32, 14, 2, 300),
            BossPart(62, -32, 14, 2, 300),
            BossPart(-62, 32, 14, 2, 300),
            BossPart(62, 32, 14, 2, 300),
        ]
        self.parts = [self.core] + self.turrets

    def pos(self, part):
        return self.x + part.dx, self.y + part.dy

    def update(self, game, dt):
        self.t += dt
        if self.y < 120:
            self.y += 70 * dt
            return
        self.x = WIDTH / 2 + math.sin(self.t * 0.7) * 100
        for turret in self.turrets:
            if not turret.alive:
                continue
            turret.fire_timer -= dt
            if turret.fire_timer <= 0:
                turret.fire_timer = max(0.9, 2.2 - game.area * 0.15) + random.uniform(0, 0.6)
                game.fire_at_player(*self.pos(turret))
        # 포대가 모두 부서지면 핵이 직접 부채꼴로 쏜다
        if not any(t.alive for t in self.turrets):
            self.core.fire_timer -= dt
            if self.core.fire_timer <= 0:
                self.core.fire_timer = 1.2
                for spread in (-0.35, 0, 0.35):
                    game.fire_at_player(self.x, self.y, spread)

    def draw(self, screen):
        x, y = self.x, self.y
        hull = [(x - 95, y - 22), (x - 45, y - 58), (x + 45, y - 58), (x + 95, y - 22),
                (x + 95, y + 22), (x + 45, y + 58), (x - 45, y + 58), (x - 95, y + 22)]
        pygame.draw.polygon(screen, DARK_STEEL, hull)
        pygame.draw.polygon(screen, SILVER, hull, 3)
        for turret in self.turrets:
            pos = tuple(int(v) for v in self.pos(turret))
            if turret.alive:
                pygame.draw.circle(screen, STEEL, pos, 14)
                pygame.draw.circle(screen, RED, pos, 6)
            else:
                pygame.draw.circle(screen, BLACK, pos, 11)
        pulse = int(abs(math.sin(self.t * 5)) * 6)
        pygame.draw.circle(screen, BLACK, (int(x), int(y)), 25)
        pygame.draw.circle(screen, RED, (int(x), int(y)), 14 + pulse)
        pygame.draw.circle(screen, YELLOW, (int(x), int(y)), 6)


class Game:
    def __init__(self):
        self.font = pygame.font.Font(None, 28)
        self.big_font = pygame.font.Font(None, 68)
        self.sounds = SoundBank()
        self.high_score = 0
        self.state = "title"  # title | playing | paused | gameover
        self.reset()

    def reset(self):
        self.terrain = Terrain()
        self.player = Player()
        self.shots = []
        self.bombs = []
        self.bullets = []
        self.air = []
        self.ground = []
        self.explosions = []
        self.items = []
        self.shot_level = 0
        self.boss = None
        self.score = 0
        self.next_extend = EXTEND_SCORE
        self.lives = START_LIVES
        self.area = 1
        self.area_time = 0.0
        self.respawn_timer = 0.0
        self.air_timer = 1.0
        self.ground_timer = 1.5
        self.banner_timer = 2.0
        self.clock_t = 0.0

    def start(self):
        self.reset()
        self.state = "playing"

    def toggle_pause(self):
        if self.state == "playing":
            self.state = "paused"
        elif self.state == "paused":
            self.state = "playing"

    def add_score(self, points):
        self.score += points
        self.high_score = max(self.high_score, self.score)
        while self.score >= self.next_extend:
            self.next_extend += EXTEND_SCORE
            self.lives += 1
            self.sounds.play("extend")

    def collect_item(self):
        if self.shot_level < len(SHOT_LEVELS) - 1:
            self.shot_level += 1
        else:
            self.add_score(ITEM_MAX_BONUS)
        self.sounds.play("item")

    def fire_at_player(self, x, y, spread=0.0):
        if not self.player:
            return
        angle = math.atan2(self.player.y - y, self.player.x - x) + spread
        speed = 170 + self.area * 15
        self.bullets.append(EnemyBullet(x, y, math.cos(angle) * speed, math.sin(angle) * speed))

    def spawn_air(self):
        x = random.uniform(40, WIDTH - 40)
        roll = random.random()
        if self.area >= 2 and roll < 0.12:
            enemy = Bacura(x, -30)
        elif roll < 0.5:
            # 토로이드는 편대로 나온다
            for i in range(4):
                self.air.append(Toroid(min(WIDTH - 70, max(70, x)), -30 - i * 42))
            return
        elif roll < 0.8:
            enemy = Torkan(x, -30)
        else:
            enemy = Zoshi(x, -30)
        self.air.append(enemy)

    def spawn_ground(self):
        for _ in range(8):
            x = random.uniform(30, WIDTH - 30)
            if self.terrain.is_land(x):
                break
        else:
            return
        kinds = [Barra, Barra, Zolbak, Logram]
        if self.area >= 2:
            kinds += [Logram, Grobda]
        self.ground.append(random.choice(kinds)(x, -30))

    def update_spawning(self, dt):
        if self.boss:
            return
        self.area_time += dt
        if self.area_time >= AREA_DURATION:
            self.boss = Boss(self.area)
            self.sounds.play("boss_alert")
            return
        self.air_timer -= dt
        if self.air_timer <= 0:
            self.air_timer = max(0.7, random.uniform(1.4, 2.4) - self.area * 0.15)
            self.spawn_air()
        self.ground_timer -= dt
        if self.ground_timer <= 0:
            self.ground_timer = max(0.5, random.uniform(0.9, 1.7) - self.area * 0.1)
            self.spawn_ground()

    def update(self, dt, controls):
        self.clock_t += dt
        if self.state != "playing":
            return
        self.banner_timer = max(0, self.banner_timer - dt)

        self.terrain.update(dt)
        self.update_spawning(dt)

        if self.player:
            self.player.update(self, dt, controls)
        elif self.lives > 0:
            self.respawn_timer -= dt
            if self.respawn_timer <= 0:
                self.player = Player()
        else:
            self.respawn_timer -= dt
            if self.respawn_timer <= 0:
                self.state = "gameover"
                self.sounds.play("game_over")

        for item in self.shots + self.bombs + self.bullets + self.explosions + self.items:
            item.update(dt)
        for enemy in self.air + self.ground:
            enemy.update(self, dt)
        if self.boss:
            self.boss.update(self, dt)

        self.handle_shot_hits()
        self.handle_bomb_hits()
        self.handle_item_pickups()
        self.handle_player_hits()

        self.shots = [s for s in self.shots if not s.offscreen()]
        self.items = [i for i in self.items if not i.offscreen()]
        self.bombs = [b for b in self.bombs if not b.landed]
        self.bullets = [b for b in self.bullets if not b.offscreen()]
        self.explosions = [e for e in self.explosions if not e.done]
        self.air = [e for e in self.air if e.alive and not e.offscreen()]
        self.ground = [g for g in self.ground if g.alive and not g.offscreen()]

    def handle_shot_hits(self):
        remaining = []
        for shot in self.shots:
            for enemy in self.air:
                if enemy.alive and distance(shot.x, shot.y, enemy.x, enemy.y) < enemy.radius + 4:
                    if enemy.destructible:
                        enemy.alive = False
                        self.add_score(enemy.score)
                        self.explosions.append(Explosion(enemy.x, enemy.y))
                        self.sounds.play("explode")
                        if random.random() < ITEM_DROP_CHANCE:
                            self.items.append(Item(enemy.x, enemy.y))
                    else:
                        self.explosions.append(Explosion(shot.x, shot.y, 8))
                        self.sounds.play("block")
                    break
            else:
                remaining.append(shot)
        self.shots = remaining

    def handle_bomb_hits(self):
        for bomb in self.bombs:
            if not bomb.landed:
                continue
            self.explosions.append(Explosion(bomb.target_x, bomb.target_y, 22, drifts=bomb.scrolls))
            self.sounds.play("bomb_hit")
            for target in self.ground:
                reach = target.radius + BOMB_SPLASH
                if target.alive and distance(bomb.target_x, bomb.target_y, target.x, target.y) < reach:
                    target.alive = False
                    self.add_score(target.score)
                    self.explosions.append(Explosion(target.x, target.y, 30, drifts=True))
                    self.sounds.play("explode")
                    if target.drops_item:
                        self.items.append(Item(target.x, target.y))
            if self.boss:
                self.bomb_boss(bomb)

    def handle_item_pickups(self):
        if not self.player:
            return
        remaining = []
        for item in self.items:
            if distance(item.x, item.y, self.player.x, self.player.y) < item.PICKUP_RADIUS:
                self.collect_item()
            else:
                remaining.append(item)
        self.items = remaining

    def bomb_boss(self, bomb):
        for part in self.boss.parts:
            px, py = self.boss.pos(part)
            if part.alive and distance(bomb.target_x, bomb.target_y, px, py) < part.radius + BOMB_SPLASH:
                part.hp -= 1
                if not part.alive:
                    self.add_score(part.score)
                    self.explosions.append(Explosion(px, py, 34))
                    self.sounds.play("explode")
        if not self.boss.core.alive:
            self.destroy_boss()

    def destroy_boss(self):
        boss = self.boss
        for _ in range(10):
            self.explosions.append(Explosion(boss.x + random.uniform(-90, 90),
                                             boss.y + random.uniform(-55, 55), 46))
        self.sounds.play("boss_down")
        self.items.append(Item(boss.x, boss.y))
        self.boss = None
        self.bullets.clear()
        self.area += 1
        self.area_time = 0.0
        self.banner_timer = 2.0

    def handle_player_hits(self):
        player = self.player
        if not player or player.invulnerable > 0:
            return
        for bullet in self.bullets:
            if distance(bullet.x, bullet.y, player.x, player.y) < bullet.RADIUS + player.RADIUS:
                self.kill_player()
                return
        for enemy in self.air:
            if distance(enemy.x, enemy.y, player.x, player.y) < enemy.radius + player.RADIUS:
                if enemy.destructible:
                    enemy.alive = False
                    self.explosions.append(Explosion(enemy.x, enemy.y))
                self.kill_player()
                return

    def kill_player(self):
        self.explosions.append(Explosion(self.player.x, self.player.y, 44))
        self.player = None
        self.lives -= 1
        self.shot_level = max(0, self.shot_level - 1)
        self.respawn_timer = RESPAWN_DELAY
        self.bullets.clear()
        self.sounds.play("player_down")

    def sight_on_target(self):
        """조준점이 지상 목표 위에 있으면 빨갛게 표시하기 위한 판정."""
        sx, sy = self.player.sight
        for target in self.ground:
            if distance(sx, sy, target.x, target.y) < target.radius + BOMB_SPLASH:
                return True
        if self.boss:
            for part in self.boss.parts:
                px, py = self.boss.pos(part)
                if part.alive and distance(sx, sy, px, py) < part.radius + BOMB_SPLASH:
                    return True
        return False

    def draw_sight(self, screen):
        x, y = (int(v) for v in self.player.sight)
        color = RED if self.sight_on_target() else WHITE
        pygame.draw.rect(screen, color, (x - 11, y - 11, 22, 22), 2)
        pygame.draw.line(screen, color, (x - 16, y), (x - 6, y), 2)
        pygame.draw.line(screen, color, (x + 6, y), (x + 16, y), 2)
        pygame.draw.line(screen, color, (x, y - 16), (x, y - 6), 2)
        pygame.draw.line(screen, color, (x, y + 6), (x, y + 16), 2)

    def draw_text(self, screen, text, font, y, color=WHITE):
        image = font.render(text, True, color)
        shadow = font.render(text, True, BLACK)
        rect = image.get_rect(center=(WIDTH // 2, y))
        screen.blit(shadow, rect.move(2, 2))
        screen.blit(image, rect)

    def draw_hud(self, screen):
        screen.blit(self.font.render(f"SCORE {self.score}", True, WHITE), (10, 8))
        high = self.font.render(f"HIGH {self.high_score}", True, YELLOW)
        screen.blit(high, (WIDTH - high.get_width() - 10, 8))
        for i in range(max(0, self.lives - 1)):
            x, y = 18 + i * 22, HEIGHT - 18
            pygame.draw.polygon(screen, SILVER, [(x, y - 10), (x + 8, y + 7), (x - 8, y + 7)])
        area = self.font.render(f"AREA {self.area}", True, WHITE)
        screen.blit(area, (WIDTH - area.get_width() - 10, HEIGHT - 28))
        shot = self.font.render(f"SHOT x{SHOT_LEVELS[self.shot_level][0]}", True, CYAN)
        screen.blit(shot, shot.get_rect(midbottom=(WIDTH // 2, HEIGHT - 8)))

    def draw(self, screen):
        self.terrain.draw(screen)

        for target in self.ground:
            target.draw(screen)
        if self.boss:
            self.boss.draw(screen)
        for bomb in self.bombs:
            bomb.draw(screen)
        for item in self.items:
            item.draw(screen, self.font)
        for enemy in self.air:
            enemy.draw(screen)
        for shot in self.shots:
            shot.draw(screen)
        blink = int(self.clock_t * 12) % 2 == 0
        for bullet in self.bullets:
            bullet.draw(screen, blink)
        if self.player and self.state != "title":
            self.draw_sight(screen)
            self.player.draw(screen)
        for explosion in self.explosions:
            explosion.draw(screen)

        self.draw_hud(screen)

        if self.state == "title":
            self.draw_text(screen, "XEVIOUS STYLE", self.big_font, 210, YELLOW)
            self.draw_text(screen, "Arrows / WASD : Move", self.font, 300)
            self.draw_text(screen, "Z / Space : Air shot    X : Ground bomb", self.font, 332)
            self.draw_text(screen, "P : Pause    Esc : Quit", self.font, 364)
            self.draw_text(screen, "Press Enter to start", self.font, 430, CYAN)
        elif self.state == "paused":
            self.draw_text(screen, "PAUSED", self.big_font, 280)
        elif self.state == "gameover":
            self.draw_text(screen, "GAME OVER", self.big_font, 260, RED)
            self.draw_text(screen, f"Score {self.score}", self.font, 320)
            self.draw_text(screen, "Press Enter to play again", self.font, 360, CYAN)
        elif self.banner_timer > 0:
            self.draw_text(screen, f"AREA {self.area}", self.big_font, 260, YELLOW)


def read_controls(keys):
    dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
    dy = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w])
    return Controls(dx, dy, keys[pygame.K_z] or keys[pygame.K_SPACE], keys[pygame.K_x])


def main():
    # allowedchanges=0: 장치 형식이 달라도 합성한 소리의 형식 그대로 재생되게 한다
    pygame.mixer.pre_init(SAMPLE_RATE, -16, 1, 512, allowedchanges=0)
    pygame.init()
    pygame.display.set_caption("Xevious Style Shooter")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    game = Game()

    running = True
    while running:
        # 창을 옮기는 동안 시간이 크게 튀어 벽을 뚫는 일을 막는다
        dt = min(clock.tick(FPS) / 1000, 0.05)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_p:
                    game.toggle_pause()
                elif event.key == pygame.K_RETURN and game.state in ("title", "gameover"):
                    game.start()

        game.update(dt, read_controls(pygame.key.get_pressed()))
        game.draw(screen)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
