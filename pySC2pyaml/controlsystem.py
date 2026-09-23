"""Bind PyAML device references to a pySC server endpoint."""
import logging

from pyaml import PyAMLException
from pyaml.common.element import __pyaml_repr__
from pyaml.control.controlsystem import ControlSystem
from pyaml.control.deviceaccess import DeviceAccess
from pyaml.validation import DynamicValidation, register_schema

from .version import __version__
from .abstract_catalog import ACatalog

logger = logging.getLogger(__name__)

@register_schema
class pySCControlSystem(ControlSystem, DynamicValidation):
    """Attach catalog devices to a configured pySC server.

    Parameters
    ----------
    name : str
        Name identifying this control system in PyAML.
    port : int
        Port of the pySC server.
    ip_address : str, optional
        Server address. Defaults to ``"127.0.0.1"``.
    catalog : ACatalog or None, optional
        Catalog used to resolve string references. Its ``resolve`` method must
        accept the key and this control system as positional arguments.
    """
    def __init__(
        self,
        name: str,
        port: int,
        ip_address: str = "127.0.0.1",
        catalog: ACatalog | None = None,
    ):
        """Store the server configuration and initialize the attached device cache."""
        super().__init__()
        self._name = name
        self._ip_address = ip_address
        self._port = port
        self._catalog = catalog
        self.__devices = {}  # Dict containing all attached DeviceAccess

        logger.warning(
            f"PyAML pySC control system binding ({__version__}) initialized with name '{self._name}',"
            f" and ip address '{self._ip_address}' and port {self._port}.",
        )

    def attach_array(self, devs: list[DeviceAccess]) -> list[DeviceAccess]:
        """Attach a sequence of devices to this server.

        Parameters
        ----------
        devs : list of pySCDeviceAccess or None
            Devices with addresses relative to the server endpoint.

        Returns
        -------
        list of pySCDeviceAccess or None
            Attached devices in input order, preserving ``None`` entries.
            Devices with the same full address and index share a cached instance.
        """
        return self._attach(devs)

    def attach(self, devs: list[DeviceAccess]) -> list[DeviceAccess]:
        """Attach devices using the configured server address and port.

        Parameters
        ----------
        devs : list of pySCDeviceAccess or None
            Devices with addresses relative to the server endpoint.

        Returns
        -------
        list of pySCDeviceAccess or None
            Cached clones with the endpoint prepended to their addresses.
            Input order and ``None`` entries are preserved.
        """
        return self._attach(devs)

    def _attach(self, devs: list[DeviceAccess]) -> list[DeviceAccess]:
        # Concatenate the pySC prefix ("ip_address:port/")
        """Prefix device addresses with the endpoint and cache clones by address and index."""
        newDevs = []
        for d in devs:
            if d is not None:
                address = d.name()
                index = d.get_index()
                full_address = f"{self._ip_address}:{self._port}/{address}"
                if index is not None:
                    key = f"{full_address}@{index}"
                else:
                    key = full_address
                if key not in self.__devices:
                    self.__devices[key] = d.clone_with_address(full_address)
                newDevs.append(self.__devices[key])
            else:
                newDevs.append(None)
        return newDevs

    def get_device_access(self, ref: str | None) -> DeviceAccess | None:
        """Resolve a catalog reference and attach the device to this server.

        Parameters
        ----------
        ref : str or None
            Key understood by the configured catalog, or ``None``.

        Returns
        -------
        DeviceAccess or None
            Attached device access, or ``None`` when no reference is supplied.

        Raises
        ------
        pyaml.PyAMLException
            If the reference is neither a string nor ``None``, the catalog is
            missing or unsupported, or catalog resolution rejects the key.

        Notes
        -----
        Use ``attach`` for existing device access objects. The catalog receives
        this control system as the second argument to its ``resolve`` method.
        """
        if ref is None:
            return None

        if isinstance(ref, DeviceAccess):
            raise PyAMLException(
                "pySCControlSystem.get_device_access() expects a catalog key "
                "or None. Use attach() for already constructed "
                "DeviceAccess objects."
            )

        if isinstance(ref, str):
            catalog = self.get_catalog()
            if catalog is None:
                raise PyAMLException(
                    f"TangoControlSystem '{self.name()}' has no catalog configured."
                )
            if not isinstance(catalog, ACatalog):
                raise PyAMLException(
                    f"TangoControlSystem '{self.name()}' has unsupported catalog type "
                    f"{type(catalog).__name__}."
                )
            try:
                resolve = catalog.resolve
            except AttributeError as exc:
                raise PyAMLException(
                    f"Catalog '{catalog.get_name()}' cannot resolve key '{ref}': "
                    "missing backend resolve() method."
                ) from exc
            device = resolve(ref, self)
            return self._attach([device])[0]

        raise PyAMLException(
            f"TangoControlSystem.get_device_access() cannot resolve references of type "
            f"{type(ref).__name__}; expected str or None."
        )

    def name(self) -> str:
        """Return the configured control system name."""
        return self._name

    def get_aggregator(self) -> None:
        """Return ``None`` to use PyAML's sequential device reads and writes.

        This backend does not provide a device access aggregator.
        """
        return None

    def scalar_aggregator(self) -> str | None:
        """Return ``None`` because this backend provides no scalar aggregator module."""
        return None

    def vector_aggregator(self) -> str | None:
        """Return ``None`` because this backend provides no vector aggregator module."""
        return None

    def get_catalog(self) -> ACatalog | None:
        """Return the configured catalog, if any.

        Returns
        -------
        ACatalog or None
            Catalog supplied at construction, or ``None`` if none was configured.
        """
        return self._catalog

    def __repr__(self):
        """Return the PyAML representation of this control system."""
        return __pyaml_repr__(self)