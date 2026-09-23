"""Resolve pySC attribute paths to cached device access objects."""
from pyaml.validation import DynamicValidation, register_schema
from pyaml.control.deviceaccess import DeviceAccess
from pyaml import PyAMLException

from .deviceaccess import pySCDeviceAccess
from .abstract_catalog import ACatalog
from .controlsystem import pySCControlSystem

@register_schema
class pySCCatalog(ACatalog, DynamicValidation):
    """Cache device access objects for pySC attribute paths.

    Keys use ``server/location/property`` with an optional ``@index`` suffix
    for selecting an element from an array read.
    """
    def __init__(self):
        """Initialize an empty device reference cache."""
        super().__init__()
        self._refs: dict[tuple[int, str], DeviceAccess] = {}

    def resolve(self, key: str, control_system: pySCControlSystem | None = None) -> DeviceAccess:
        """Return the cached device access for a key and control system.

        Parameters
        ----------
        key : str
            Address in the form ``server/location/property`` or
            ``server/location/property@index``.
        control_system : pySCControlSystem or None, optional
            Control system whose identity scopes the cache. Its network address
            is not added here; attachment is handled by the control system.

        Returns
        -------
        DeviceAccess
            Cached device access with the parsed address and optional index.

        Raises
        ------
        pyaml.PyAMLException
            If the key is not a string or has an invalid address or index.
        """
        address, index = self._parse_key(key)
        cache_key = (id(control_system), key)

        if cache_key not in self._refs:
            self._refs[cache_key] = pySCDeviceAccess(address=address, index=index)

        return self._refs[cache_key]

    def _parse_key(self, key: str) -> tuple[str, int | None]:
        """Validate and split a catalog key into an attribute path and index.

        Parameters
        ----------
        key : str
            Three nonempty slash-separated components, optionally followed by
            ``@`` and an integer index. Negative indices are accepted.

        Returns
        -------
        tuple[str, int or None]
            Attribute path without the suffix and the parsed index, or ``None``
            when no index is supplied.

        Raises
        ------
        pyaml.PyAMLException
            If the key is not a string, the attribute path does not have exactly
            three nonempty components, or the index is not a valid integer.
        """
        if not isinstance(key, str):
            raise PyAMLException(
                f"pySC catalog expects string keys, got {type(key).__name__}"
            )

        if "@" in key:
            attr_path, idx_str = key.rsplit("@", 1)
            try:
                index = int(idx_str)
            except ValueError as exc:
                raise PyAMLException(
                    f"pySC catalog invalid index '{idx_str}' in key '{key}'."
                ) from exc
        else:
            attr_path = key
            index = None

        parts = attr_path.split("/")
        if len(parts) != 3 or any(part == "" for part in parts):
            raise PyAMLException(
                f"pySC catalog cannot resolve invalid pySC address "
                f"reference '{key}'. Expected 'server/location/property' or "
                f"'server/location/property@index'."
            )

        return attr_path, index