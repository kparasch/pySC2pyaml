import argparse
import sys
from typing import Sequence, Optional
import yaml
from pySC import generate_SC
import pathlib
import tempfile
import os
from scipy.constants import c

def main(argv: Optional[Sequence[str]] = None) -> int:
    argparser = argparse.ArgumentParser()
    argparser.add_argument('pysc_config', type=str, help='Path for the pySC configuration file to load')
    argparser.add_argument('output_path', type=str, help='Output path for pyaml configuration file')
    argparser.add_argument('--ip_address', type=str, default="127.0.0.1")
    argparser.add_argument('--port', type=int, default=13131)
    argparser.add_argument('--facility_name', type=str, default="pySC")
    args = argparser.parse_args(argv)

    absolute_config_path = pathlib.Path(args.pysc_config).resolve()
    initial_dir = pathlib.Path.cwd()
    config_dir = absolute_config_path.parent.resolve()
    os.chdir(config_dir)

    SC = generate_SC(absolute_config_path)

    energy = float(SC.lattice.design.energy)
    brho = energy/c
    os.chdir(initial_dir)

    facility_name = args.facility_name
    ip_address = args.ip_address
    port = args.port


    controls_config = [{"class": "pySC2pyaml.controlsystem.pySCControlSystem",
                       "name": "live",
                       "port": port,
                       "ip_address": ip_address,
                       "catalog": {"class": "pySC2pyaml.catalog.pySCCatalog"}
                      }]

    arrays_config = [
                     {"class": "pyaml.arrays.bpm.BPM",
                      "name": "BPM",
                      "elements": SC.bpm_system.names
                     },
                    ]

    bpm_devices = [{"class": "pyaml.bpm.bpm.BPM", 
                    "name": name, 
                    "x_pos": f"ORBIT/RAW/X@{i}",
                    "y_pos": f"ORBIT/RAW/Y@{i}"
                   } for i, name in enumerate(SC.bpm_system.names)
                  ]

    rf_devices = [{"class": "pyaml.rf.rf_plant.RFPlant",
                    "name": "RF",
                    "masterclock": "RF/MAIN/FREQUENCY"
                    }]
    tool_devices = [
        {"class": "pyaml.tuning_tools.orbit.Orbit",
         "bpm_array_name": "BPM",
         "hcorr_array_name": "HCorr",
         "vcorr_array_name": "VCorr",
         "rf_plant_name": "RF",
         "name": "DEFAULT_ORBIT_CORRECTION",
         "singular_values": 120,
         "response_matrix": "${path:orm.json}",
        },
        {"class": "pyaml.tuning_tools.dispersion.Dispersion",
         "name": "DEFAULT_DISPERSION",
         "bpm_array_name": "BPM",
         "rf_plant_name": "RF",
         "frequency_delta": 1500
        },
        {"class": "pyaml.tuning_tools.orbit_response_matrix.OrbitResponseMatrix",
         "name": "DEFAULT_ORBIT_RESPONSE_MATRIX",
         "bpm_array_name": "BPM",
         "hcorr_array_name": "HCorr",
         "vcorr_array_name": "VCorr",
         "corrector_delta": 1e-6
        },
    ]

    HCorr_elements = []
    HCorr_families = [list(a.keys())[0] for a in SC.configuration['tuning']['HCORR']]
    VCorr_families = [list(a.keys())[0] for a in SC.configuration['tuning']['VCORR']]
    VCorr_elements = []

    magnet_devices = []

    for array in SC.control_arrays:
        array_names = []
        magnet_conf = {}
        components = list(set([aa.split('/')[-1] for aa in SC.control_arrays[array]]))
        if len(components) == 1:
            component = components[0]
            magnet_model = {"class" : "pyaml.magnet.linear_model.LinearMagnetModel",
                            "unit": 'rad',
                            "hardware_unit": 'str'}
            #magnet_model_unit = 'rad'
            if component.startswith("B1"):
                magnet_class = "pyaml.magnet.hcorrector.HCorrector"
            elif component.startswith("A1"):
                magnet_class = "pyaml.magnet.vcorrector.VCorrector"
            elif component.startswith("B2"):
                magnet_class = "pyaml.magnet.quadrupole.Quadrupole"
            elif component.startswith("A2"):
                magnet_class = "pyaml.magnet.skewquad.SkewQuad"
            elif component.startswith("B3"):
                magnet_class = "pyaml.magnet.sextupole.Sextupole"
            elif component.startswith("A3"):
                magnet_class = "pyaml.magnet.skewsext.SkewSext"
            elif component.startswith("B4"):
                magnet_class = "pyaml.magnet.octupole.Octupole"
            elif component.startswith("A4"):
                magnet_class = "pyaml.magnet.skewoct.SkewOct"

            for magnet in SC.magnet_arrays[array]:
                magnet_conf = {"class": magnet_class,
                               "name": magnet,
                               "model": magnet_model.copy()
                              }
                if component.endswith("L"):
                    magnet_conf["model"]["calibration_factor"] = brho
                else:
                    #untested
                    magnet_conf["model"]["calibration_factor"] = brho * SC.design_magnet_settings.magnets[magnet].length
                magnet_conf["model"]["powerconverter"] = f"MAGNET/{magnet}/{component}"
                magnet_devices.append(magnet_conf)
                array_names.append(magnet)
                if array in HCorr_families:
                    HCorr_elements.append(magnet)
                if array in VCorr_families:
                    VCorr_elements.append(magnet)
            arrays_config.append({"class": "pyaml.arrays.magnet.Magnet",
                                  "name": array,
                                  "elements": array_names})
        else:
            raise NotImplementedError("CFM magnet")

    arrays_config.append({"class": "pyaml.arrays.magnet.Magnet",
                          "name": "HCorr",
                          "elements": HCorr_elements})
    arrays_config.append({"class": "pyaml.arrays.magnet.Magnet",
                          "name": "VCorr",
                          "elements": VCorr_elements})

    config = {"class": "pyaml.accelerator.Accelerator",
              "machine": "sr",
              "facility": facility_name,
              "energy": energy,
              #"alphac": float(mcf),
              "controls": controls_config,
              "arrays": arrays_config,
              "devices": tool_devices + rf_devices + bpm_devices + magnet_devices
              }


    yaml.safe_dump(config, open(args.output_path, 'w'), sort_keys=False)
    return 0

if __name__ == "__main__":
    sys.exit(main())
