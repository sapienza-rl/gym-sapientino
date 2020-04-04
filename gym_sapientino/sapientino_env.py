# -*- coding: utf-8 -*-

"""
Sapientino environment with OpenAI Gym interface

Luca Iocchi 2017
"""
import itertools
from abc import ABC, abstractmethod
from collections import defaultdict
from enum import Enum
from typing import Optional, Tuple, Dict, Union, List

import gym as gym
import pygame
from gym.spaces import Discrete, MultiDiscrete
from numpy import clip

black = [0, 0, 0]
white = [255, 255, 255]
grey = [180, 180, 180]
orange = [180, 100, 20]
red = [180, 0, 0]


class Colors(Enum):
    BLANK = "blank"
    RED = "red"
    GREEN = "green"
    BLUE = "blue"
    PINK = "pink"
    BROWN = "brown"
    GRAY = "gray"
    PURPLE = "purple"

    def __str__(self):
        return self.value

    def __int__(self):
        return color2int[self]

color2int = dict(map(reversed, enumerate(Colors)))

TOKENS = [
    ['r1', Colors.RED.value, 0, 0],
    ['r2', Colors.RED.value, 1, 1],
    ['r3', Colors.RED.value, 6, 3],
    ['g1', Colors.GREEN.value, 4, 0],
    ['g2', Colors.GREEN.value, 5, 2],
    ['g3', Colors.GREEN.value, 5, 4],
    ['b1', Colors.BLUE.value, 1, 3],
    ['b2', Colors.BLUE.value, 2, 4],
    ['b3', Colors.BLUE.value, 6, 0],
    ['p1', Colors.PINK.value, 2, 1],
    ['p2', Colors.PINK.value, 2, 3],
    ['p3', Colors.PINK.value, 4, 2],
    ['n1', Colors.BROWN.value, 3, 0],
    ['n2', Colors.BROWN.value, 3, 4],
    ['n3', Colors.BROWN.value, 6, 1],
    ['y1', Colors.GRAY.value, 0, 2],
    ['y2', Colors.GRAY.value, 3, 1],
    ['y3', Colors.GRAY.value, 4, 3],
    ['u1', Colors.PURPLE.value, 0, 4],
    ['u2', Colors.PURPLE.value, 1, 0],
    ['u3', Colors.PURPLE.value, 5, 1]
]


class Direction:

    NB_DIRECTIONS = 4

    def __init__(self, th: int = 90):
        self.th = th

    def rotate_left(self) -> 'Direction':
        th = (self.th + 90) % 360
        return Direction(th)

    def rotate_right(self) -> 'Direction':
        th = (self.th - 90) % 360
        if th == -90: th = 270
        return Direction(th)


class State(ABC):
    pass


class PygameDrawable(ABC):

    @abstractmethod
    def draw_on_screen(self, screen: pygame.Surface):
        """Draw a Pygame object on a given Pygame screen."""


class _AbstractPygameViewer(ABC):

    @abstractmethod
    def reset(self, state: 'State'):
        pass

    @abstractmethod
    def render(self):
        pass

    @abstractmethod
    def close(self):
        pass


class PygameViewer(_AbstractPygameViewer):

    def __init__(self, state: 'SapientinoState'):
        self.state = state

        pygame.init()
        pygame.display.set_caption('Breakout')
        self.screen = pygame.display.set_mode([self.state.config.win_width, self.state.config.win_height])
        self.myfont = pygame.font.SysFont("Arial", 30)
        self.drawables = self._init_drawables()  # type: List[PygameDrawable]

    def reset(self, state: 'State'):
        self.state = state
        self.drawables = self._init_drawables()

    def _init_drawables(self) -> List[PygameDrawable]:
        result = list()
        result.append(self.state.grid)
        result.append(self.state.robot)
        return result

    def render(self, mode="human"):
        self._fill_screen()
        self._draw_score_label()
        self._draw_last_command()
        self._draw_game_objects()

        if mode == "human":
            pygame.display.update()
        elif mode == "rgb_array":
            screen = pygame.surfarray.array3d(self.screen)
            # swap width with height
            return screen.swapaxes(0, 1)

    def _fill_screen(self):
        self.screen.fill(white)

    def _draw_score_label(self):
        score_label = self.myfont.render(str(self.state.score), 100, pygame.color.THECOLORS['black'])
        self.screen.blit(score_label, (20, 10))

    def _draw_last_command(self):
        cmd = self.state.last_command
        s = '%s' % cmd if cmd else ""
        count_label = self.myfont.render(s, 100, pygame.color.THECOLORS['brown'])
        self.screen.blit(count_label, (60, 10))

    def _draw_game_objects(self):
        for d in self.drawables:
            d.draw_on_screen(self.screen)

    def close(self):
        pygame.display.quit()
        pygame.quit()


class NormalCommand(Enum):
    LEFT = 0
    UP = 1
    RIGHT = 2
    DOWN = 3
    BEEP = 4
    NOP = 5

    def __str__(self):
        cmd = NormalCommand(self.value)
        if cmd == NormalCommand.LEFT:
            return "<"
        elif cmd == NormalCommand.RIGHT:
            return ">"
        elif cmd == NormalCommand.UP:
            return "^"
        elif cmd == NormalCommand.DOWN:
            return "v"
        elif cmd == NormalCommand.BEEP:
            return "o"
        elif cmd == NormalCommand.NOP:
            return "_"
        else:
            raise ValueError("Shouldn't be here...")


class DifferentialCommand(Enum):
    LEFT = 0
    FORWARD = 1
    RIGHT = 2
    BACKWARD = 3
    BEEP = 4
    NOP = 5

    def __str__(self):
        cmd = DifferentialCommand(self.value)
        if cmd == DifferentialCommand.LEFT:
            return "<"
        elif cmd == DifferentialCommand.RIGHT:
            return ">"
        elif cmd == DifferentialCommand.FORWARD:
            return "^"
        elif cmd == DifferentialCommand.BACKWARD:
            return "v"
        elif cmd == DifferentialCommand.BEEP:
            return "o"
        elif cmd == DifferentialCommand.NOP:
            return "_"
        else:
            raise ValueError("Shouldn't be here...")


class SapientinoConfiguration:

    def __init__(self, rows: int = 5,
                 columns: int = 7,
                 differential: bool = False,
                 horizon: Optional[int] = None,
                 reward_outside_grid: float = -1.0,
                 reward_duplicate_beep: float = -1.0,
                 reward_per_step: float = -0.01):

        self.rows = rows
        self.columns = columns
        self.differential = differential
        self._horizon = horizon if horizon else (self.columns * self.rows) * 10
        self.reward_outside_grid = reward_outside_grid
        self.reward_duplicate_beep = reward_duplicate_beep
        self.reward_per_step = reward_per_step

        self.offx = 40
        self.offy = 100
        self.radius = 5
        self.size_square = 40

    @property
    def win_width(self):
        if self.columns > 10:
            return self.size_square * (self.columns - 10)
        else:
            return 480

    @property
    def win_height(self):
        if self.rows > 10:
            return self.size_square * (self.rows-10)
        else:
            return 520

    @property
    def action_space(self):
        if self.differential:
            return Discrete(len(DifferentialCommand))
        else:
            return Discrete(len(NormalCommand))

    @property
    def observation_space(self):
        if self.differential:
            # 4 is the number of possible direction - nord, sud, west, east
            return MultiDiscrete((self.columns, self.rows, Direction.NB_DIRECTIONS))
        else:
            return MultiDiscrete((self.columns, self.rows))

    def get_action(self, action: int) -> Union[DifferentialCommand, NormalCommand]:
        if self.differential:
            return DifferentialCommand(action)
        else:
            return NormalCommand(action)

    @property
    def horizon(self):
        return self._horizon

    @property
    def nb_theta(self):
        return Direction.NB_DIRECTIONS

    @property
    def nb_colors(self):
        return len(color2int)

class Robot(PygameDrawable):

    def __init__(self, config: SapientinoConfiguration):
        self.config = config

        self._initial_x = 3
        self._initial_y = 2
        self._initial_th = 90

        self.x = self._initial_x
        self.y = self._initial_y
        self.direction = Direction(self._initial_th)

    @property
    def position(self) -> Tuple[int, int]:
        return (self.x, self.y)

    def reset(self):
        self.x = self._initial_x
        self.y = self._initial_y
        self.direction = Direction(self._initial_th)

    def draw_on_screen(self, screen: pygame.Surface):
        dx = int(self.config.offx + self.x * self.config.size_square)
        dy = int(self.config.offy + (self.config.rows - self.y - 1) * self.config.size_square)
        pygame.draw.circle(screen, pygame.color.THECOLORS['orange'],
                           [dx + self.config.size_square // 2, dy + self.config.size_square // 2],
                           2 * self.config.radius, 0)
        ox = 0
        oy = 0
        if self.direction.th == 0:  # right
            ox = self.config.radius
        elif self.direction.th == 90:  # up
            oy = -self.config.radius
        elif self.direction.th == 180:  # left
            ox = -self.config.radius
        elif self.direction.th == 270:  # down
            oy = self.config.radius

        pygame.draw.circle(screen, pygame.color.THECOLORS['black'],
                           [dx + self.config.size_square // 2 + ox, dy + self.config.size_square // 2 + oy], 5, 0)

    def step(self, command: Union[DifferentialCommand, NormalCommand]):
        if isinstance(command, NormalCommand):
            if command == command.DOWN: self.y -= 1
            elif command == command.UP: self.y += 1
            elif command == command.RIGHT: self.x += 1
            elif command == command.LEFT: self.x -= 1
        elif isinstance(command, DifferentialCommand):
            dx = 1 if self.direction.th == 0 else -1 if self.direction.th == 180 else 0
            dy = 1 if self.direction.th == 90 else -1 if self.direction.th == 270 else 0
            if command == command.LEFT: self.direction = self.direction.rotate_left()
            elif command == command.RIGHT: self.direction = self.direction.rotate_right()
            elif command == command.FORWARD:
                self.x += dx
                self.y += dy
            elif command == command.BACKWARD:
                self.x -= dx
                self.y -= dy
        else:
            raise ValueError("Command not recognized.")

    @property
    def encoded_theta(self):
        return self.direction.th // 90


class Cell:

    def __init__(self, config: SapientinoConfiguration, x: int, y: int, color: Colors):
        self.config = config
        self.x = x
        self.y = y
        self.color = color
        self.bip_count = 0

    def reset(self):
        self.bip_count = 0

    @property
    def encoded_color(self):
        return color2int[self.color]
    
    def beep(self):
        self.bip_count += 1

    def draw_on_screen(self, screen):
        dx = int(self.config.offx + self.x * self.config.size_square)
        dy = int(self.config.offy + (self.config.rows - self.y - 1) * self.config.size_square)
        sqsz = (dx + 5, dy + 5, self.config.size_square - 10, self.config.size_square - 10)
        pygame.draw.rect(screen, pygame.color.THECOLORS[str(self.color)], sqsz)
        if self.bip_count >= 1:
            pygame.draw.rect(screen, pygame.color.THECOLORS['black'],
                             (dx + 15, dy + 15, self.config.size_square - 30, self.config.size_square - 30))


class BlankCell(Cell):

    def __init__(self, config: SapientinoConfiguration, x: int, y: int):
        super().__init__(config, x, y, Colors.BLANK)

    def draw_on_screen(self, screen):
        pass


class SapientinoGrid(PygameDrawable):

    def __init__(self, config: SapientinoConfiguration):
        self.config = config

        self.rows = config.rows
        self.columns = config.columns

        self.cells = {}  # type: Dict[Tuple[int, int], Cell]
        self.color_count = defaultdict(lambda: 0)  # type: Dict[Colors, int]

        self._populate_token_grid()

    def _populate_token_grid(self):
        # add color cells
        for t in TOKENS:
            x, y = t[2], t[3]
            color = t[1]
            color_cell = Cell(self.config, x, y, Colors(color))
            self.cells[(x, y)] = color_cell

        # add blank cells
        for x, y in itertools.product(range(self.config.columns), range(self.config.rows)):
            if (x, y) not in self.cells:
                self.cells[(x, y)] = BlankCell(self.config, x, y)

    def reset(self):
        for t in self.cells.values():
            t.reset()

    def draw_on_screen(self, screen: pygame.Surface):
        for i in range(0, self.columns + 1):
            ox = self.config.offx + i*self.config.size_square
            pygame.draw.line(screen,
                             pygame.color.THECOLORS['black'],
                             [ox, self.config.offy],
                             [ox, self.config.offy + self.rows * self.config.size_square])

        for i in range (0, self.rows + 1):
            oy = self.config.offy + i * self.config.size_square
            pygame.draw.line(screen,
                             pygame.color.THECOLORS['black'],
                             [self.config.offx, oy],
                             [self.config.offx + self.columns * self.config.size_square, oy])

        for cell in self.cells.values():
            cell.draw_on_screen(screen)


class SapientinoState(State):

    def __init__(self, config: SapientinoConfiguration):
        self.config = config

        self.score = 0
        self.grid = SapientinoGrid(config)
        self.robot = Robot(config)

        self.last_command = NormalCommand.NOP if config.differential else DifferentialCommand.NOP
        self._steps = 0

    def step(self, command: Union[DifferentialCommand, NormalCommand]) -> float:
        reward = 0.0
        self._steps += 1

        self.robot.step(command)
        self.last_command = command

        if not (0 <= self.robot.x < self.config.columns):
            reward += self.config.reward_outside_grid
            self.robot.x = int(clip(self.robot.x, 0, self.config.columns - 1))
        if not (0 <= self.robot.y < self.config.rows):
            reward += self.config.reward_outside_grid
            self.robot.y = int(clip(self.robot.y, 0, self.config.rows - 1))

        if command == command.BEEP:
            position = self.robot.x, self.robot.y
            cell = self.grid.cells[position]
            cell.beep()
            if cell.color != Colors.BLANK:
                self.grid.color_count[cell.color] += 1
            if cell.bip_count >= 2:
                reward += self.config.reward_duplicate_beep

        reward += self.config.reward_per_step
        return reward

    def reset(self) -> 'SapientinoState':
        return SapientinoState(self.config)

    @property
    def last_command_beep(self) -> bool:
        return self.last_command.value == 4

    def to_dict(self) -> dict:
        return {
            "x": self.robot.x,
            "y": self.robot.y,
            "theta": self.robot.encoded_theta,
            "beep": int(self.last_command_beep),  # 0 or 1
            "color": self.current_cell.encoded_color
        }

    @property
    def current_cell(self) -> Cell:
        return self.grid.cells[self.robot.position]

    def is_finished(self) -> bool:
        end = self._steps > self.config.horizon
        return end


class Sapientino(gym.Env, ABC):

    metadata = {'render.modes': ['human', 'rgb_array']}

    def __init__(self, configuration: Optional[SapientinoConfiguration] = None):
        self.configuration = configuration if configuration is not None else SapientinoConfiguration()
        self.state = SapientinoState(self.configuration)
        self.viewer = None  # type: Optional[PygameViewer]

    @property
    def action_space(self):
        return self.configuration.action_space

    @property
    def observation_space(self):
        return self.configuration.action_space

    def step(self, action: int):
        command = self.configuration.get_action(action)
        reward = self.state.step(command)
        obs = self.observe(self.state)
        is_finished = self.state.is_finished()
        info = {}
        return obs, reward, is_finished, info

    def reset(self):
        self.state = SapientinoState(self.configuration)
        if self.viewer is not None:
            self.viewer.reset(self.state)
        return self.observe(self.state)

    def render(self, mode='human'):
        if self.viewer is None:
            self.viewer = PygameViewer(self.state)

        return self.viewer.render(mode=mode)

    def close(self):
        if self.viewer is not None:
            self.viewer.close()

    @abstractmethod
    def observe(self, state: SapientinoState) -> gym.Space:
        """
        Extract observation from the state of the game.
        :param state: the state of the game
        :return: an instance of a gym.Space
        """

    def play(self):
        print("Press 'Q' to quit.")
        self.reset()
        self.render()
        quitted = False
        while not quitted:
            event = pygame.event.wait()
            cmd = 5
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    quitted = True
                elif event.key == pygame.K_LEFT:
                    cmd = 0
                elif event.key == pygame.K_UP:
                    cmd = 1
                elif event.key == pygame.K_RIGHT:
                    cmd = 2
                elif event.key == pygame.K_DOWN:
                    cmd = 3
                elif event.key == pygame.K_SPACE:
                    cmd = 4

                self.step(cmd)
                self.render()
