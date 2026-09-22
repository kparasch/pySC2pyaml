from typing import Union
import copy

import numpy.typing as npt
from pyaml.control.deviceaccess import DeviceAccess
from pyaml.control.readback_value import Value
import pySC.control_system.client as pySC_client

from pyaml import PyAMLException
from pyaml.validation import DynamicValidation, register_schema

import logging
logger = logging.getLogger(__name__)

@register_schema
class pySCDeviceAccess(DeviceAccess, DynamicValidation):
    def __init__(self,
                 address: str,
                 unit: str = "",
                 writable: bool = True,
                 index: int | None = None):
        super().__init__()

        self._address = address
        self._unit = unit
        self._writable = writable,
        self._index = index

        if index:
            #logger.warning()
            self._writable = False

    def name(self) -> str:
        """Return the name of the variable"""
        return self._address

    def measure_name(self) -> str:
        """Return the short attribute name (last component)."""
        short = self.name.rsplit("/", 1)[1]
        return short

    def set(self, value: float):
        """Write a control system device variable (i.e. a power supply current)"""
        if self._writable:
            pySC_client.write(self._address, value)
        else:
            raise PyAMLException(f'Device {self.name()} at address={self._address} is not writable.')

    def set_and_wait(self, value: float):
        """Write a control system device variable (i.e. a power supply current)"""
        return self.set(value)

    def get(self) -> float:
        """Return the setpoint of a control system device variable"""
        value = pySC_client.read(self._address)
        if self._index is None:
            return value
        else:
            return value[self._index]

    def readback(self) -> Union[Value, npt.NDArray[Value]]:
        """Return the measured variable"""
        return self.get()

    def unit(self) -> str:
        """Return the variable unit"""
        return self._unit

    def clone_with_address(self, address: str) -> "pySCDeviceAccess":
        new_obj = copy.copy(self)
        new_obj._address = address
        return new_obj

    def get_range(self) -> list[float]:
        return [-1e16,1e16]

    def check_device_availability(self) -> bool:
        return True

    def get_index(self) -> int | None:
        return self._index
