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

from os import environ

if "SUMPF_DISABLE_CONNECTORS" in environ and environ["SUMPF_DISABLE_CONNECTORS"] in (1, "1", "True", "true", "Yes", "yes", "Y", "y"):
    from ._connectors.dummydecorators import Input, Trigger, MultiInput, Output
else:
    from ._connectors.functions import connect, disconnect, disconnect_all, \
                                       deactivate_output, activate_output, \
                                       destroy_connectors, set_multiple_values
    from ._connectors.decorators import Input, Trigger, MultiInput, Output
    from ._connectors import progressindicators

del environ

