import pytest

def spin_format(val):
    if val == 0:
        return "0"
    return f"{val:+g}"

@pytest.fixture(scope = "function")
def create_temp_data(tmp_path):
    data_dir = tmp_path / "data"
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
