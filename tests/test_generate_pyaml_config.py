"""Exercise the CLI with a small simulated machine and real YAML output."""

from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from scipy.constants import c

from pySC2pyaml.scripts import generate_pyaml_config as generator


@pytest.fixture
def machine():
    """Represent the pySC fields consumed by the configuration generator."""
    return SimpleNamespace(
        lattice=SimpleNamespace(design=SimpleNamespace(energy=3e9)),
        bpm_system=SimpleNamespace(names=["BPM1", "BPM2"]),
        configuration={"tuning": {"HCORR": [{"H": {}}], "VCORR": [{"V": {}}]}},
        control_arrays={"H": ["MAGNET/H1/B1L"], "V": ["MAGNET/V1/A1"]},
        magnet_arrays={"H": ["H1"], "V": ["V1"]},
        design_magnet_settings=SimpleNamespace(
            magnets={"V1": SimpleNamespace(length=0.4)}
        ),
    )


@pytest.fixture
def generation_context(tmp_path, monkeypatch, machine):
    """Load a fake machine from a separate input directory."""
    monkeypatch.chdir(tmp_path)
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    source = inputs / "machine.yaml"
    source.write_text("# Input is supplied by the mocked loader.\n")
    calls = []

    def load(path):
        calls.append((path, Path.cwd()))
        return machine

    monkeypatch.setattr(generator, "generate_SC", load)
    return SimpleNamespace(source=source, root=tmp_path, calls=calls)


@pytest.mark.parametrize("custom", [False, True])
def test_generated_configuration(generation_context, custom):
    context = generation_context
    output = context.root / "output.yaml"
    output.write_text("old contents")
    arguments = ["inputs/machine.yaml", "output.yaml"]
    if custom:
        arguments += [
            "--ip_address",
            "192.0.2.1",
            "--port",
            "1234",
            "--facility_name",
            "TestRing",
        ]
    assert generator.main(arguments) == 0
    assert context.calls == [(context.source, context.source.parent)]
    assert Path.cwd() == context.root
    config = yaml.safe_load(output.read_text())
    assert config["class"] == "pyaml.accelerator.Accelerator"
    assert config["machine"] == "sr"
    assert config["energy"] == 3e9
    assert config["facility"] == ("TestRing" if custom else "pySC")
    control = config["controls"][0]
    assert control["class"] == "pySC2pyaml.controlsystem.pySCControlSystem"
    assert control["catalog"]["class"] == "pySC2pyaml.catalog.pySCCatalog"
    assert control["ip_address"] == ("192.0.2.1" if custom else "127.0.0.1")
    assert control["port"] == (1234 if custom else 13131)
    arrays = {array["name"]: array["elements"] for array in config["arrays"]}
    assert arrays == {
        "BPM": ["BPM1", "BPM2"],
        "H": ["H1"],
        "V": ["V1"],
        "HCorr": ["H1"],
        "VCorr": ["V1"],
    }
    devices = {device["name"]: device for device in config["devices"]}
    for index, name in enumerate(["BPM1", "BPM2"]):
        assert devices[name]["x_pos"] == f"ORBIT/RAW/X@{index}"
        assert devices[name]["y_pos"] == f"ORBIT/RAW/Y@{index}"
    assert devices["RF"]["masterclock"] == "RF/MAIN/FREQUENCY"
    assert devices["H1"]["model"]["powerconverter"] == "MAGNET/H1/B1L"
    assert devices["H1"]["model"]["calibration_factor"] == pytest.approx(3e9 / c)
    assert devices["V1"]["model"]["calibration_factor"] == pytest.approx(3e9 / c * 0.4)
    for name in (
        "DEFAULT_ORBIT_CORRECTION",
        "DEFAULT_DISPERSION",
        "DEFAULT_ORBIT_RESPONSE_MATRIX",
    ):
        assert devices[name]["bpm_array_name"] == "BPM"


@pytest.mark.parametrize(
    "component,class_name",
    [
        ("B1L", "hcorrector.HCorrector"),
        ("A1L", "vcorrector.VCorrector"),
        ("B2L", "quadrupole.Quadrupole"),
        ("A2L", "skewquad.SkewQuad"),
        ("B3L", "sextupole.Sextupole"),
        ("A3L", "skewsext.SkewSext"),
        ("B4L", "octupole.Octupole"),
        ("A4L", "skewoct.SkewOct"),
    ],
)
def test_magnet_class_mapping(generation_context, machine, component, class_name):
    machine.control_arrays = {"M": [f"MAGNET/M1/{component}"]}
    machine.magnet_arrays = {"M": ["M1"]}
    generator.main([str(generation_context.source), "output.yaml"])
    config = yaml.safe_load(Path("output.yaml").read_text())
    magnet = next(device for device in config["devices"] if device["name"] == "M1")
    assert magnet["class"] == f"pyaml.magnet.{class_name}"
    assert magnet["model"]["powerconverter"] == f"MAGNET/M1/{component}"


def test_combined_function_magnets_are_rejected(generation_context, machine):
    machine.control_arrays["H"].append("MAGNET/H1/B2L")
    with pytest.raises(NotImplementedError, match="CFM magnet"):
        generator.main([str(generation_context.source), "output.yaml"])
    assert not Path("output.yaml").exists()


@pytest.mark.parametrize(
    "arguments,exit_code",
    [(["--help"], 0), ([], 2), (["in.yaml", "out.yaml", "--port", "invalid"], 2)],
)
def test_argument_handling(monkeypatch, arguments, exit_code):
    def unexpected_load(*args):
        pytest.fail("Argument handling should not load a machine")

    monkeypatch.setattr(generator, "generate_SC", unexpected_load)
    with pytest.raises(SystemExit) as exc:
        generator.main(arguments)
    assert exc.value.code == exit_code


def test_uses_process_arguments(generation_context, monkeypatch):
    monkeypatch.setattr(
        "sys.argv", ["pysc-to-pyaml", str(generation_context.source), "output.yaml"]
    )
    assert generator.main() == 0
    assert Path("output.yaml").is_file()
