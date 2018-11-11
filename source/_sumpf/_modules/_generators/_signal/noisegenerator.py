# SuMPF - Sound using a Monkeyforest-like processing framework
# Copyright (C) 2012-2018 Jonas Schulte-Coerne
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
import random
import numpy

import sumpf

from .signalgenerator import SignalGenerator


class Distribution(object):
    """
    An abstract base class to define probability distributions for the NoiseGenerator.
    Derived classes have to implement the GetSamples method. Implementing a constructor
    is optional to store parameters for the probability distribution.
    """
    def SetRandom(self, random_instance):
        """
        Stores an instance of random.Random.
        The instance is set by the NoiseGenerator.
        @param random_instance: an instance of random.Random
        """
        self._random = random_instance

    def GetSamples(self, length):
        """
        This method shall generate and return a tuple of random samples. The
        generated samples shall be distributed by the respective distribution
        function.
        @param length: the length of the random sequence
        @retval : a random float sample
        """
        raise NotImplementedError("This method should have been overridden in a derived class")



class NoiseGenerator(SignalGenerator):
    """
    A module that generates a Signal with random samples.
    As the samples are random, they are not necessarily in the interval between
    -1.0 and 1.0. So make sure to scale the output Signal properly before feeding
    it to the sound card.

    By default this module generates white noise. If you want to select another
    distribution, pass an instance of a subclass of Distribution (e.g.
    NoiseGenerator.PinkNoise or NoiseGenerator.UniformDistribution) to the noise
    generator via either the constructor or the SetDistribution method.
    Some subclasses may take constructor arguments to define their probability
    distributions.

    The GetSignal method of this class might cache the resulting noise Signal.
    If caching is enabled, calling GetSignal multiple times will always return
    the same Signal, because GetSignal calculates the Signal once and the only
    returns the cached value. Call Recalculate or one of the setter methods to
    trigger the calculation of a new noise Signal.
    If caching is disabled, each call of GetSignal will return a newly calculated
    noise Signal.

    The resulting Signal will have one channel.
    """
    def __init__(self, distribution=None, seed=None, samplingrate=None, length=None):
        """
        @param distribution: a Distribution instance
        @param seed: a seed for the random.Random instance
        @param samplingrate: the sampling rate in Hz
        @param length: the number of samples of the signal
        """
        SignalGenerator.__init__(self, samplingrate=samplingrate, length=length)
        self.__distribution = distribution
        self.__random = random.Random()
        if seed is None:
            self.__random.seed()
        else:
            self.__random.seed(seed)
        if self.__distribution is None:
            self.__distribution = type(self).WhiteNoise()
        self.__distribution.SetRandom(self.__random)

    @sumpf.Input(Distribution, "GetSignal")
    def SetDistribution(self, distribution):
        """
        Sets the function that defines the probability distribution of the
        generated samples.
        @param distribution: a Distribution instance
        """
        self.__distribution = distribution
        self.__distribution.SetRandom(self.__random)

    @sumpf.Input(None, "GetSignal")
    def Seed(self, seed):
        """
        Seeds the random number generator with a defined seed.
        @param seed: the seed for the random number generator. This can be any hashable object
        """
        self.__random.seed(seed)

    @sumpf.Trigger("GetSignal")
    def Recalculate(self):
        """
        A Trigger, that triggers the recalculation of the random sequence, so that
        a new Signal is created, even when the caching of the GetSignal-connector
        is enabled.
        """
        pass

    def _GetSamples(self):
        """
        Generates the samples of the random Signal and returns them as a tuple.
        @retval : a tuple of samples
        """
        return self.__distribution.GetSamples(self._length)

    def _GetLabel(self):
        """
        Returns the label for the generated channel.
        @retval : the string label
        """
        if isinstance(self.__distribution, NoiseGenerator.WhiteNoise):
            return "White Noise"
        elif isinstance(self.__distribution, NoiseGenerator.PinkNoise):
            return "Pink Noise"
        elif isinstance(self.__distribution, NoiseGenerator.RedNoise):
            return "Red Noise"
        else:
            return "Noise"

    class WhiteNoise(Distribution):
        """
        Generates the samples for white noise.
        """
        STANDARD_NORMAL = 0
        UNIFORM = 1
        SHAPIRO_RUDIN = 2
        NEWMAN = 3
        def __init__(self, remove_dc=True, phase_distribution=STANDARD_NORMAL):
            self.__remove_dc = remove_dc
            self.__phase_distribution = phase_distribution

        def GetSamples(self, length):
            flength = length // 2 + 1
            if self.__phase_distribution == NoiseGenerator.WhiteNoise.STANDARD_NORMAL:
                fsamples = numpy.exp([2.0j * math.pi * self._random.gauss(0.0, 1.0) for _ in range(flength)])
            elif self.__phase_distribution == NoiseGenerator.WhiteNoise.UNIFORM:
                fsamples = numpy.exp([2.0j * math.pi * self._random.random() for _ in range(flength)])
            elif self.__phase_distribution == NoiseGenerator.WhiteNoise.SHAPIRO_RUDIN:
                fsamples = numpy.empty(flength)
                fsamples[0:2] = (1.0, 1.0)
                i = 2
                while i < flength:
                    try:
                        fsamples[i:i + i // 2] = fsamples[0:i // 2]
                    except ValueError:
                        j = min(i // 2, flength - i)
                        fsamples[i:i + j] = fsamples[0:j]
                        break
                    try:
                        fsamples[i + i // 2:2 * i] = -fsamples[i // 2:i]
                    except ValueError:
                        j = flength - i
                        fsamples[i + i // 2:i + j] = -fsamples[i // 2:j]
                    i *= 2
            elif self.__phase_distribution == NoiseGenerator.WhiteNoise.NEWMAN:
                fsamples = numpy.exp([(-1.0j * math.pi * i ** 2) / flength for i in range(flength)])
            else:
                raise ValueError("Unknown phase distribution: %i" % self.__phase_distribution)
            fsamples *= 2.0 ** (0.5 * math.log(flength, 2.0) - 1.0) * 2.0 ** 0.5
            if self.__remove_dc:
                fsamples[0] = 0.0
            samples = numpy.fft.irfft(fsamples)
            return tuple(samples)

    class PinkNoise(Distribution):
        """
        Generates the samples for pink noise. p ~ (1/f)
        """
        def GetSamples(self, length):
            fsamples = [0.0]    # first fft-sample is 0.0 to avoid a dc offset
            factor = 2.0 ** (0.899 * math.log(length, 2.0) - 1.0) * 0.8
            for i in range(1, length // 2 + 1):
                fsamples.append(factor / (i ** 0.5) * numpy.exp(2.0j * math.pi * self._random.gauss(0.0, 1.0)))
            samples = numpy.fft.irfft(fsamples)
            return tuple(samples)

    class RedNoise(Distribution):
        """
        Generates the samples for red noise. p ~ (1/f^2)
        """
        def GetSamples(self, length):
            fsamples = [0.0]    # first fft-sample is 0.0 to avoid a dc offset
            factor = 2.0 ** (math.log(length, 2.0) - 1.0) * 0.8
            for i in range(1, length // 2 + 1):
                fsamples.append(factor / i * numpy.exp(2.0j * math.pi * self._random.gauss(0.0, 1.0)))
            samples = numpy.fft.irfft(fsamples)
            return tuple(samples)

    class UniformDistribution(Distribution):
        """
        Generates samples that are uniformly distributed between the given
        minimum and maximum.
        """
        def __init__(self, minimum=-1.0, maximum=1.0):
            self.__minimum = float(minimum)
            self.__maximum = float(maximum)
        def GetSamples(self, length):
            result = []
            for i in range(length):
                result.append(self._random.uniform(self.__minimum, self.__maximum))
            return result

    class GaussianDistribution(Distribution):
        """
        Generates samples that are gaussianly distributed with the given mean
        and standard deviation.
        """
        def __init__(self, mean=0.0, standard_deviation=1.0):
            self.__mean = float(mean)
            self.__standard_deviation = float(standard_deviation)
        def GetSamples(self, length):
            result = []
            for i in range(length):
                result.append(self._random.gauss(self.__mean, self.__standard_deviation))
            return result

