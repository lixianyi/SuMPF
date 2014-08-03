# SuMPF - Sound using a Monkeyforest-like processing framework
# Copyright (C) 2012-2014 Jonas Schulte-Coerne
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import math
import sumpf
from .auralization_base import ThieleSmallParameterAuralization


class ThieleSmallParameterAuralizationNonlinear(ThieleSmallParameterAuralization):
	"""
	Synthesizes loudspeaker responses for a given input voltage signal.
	These responses can be the membrane displacement, the membrane velocity, the
	membrane acceleration, the input current and the generated sound pressure
	at a given distance.

	This synthesis also simulates nonlinear effects, which are caused by loudspeaker
	parameters that change with the membrane displacement or the membrane velocity.
	Frequency or temperature dependencies of parameters are not considered in
	this simulation.

	The simulation is implemented as an IIR-filter in the z-domain, that updates
	the displacement and velocity dependent parameters for each sample with the
	displacement and velocity that has been calculated for the previous sample.

	The formula for the IIR-filter has been calculated by using the bilinear transform
	on the voltage-to-displacement transfer function in the Laplace domain. Due
	to the non-infinite sampling rate, this causes an error in the high frequencies
	of the output signals. Specifying a "warp frequency" for the Filter minimizes
	the error at that frequency, but this increases the errors at other frequencies.
	"""
	def __init__(self, thiele_small_parameters=sumpf.ThieleSmallParameters(), voltage_signal=None, listener_distance=1.0, medium_density=1.2041, warp_frequency=0.0, regularization=0.0):
		"""
		@param thiele_small_parameters: a ThieleSmallParameters instance
		@param voltage_signal: a signal for the input voltage of the loudspeaker
		@param listener_distance: a float value for the distance between the loudspeaker and the point where the radiated sound is received in meters
		@param medium_density: a float value for the density of the medium, in which the loudspeaker radiates sound (probably air) in kilograms per cubic meter
		@param warp_frequency: a frequency in Hz, at which the error, that is caused by the bilinear transform, shall be minimized
		@param regularization: a small float < 1.0 that ensures the stability of the bilinear transform
		"""
		ThieleSmallParameterAuralization.__init__(self, thiele_small_parameters=thiele_small_parameters, voltage_signal=voltage_signal, listener_distance=listener_distance, medium_density=medium_density)
		self.__warp_frequency = warp_frequency
		self.__regularization = regularization

	@sumpf.Input(float, ("GetDisplacement", "GetVelocity", "GetAcceleration", "GetCurrent", "GetSoundPressure"))
	def SetWarpFrequency(self, frequency):
		"""
		Sets a frequency, at which the error, that is caused by the bilinear
		transform, shall be minimized.
		This increases the error at frequencies, that are not near the warp frequency.
		Setting the warp frequency to a high frequency, where the errors of the
		bilinear transform are especially high, causes a significant increase in
		the overall simulation error, so low warp frequencies (e.g. the resonance
		frequency of the simulated loudspeaker) are recommended.
		@param warp_frequency: a frequency in Hz as a float
		"""
		self.__warp_frequency = frequency
		self._recalculate = True

	@sumpf.Input(float, ("GetDisplacement", "GetVelocity", "GetAcceleration", "GetCurrent", "GetSoundPressure"))
	def SetRegularization(self, value):
		"""
		Sets a regularization value, that ensures the stability of the bilinear
		transform.
		The bilinear transform has a pole at z=-1, which is on the unit circle and
		means that the resulting filter is not stable. The regularization value
		shifts the pole to z=-1+q to get a stable filter. The formula for the
		bilinear transform with regularization is:
			s = K * (z-1) / (z+1-q)
		It is recommended, to use a small regularization value, as larger values
		increase the simulation error.
		@param regularization: a small float < 1.0
		"""
		self.__regularization, value
		self._recalculate = True

	def _Recalculate(self):
		"""
		Calculates the channels for the displacement, velocity and acceleration
		of the membrane and for the input current and the generated sound pressure.
		@retval the channel data displacement_channels, velocity_channels, acceleration_channels, current_channels, sound_pressure_channels
		"""
		# make class variables local
		thiele_small = self._thiele_small
		r = self._listener_distance
		rho = self._medium_density
		# precalculate necessary values
		length = len(self._voltage.GetChannels()[0]) + 3
		K = 2.0 * self._voltage.GetSamplingRate()
		if self.__warp_frequency != 0.0:
			K = 2.0 * math.pi * self.__warp_frequency / math.tan(2.0 * math.pi * self.__warp_frequency / K)
		q = 1.0 - self.__regularization
		_4pi = 4.0 * math.pi
		_3q = 3.0 * q					# a1
		_3q2 = 3.0 * q ** 2				# a2
		_q3 = q ** 3					# a3
		_K3 = K ** 3					# b0
		_K2 = K ** 2
		_3K3 = 3.0 * _K3				# b1
		_K2q2 = _K2 * (q - 2.0)
		_K2q1 = K * (2.0 * q - 1.0)
		_K212q = _K2 * (1.0 - 2.0 * q)	# b2
		_Kqq2 = K * q * (q - 2.0)
		_K2q = K ** 2 * q				# b3
		_Kq2 = K * q ** 2
		# start the calculation
		displacement_channels = []
		velocity_channels = []
		acceleration_channels = []
		current_channels = []
		sound_pressure_channels = []
		f = 0.0
		t = None
		for channel in self._voltage.GetChannels():
			voltage = (0.0,) * 3 + channel
			displacement = [0.0] * length
			velocity = [0.0] * length
			acceleration = [0.0] * length
			current = [0.0] * length
			sound_pressure = [0.0] * length
			for i in range(4, len(voltage)):
				x = displacement[i - 1]
				v = velocity[i - 1]
				# get the Thiele Small parameters
				R = thiele_small.GetVoiceCoilResistance(f, x, v, t)
				L = thiele_small.GetVoiceCoilInductance(f, x, v, t)
				M = thiele_small.GetForceFactor(f, x, v, t)
				k = thiele_small.GetSuspensionStiffness(f, x, v, t)
				w = thiele_small.GetMechanicalDamping(f, x, v, t)
				m = thiele_small.GetMembraneMass(f, x, v, t)
				S = thiele_small.GetMembraneArea(f, x, v, t)
				# precalculate some values for the displacement calculation
				Lm = L * m
				LwRm = L * w + R * m
				LkM2Rw = L * k + M * M + R * w
				Rk = R * k
				# calculate the filter coefficients for the displacement calculation
				a0 = M
				a1 = M * _3q
				a2 = M * _3q2
				a3 = M * _q3
				b0 = Lm * _K3 + LwRm * _K2 + LkM2Rw * K + Rk
				b1 = -Lm * _3K3 + LwRm * _K2q2 + LkM2Rw * _K2q1 + Rk * _3q
				b2 = Lm * _3K3 + LwRm * _K212q + LkM2Rw * _Kqq2 + Rk * _3q2
				b3 = -Lm * _K3 + LwRm * _K2q - LkM2Rw * _Kq2 + Rk * _q3
				summed = a0 * voltage[i] + a1 * voltage[i - 1] + a2 * voltage[i - 2] + a3 * voltage[i - 3] - b1 * displacement[i - 1] - b2 * displacement[i - 2] - b3 * displacement[i - 3]
				displacement[i] = summed / b0
				# calculate the velocity, the acceleration, the current and the sound pressure
				velocity[i] = K * (displacement[i] - displacement[i - 1]) - q * velocity[i - 1]
				acceleration[i] = K * (velocity[i] - velocity[i - 1]) - q * acceleration[i - 1]
				current[i] = (k * displacement[i] + w * velocity[i] + m * acceleration[i]) / M
				sound_pressure[i] = (rho * acceleration[i] * S) / (_4pi * r)
			# store the Signals
			displacement_channels.append(tuple(displacement[3:]))
			velocity_channels.append(tuple(velocity[3:]))
			acceleration_channels.append(tuple(acceleration[3:]))
			current_channels.append(tuple(current[3:]))
			sound_pressure_channels.append(tuple(sound_pressure[3:]))
		return displacement_channels, velocity_channels, acceleration_channels, current_channels, sound_pressure_channels

