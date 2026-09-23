"""Public catalog validation and cache behavior."""

import pytest
from pyaml import PyAMLException

from pySC2pyaml.catalog import pySCCatalog
from pySC2pyaml.controlsystem import pySCControlSystem


@pytest.mark.parametrize(
    "suffix,index", [("", None), ("@0", 0), ("@12", 12), ("@-1", -1)]
)
def test_resolve_address_and_index(suffix, index):
    device = pySCCatalog().resolve("ORBIT/RAW/X" + suffix)
    assert device.name() == "ORBIT/RAW/X"
    assert device.get_index() == index


@pytest.mark.parametrize(
    "key",
    [
        None,
        1,
        [],
        "",
        "a/b",
        "a/b/c/d",
        "/b/c",
        "a//c",
        "a/b/",
        "a/b/c@",
        "a/b/c@no",
        "a/b/c@1.5",
    ],
)
def test_invalid_references(key):
    with pytest.raises(PyAMLException):
        pySCCatalog().resolve(key)


def test_cache_is_scoped_by_reference_and_control_system():
    catalog = pySCCatalog()
    first = pySCControlSystem("first", 13131)
    second = pySCControlSystem("second", 13132)
    device = catalog.resolve("ORBIT/RAW/X@0", first)
    assert catalog.resolve("ORBIT/RAW/X@0", first) is device
    assert catalog.resolve("ORBIT/RAW/X@0", second) is not device
    assert catalog.resolve("ORBIT/RAW/X@1", first) is not device
    assert catalog.resolve("ORBIT/RAW/X", first) is not device
    assert catalog.resolve("ORBIT/RAW/X") is catalog.resolve("ORBIT/RAW/X")
