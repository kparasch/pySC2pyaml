"""Attachment and catalog-to-client integration without network access."""

import pytest
from pyaml import PyAMLConfigException, PyAMLException

from pySC2pyaml.catalog import pySCCatalog
from pySC2pyaml.controlsystem import pySCControlSystem
from pySC2pyaml.deviceaccess import pySCDeviceAccess


@pytest.mark.parametrize("method", ["attach", "attach_array"])
def test_attachment_preserves_order_and_reuses_devices(method):
    control = pySCControlSystem("live", 1234, ip_address="192.0.2.1")
    source = pySCDeviceAccess("ORBIT/RAW/X", index=0)
    other_index = pySCDeviceAccess("ORBIT/RAW/X", index=1)
    attached = getattr(control, method)([source, None, source, other_index])
    assert attached[0].name() == "192.0.2.1:1234/ORBIT/RAW/X"
    assert attached[1] is None
    assert attached[0] is attached[2]
    assert attached[0] is not attached[3]
    assert [attached[i].get_index() for i in (0, 3)] == [0, 1]
    assert source.name() == "ORBIT/RAW/X"
    assert control.attach([source])[0] is attached[0]
    assert getattr(control, method)([]) == []


def test_catalog_reference_reads_from_configured_endpoint(client):
    catalog = pySCCatalog()
    control = pySCControlSystem("live", 13131, catalog=catalog)
    device = control.get_device_access("ORBIT/RAW/X@0")
    client.read.side_effect = None
    client.read.return_value = [4.5, 7.5]
    assert device.readback() == 4.5
    client.read.assert_called_once_with("127.0.0.1:13131/ORBIT/RAW/X")
    assert control.get_device_access("ORBIT/RAW/X@0") is device
    with pytest.raises(PyAMLException, match="not writable"):
        device.set(1.0)
    client.write.assert_not_called()
    assert control.get_catalog() is catalog
    assert control.name() == "live"


def test_none_reference_needs_no_catalog():
    assert pySCControlSystem("live", 13131).get_device_access(None) is None


def test_missing_catalog():
    with pytest.raises(PyAMLException, match="no catalog"):
        pySCControlSystem("live", 13131).get_device_access("ORBIT/RAW/X")


def test_invalid_catalog_rejected_at_construction():
    with pytest.raises(PyAMLConfigException, match="catalog"):
        pySCControlSystem("live", 13131, catalog=object())


@pytest.mark.parametrize("ref", [42, [], pySCDeviceAccess("ORBIT/RAW/X")])
def test_rejects_nonstring_references(ref):
    with pytest.raises(PyAMLException):
        pySCControlSystem("live", 13131, catalog=pySCCatalog()).get_device_access(ref)


def test_propagates_invalid_catalog_key():
    with pytest.raises(PyAMLException, match="invalid pySC address"):
        pySCControlSystem("live", 13131, catalog=pySCCatalog()).get_device_access(
            "invalid"
        )
