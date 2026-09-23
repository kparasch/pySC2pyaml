"""Abstract interface for resolving pySC device references."""
from abc import ABCMeta, abstractmethod

# This is actually required only to avoid circular imports. TYPE_CHECKING does not work in this case with pyaml validation. 
class ACatalog(metaclass=ABCMeta):
    """Define the interface for a catalog of device references."""
    @abstractmethod
    def resolve(self, key: str):
        """Resolve a catalog key to a device access object.

        Parameters
        ----------
        key : str
            Device reference in the format supported by the catalog.

        Returns
        -------
        DeviceAccess
            Device access object corresponding to the reference.
        """
        pass