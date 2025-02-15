# coding=utf-8
# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

###############################################################################
#
# This is a port of the work by: Krzysztof Choromanski, Mark Rowland,
# Vikas Sindhwani, Richard E. Turner, Adrian Weller:  "Structured Evolution
# with Compact Architectures for Scalable Policy Optimization",
# https://arxiv.org/abs/1804.02395
#
###############################################################################
r"""Library of gradient ascent algorithms.

Library of stateful gradient ascent algorithms taking as input the gradient and
current parameters, and output the new parameters.
"""

import abc
import numpy as np


# TODO(kchoro): Borrow JAXs optimizer library here. Integrated into Blackbox-v2.
class GradientAscentOptimizer(metaclass=abc.ABCMeta):
  """Abstract class for general gradient ascent optimizers.

  Class is responsible for encoding different gradient ascent optimization
  techniques.
  """

  @abc.abstractmethod
  def run_step(self, current_input, gradient):
    """Conducts a single step of gradient ascent optimization.

    Conduct a single step of gradient ascent optimization procedure, given the
    current parameters and the raw gradient.

    Args:
      current_input: the current parameters.
      gradient: the raw gradient.

    Returns:
      New parameters by conducting a single step of gradient ascent.
    """
    raise NotImplementedError("Abstract method")

  @abc.abstractmethod
  def get_state(self):
    """Returns the state of the optimizer.

    Returns the state of the optimizer.

    Args:

    Returns:
      The state of the optimizer.
    """
    raise NotImplementedError("Abstract method")

  @abc.abstractmethod
  def set_state(self, state):
    """Sets up the internal state of the optimizer.

    Sets up the internal state of the optimizer.

    Args:
      state: state to be set up

    Returns:
    """
    raise NotImplementedError("Abstract method")


class MomentumOptimizer(GradientAscentOptimizer):
  """Class implementing momentum gradient ascent optimizer.

  Setting momentum coefficient to zero is equivalent to vanilla gradient
  ascent.

  the state is the moving average as a list
  """

  def __init__(self, step_size, momentum):
    self.step_size = step_size
    self.momentum = momentum

    self.moving_average = np.asarray([], dtype=np.float32)
    super().__init__()

  def run_step(self, current_input, gradient):
    if self.moving_average.size == 0:
      # Initialize the moving average
      self.moving_average = np.zeros(len(current_input), dtype=np.float32)
    elif len(self.moving_average) != len(current_input):
      raise ValueError(
          "Dimensions of the parameters and moving average do not match")

    if not isinstance(gradient, np.ndarray):
      gradient = np.asarray(gradient, dtype=np.float32)

    self.moving_average = self.momentum * self.moving_average + (
        1 - self.momentum) * gradient
    step = self.step_size * self.moving_average

    return current_input + step

  def get_state(self):
    return self.moving_average.tolist()

  def set_state(self, state):
    self.moving_average = np.asarray(state, dtype=np.float32)


class AdamOptimizer(GradientAscentOptimizer):
  """Class implementing ADAM gradient ascent optimizer.
  
  The state is the first moment moving average, the second moment moving average, 
  and t (current step number) combined in that order into one list
  """

  def __init__(self, step_size, beta1=0.9, beta2=0.999, epsilon=1e-07):
    self.step_size = step_size
    self.beta1 = beta1
    self.beta2 = beta2
    self.epsilon = epsilon

    self.first_moment_moving_average = np.asarray([], dtype=np.float32)
    self.second_moment_moving_average = np.asarray([], dtype=np.float32)
    self.t = 0
    super().__init__()

  def run_step(self, current_input, gradient):
    if self.first_moment_moving_average.size == 0:
      # Initialize the moving averages
      self.first_moment_moving_average = np.zeros(
          len(current_input), dtype=np.float32)
      self.second_moment_moving_average = np.zeros(
          len(current_input), dtype=np.float32)
      # Initialize the step counter
      self.t = 0
    elif len(self.first_moment_moving_average) != len(current_input):
      raise ValueError(
          "Dimensions of the parameters and moving averages do not match")

    if not isinstance(gradient, np.ndarray):
      gradient = np.asarray(gradient, dtype=np.float32)

    self.first_moment_moving_average = (
        self.beta1 * self.first_moment_moving_average +
        (1 - self.beta1) * gradient)
    self.second_moment_moving_average = (
        self.beta2 * self.second_moment_moving_average + (1 - self.beta2) *
        (gradient * gradient))

    self.t += 1
    scale = np.sqrt(1 - self.beta2**self.t) / (1 - self.beta1**self.t)

    step = self.step_size * scale * self.first_moment_moving_average / (
        np.sqrt(self.second_moment_moving_average) + self.epsilon)

    return current_input + step

  def get_state(self):
    return (self.first_moment_moving_average.tolist() +
            self.second_moment_moving_average.tolist() + [self.t])

  def set_state(self, state):
    total_len = len(state)
    if total_len % 2 != 1:
      raise ValueError("The dimension of the state should be odd")
    dim = total_len // 2

    self.first_moment_moving_average = np.asarray(state[:dim], dtype=np.float32)
    self.second_moment_moving_average = np.asarray(
        state[dim:2 * dim], dtype=np.float32)
    self.t = int(state[-1])
    if self.t < 0:
      raise ValueError("The step counter should be non-negative")
