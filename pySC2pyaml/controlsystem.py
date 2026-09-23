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
    def __init__(
        self,
        name: str,
        port: int,
        ip_address: str = "127.0.0.1",
        catalog: ACatalog | None = None,
    ):
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
        return self._attach(devs)

    def attach(self, devs: list[DeviceAccess]) -> list[DeviceAccess]:
        return self._attach(devs)

    def _attach(self, devs: list[DeviceAccess]) -> list[DeviceAccess]:
        # Concatenate the pySC prefix ("ip_address:port/")
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
        """
        Resolve a public device reference for this pySC control system.

        YAML references are opaque strings resolved by the configured backend
        catalog. Public Python APIs may pass Tango backend configuration models.
        Already constructed DeviceAccess instances are intentionally rejected:
        attach() remains the internal compatibility API for those.

        Parameters
        ----------
        ref : str or None
            Catalog key or ``None``.

        Returns
        -------
        DeviceAccess or None
            Attached device access, or ``None`` if ``ref`` is ``None``.

        Raises
        ------
        pyaml.PyAMLException
            If ``ref`` is an already constructed DeviceAccess, if no usable
            catalog is configured for a string key, or if ``ref`` has an
            unsupported type.
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
        """
        Return the name of the control system.

        Returns
        -------
        str
            Name of the control system.
        """
        return self._name

    def get_aggregator(self) -> None:
        """
        Return a new empty aggregator of device accesses.

        If ``None`` were returned, serialized readings/writings would be
        performed by the pyAML core instead.

        Returns
        -------
        MultiAttribute
            New empty :class:`~tango.pyaml.multi_attribute.MultiAttribute`.
        """
        return None

    def scalar_aggregator(self) -> str | None:
        """
        Return the module name used for handling aggregator of DeviceAccess.

        Returns
        -------
        str or None
            Aggregator module name. Always ``None`` for Tango.
        """
        return None

    def vector_aggregator(self) -> str | None:
        """
        Return the module name used for handling aggregator of DeviceVectorAccess.

        Returns
        -------
        str or None
            Aggregator module name. Always ``None`` for Tango.
        """
        return None

    def get_catalog(self) -> ACatalog | None:
        """
        Return the catalog that references all control system devices.

        Returns
        -------
        Catalog or None
            The catalog, or ``None`` if none was configured.
        """
        return self._catalog

    def __repr__(self):
        return __pyaml_repr__(self)