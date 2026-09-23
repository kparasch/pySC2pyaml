"""Expose pySC client reads and writes through the PyAML device access interface."""
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
    """Access a pySC attribute, optionally selecting an element when reading arrays.

    Parameters
    ----------
    address : str
        Attribute address. Client operations require an endpoint-prefixed
        address; a control system can attach a relative catalog address.
    unit : str, optional
        Unit label returned by ``unit``. Defaults to an empty string.
    writable : bool, optional
        Allow writes when no index is configured. Defaults to ``True``.
    index : int or None, optional
        Element selected from each read, or ``None`` for the full value.
        Any configured index, including zero, makes the device read-only.

    Notes
    -----
    Writes target the whole attribute and are allowed only when ``writable``
    is true and ``index`` is ``None``.
    """
    def __init__(self,
                 address: str,
                 unit: str = "",
                 writable: bool = True,
                 index: int | None = None):
        """Store the address, unit, write configuration, and optional read index."""
        super().__init__()

        self._address = address
        self._unit = unit
        self._writable = writable
        self._index = index

        if index is not None:
            #logger.warning()
            self._writable = False

    def name(self) -> str:
        """Return the configured attribute address."""
        return self._address

    def measure_name(self) -> str:
        """Return the final slash-separated component of the attribute address."""
        short = self.name().rsplit("/", 1)[1]
        return short

    def set(self, value: float):
        """Write a value to the full pySC attribute address.

        Parameters
        ----------
        value : float
            Value forwarded to the pySC client without unit conversion.

        Raises
        ------
        pyaml.PyAMLException
            If writes are disabled or a read index is configured.

        Notes
        -----
        Indexed devices are read-only; writes always target the whole attribute.
        """
        if self._writable:
            pySC_client.write(self._address, value)
        else:
            raise PyAMLException(f'Device {self.name()} at address={self._address} is not writable.')

    def set_and_wait(self, value: float):
        """Delegate to ``set`` without an additional readback or settling wait.

        Parameters
        ----------
        value : float
            Value to write to the pySC attribute.
        """
        return self.set(value)

    def get(self) -> float:
        """Read the attribute and optionally select an indexed element.

        Returns
        -------
        scalar or array-like
            Value returned by the pySC client, or its element at ``index`` when
            configured. The return value is not coerced to a float.
        """
        value = pySC_client.read(self._address)
        if self._index is None:
            return value
        else:
            return value[self._index]

    def readback(self) -> Union[Value, npt.NDArray[Value]]:
        """Return the same attribute value as ``get``, including any index selection."""
        return self.get()

    def unit(self) -> str:
        """Return the configured unit label without performing unit conversion."""
        return self._unit

    def clone_with_address(self, address: str) -> "pySCDeviceAccess":
        """Return a shallow copy with a replacement attribute address.

        Parameters
        ----------
        address : str
            Address to assign to the copy.

        Returns
        -------
        pySCDeviceAccess
            Copy retaining the original unit, write flag, and read index.
        """
        new_obj = copy.copy(self)
        new_obj._address = address
        return new_obj

    def get_range(self) -> list[float]:
        """Return the fixed placeholder limits ``[-1e16, 1e16]`` without querying pySC."""
        return [-1e16,1e16]

    def check_device_availability(self) -> bool:
        """Return ``True`` without checking the server or attribute availability."""
        return True

    def get_index(self) -> int | None:
        """Return the configured read index, or ``None`` for the full attribute."""
        return self._index
