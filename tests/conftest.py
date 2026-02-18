import pytest
import shutil
import yaml
from pathlib import Path

ENCODINGS_YAML = Path(__file__).parents[1] / "encodings.yaml"

@pytest.fixture(scope="function", autouse=True)
def _append_tmp_path_entry_to_repo_yaml(tmp_path, request, fmt = "data/{mag:d}_mag{aspin}_w{win:d}.h5"):
    y = yaml.safe_load(ENCODINGS_YAML.read_text(encoding="utf-8")) or {}
    y.setdefault("data", [])

    new_entry = {
        "fmt": fmt,
        "path_to_fmt": str(tmp_path),
        "encoding": {
            "aspin": r"m([0-9]+(\.[0-9]+)?|\.[0-9]+)"
        },
    }

    y["data"].append(new_entry)
    ENCODINGS_YAML.write_text(yaml.safe_dump(y, sort_keys=False), encoding="utf-8")

    yield

    y = yaml.safe_load(ENCODINGS_YAML.read_text(encoding="utf-8")) or {}
    if y.get("data"):
        y["data"].pop()
        ENCODINGS_YAML.write_text(yaml.safe_dump(y, sort_keys=False), encoding="utf-8")

def spin_format(val):
    if val == 0:
        return "0"
    return f"{val:+g}"

@pytest.fixture(scope = "function")
def create_temp_data(tmp_path):
    data_dir = tmp_path / "data"
    print(data_dir)
    for a in range(10):
        subdir = data_dir / f"a_{a}"
        subdir.mkdir(parents=True)
        for b in range(10, 20):
            (subdir / f"b_{b}.txt").touch()
    return data_dir

@pytest.fixture(scope = "function")
def create_temp_data_spin(tmp_path):
    data_dir = tmp_path / "data"
    spins = [-0.5, 0.0, 0.5]
    for a in spins:
        subdir = data_dir / f"a{spin_format(a)}"
        subdir.mkdir(parents=True)
        for b in range(10, 20):
            (subdir / f"b_{b}.txt").touch()
    return data_dir

@pytest.fixture(scope = "function")
def create_temp_data_spin_with_m(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True)
    spins = ["m0.5", "0", "0.5"]
    
    for mag in range(0, 2):   
        for aspin in spins:       
            for win in range(10, 20):  
                file_name = f"{mag}_mag{aspin}_w{win}.h5"
                (data_dir / file_name).touch()
    return data_dir