"""Device I/O contracts and regressions for permissions and attribute names."""

import numpy as np
import pytest
from pyaml import PyAMLException

from pySC2pyaml.deviceaccess import pySCDeviceAccess

ADDRESS = "127.0.0.1:13131/ORBIT/RAW/X"


@pytest.mark.parametrize("method", ["set", "set_and_wait"])
@pytest.mark.parametrize("writable", [False, True])
@pytest.mark.parametrize("index", [None, 0, 1, -1])
def test_write_permissions(client, method, writable, index):
    device = pySCDeviceAccess(ADDRESS, writable=writable, index=index)
    if writable and index is None:
        getattr(device, method)(2.5)
        client.write.assert_called_once_with(ADDRESS, 2.5)
    else:
        with pytest.raises(PyAMLException, match="not writable"):
            getattr(device, method)(2.5)
        client.write.assert_not_called()
    client.read.assert_not_called()


@pytest.mark.parametrize("method", ["get", "readback"])
@pytest.mark.parametrize("index", [None, 0, 1, -1])
def test_array_reads(client, method, index):
    values = np.array([1.5, 2.5, 3.5])
    client.read.side_effect = None
    client.read.return_value = values
    result = getattr(pySCDeviceAccess(ADDRESS, index=index), method)()
    np.testing.assert_array_equal(result, values if index is None else values[index])
    client.read.assert_called_once_with(ADDRESS)
    client.write.assert_not_called()


def test_scalar_read(client):
    client.read.side_effect = None
    client.read.return_value = 3.5
    assert pySCDeviceAccess(ADDRESS).get() == 3.5


@pytest.mark.parametrize("address", [ADDRESS, "ORBIT/RAW/X"])
def test_names_and_units(address):
    device = pySCDeviceAccess(address, unit="mm")
    assert device.name() == address
    assert device.measure_name() == "X"
    assert device.unit() == "mm"


@pytest.mark.parametrize("index,writable", [(None, True), (None, False), (0, True)])
def test_clone_preserves_configuration(client, index, writable):
    original = pySCDeviceAccess(
        "ORBIT/RAW/X", unit="mm", writable=writable, index=index
    )
    clone = original.clone_with_address(ADDRESS)
    assert clone is not original
    assert original.name() == "ORBIT/RAW/X"
    assert clone.name() == ADDRESS
    assert clone.unit() == "mm"
    assert clone.get_index() == index
    if writable and index is None:
        clone.set(1.0)
        client.write.assert_called_once_with(ADDRESS, 1.0)
    else:
        with pytest.raises(PyAMLException, match="not writable"):
            clone.set(1.0)
        client.write.assert_not_called()


@pytest.mark.parametrize("method,operation", [("get", "read"), ("set", "write")])
def test_client_errors_propagate(client, method, operation):
    getattr(client, operation).side_effect = ConnectionError("server unavailable")
    with pytest.raises(ConnectionError, match="server unavailable"):
        getattr(pySCDeviceAccess(ADDRESS), method)(*([1.0] if method == "set" else []))
