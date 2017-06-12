# SuMPF - Sound using a Monkeyforest-like processing framework
# Copyright (C) 2012-2017 Jonas Schulte-Coerne
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

from ._interpretations.energydecaycurvefromimpulseresponse import EnergyDecayCurveFromImpulseResponse
from ._interpretations.minmax import SignalMinimum, SignalMaximum

try:
    from ._interpretations.findharmonicimpulseresponse import FindHarmonicImpulseResponse
except ImportError:
    pass

try:
    from ._interpretations.regularizedspectruminversion import RegularizedSpectrumInversion
except ImportError:
    pass

try:
    from ._interpretations.signalenvelope import SignalEnvelope
except ImportError:
    pass

