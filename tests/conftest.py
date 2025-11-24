import pytest

@pytest.fixture(scope = "function")
def create_temp_data(tmp_path):
    data_dir = tmp_path / "data"
    for a in range(10):
        subdir = data_dir / f"a_{a}"
        subdir.mkdir(parents=True)
        for b in range(10, 20):
            (subdir / f"b_{b}.txt").touch()
    return data_dir