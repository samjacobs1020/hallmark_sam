import pandas as pd
import pytest
from hallmark import ParaFrame

@pytest.fixture
def create_ParaFrame(create_temp_data):
    fmt = str(create_temp_data / "a_{a:d}/b_{b:d}.txt")
    return ParaFrame.parse(fmt, debug = True)

def test_type_of_ParaFrame(create_ParaFrame):
    assert isinstance(create_ParaFrame, ParaFrame)

def test_shape_of_ParaFrame(create_ParaFrame):
    pf = create_ParaFrame
    assert pf.shape == (100,3)

def test_column_names_in_ParaFrame(create_ParaFrame):
    pf = create_ParaFrame
    assert set(pf.columns) == {"path","a","b"}

def test_all_subdirectories_a0_through_a9_get_created(create_ParaFrame):
    pf = create_ParaFrame
    assert all(pf["a"].unique() == range(10))

def test_all_txt_files_b10_through_b19_get_created(create_ParaFrame):
    pf = create_ParaFrame
    assert all(pf["b"].unique() == range(10,20))

def test_pandas_method_on_pf(create_ParaFrame):
    pf = create_ParaFrame
    assert isinstance(pf.head(), pd.DataFrame)