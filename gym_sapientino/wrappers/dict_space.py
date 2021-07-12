# -*- coding: utf-8 -*-
#
# Copyright 2019-2020 Marco Favorito, Luca Iocchi
#
# ------------------------------
#
# This file is part of gym-sapientino.
#
# gym-sapientino is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# gym-sapientino is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with gym-sapientino.  If not, see <https://www.gnu.org/licenses/>.
#

"""Sapientino environments using a "dict" state space."""
import sys

from gym.spaces import Box, Discrete
from gym.spaces import Tuple as GymTuple
from gym.spaces import Dict as GymDict

from gym_sapientino.core.states import SapientinoState
from gym_sapientino.sapientino_env import Sapientino


class SapientinoDictSpace(Sapientino):
    """
    A Sapientino environment with a dictionary state space.

    The components of the space are:
    - Robot x coordinate (Discrete)
    - Robot y coordinate (Discrete)
    - The orientation (Discrete)
    - A boolean to check whether the last action was a beep (Discrete)
    - The color of the current cell (Discrete)
    """

    def __init__(self, *args, **kwargs):
        """Initialize the dictionary space."""
        super().__init__(*args, **kwargs)

        self._discrete_x_space = Discrete(self.configuration.columns)
        self._discrete_y_space = Discrete(self.configuration.rows)
        self._x_space = Box(0.0, self.configuration.columns, shape=[1])
        self._y_space = Box(0.0, self.configuration.rows, shape=[1])
        self._velocity_space = Box(
            -self.configuration.max_velocity, self.configuration.max_velocity, shape=[1]
        )
        self._theta_space = Discrete(self.configuration.nb_theta)
        self._angle_space = Box(0.0, 360.0 - sys.float_info.epsilon, shape=[1])
        self._beep_space = Discrete(2)
        self._color_space = Discrete(self.configuration.nb_colors)

    @property
    def observation_space(self) -> GymTuple:
        """Get the observation space."""

        observation_spaces = [
            GymDict({
                "discrete_x": self._discrete_x_space,
                "discrete_y": self._discrete_y_space,
                "x": self._x_space,
                "y": self._y_space,
                "velocity": self._velocity_space,
                "theta": self._theta_space,
                "angle": self._angle_space,
                "beep": self._beep_space,
                "color": self._color_space,
            })
        ]
        return GymTuple(observation_spaces)

    def observe(self, state: SapientinoState):
        """Observe the state."""
        return state.to_dict()
