import pandas as pd
import pytest
from hallmark import ParaFrame
from hallmark.helper_functions import *

@pytest.fixture
def create_ParaFrame(create_temp_data):
    fmt = str(create_temp_data / "a_{a:d}/b_{b:d}.txt")
    return ParaFrame.parse(fmt)

@pytest.fixture
def create_ParaFrame_spin(create_temp_data_spin):
    fmt = str(create_temp_data_spin / "a{aspin}/b_{b:d}.txt")
    return ParaFrame.parse(fmt)

@pytest.fixture
def create_ParaFrame_spin_with_m(create_temp_data_spin_with_m):
    fmt = str(create_temp_data_spin_with_m / '{mag:d}_mag{aspin}_w{win:d}.h5')
    return ParaFrame.parse(fmt,encoding=True)

def test_type_of_ParaFrame(create_ParaFrame):
    assert isinstance(create_ParaFrame, ParaFrame)

def test_shape_of_ParaFrame(create_ParaFrame):
    pf = create_ParaFrame
    assert pf.shape == (100,3)

def test_column_dtype(create_ParaFrame):
    pf = create_ParaFrame
    assert pd.api.types.is_float_dtype(pf["a"])
    assert pd.api.types.is_float_dtype(pf["b"])

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

def test_glob_string_format(create_temp_data):
    fmt = str(create_temp_data / "a_{a:d}/b_{b:d}.txt")
    pattern = ParaFrame.glob_search(fmt, a=0, return_pattern=True)[1]
    norm = pattern.replace("\\", "/") # standardize output for Mac and PC
    assert  norm.endswith("/a_0/b_*.txt")

def test_glob_method_returns_files(create_temp_data):
    fmt = str(create_temp_data / "a_{a:d}/b_{b:d}.txt")
    files = ParaFrame.glob_search(fmt, a=0, return_pattern=True)[0]
    assert len(files) == 10

def test_parse_method_with_added_filter_arg(create_temp_data):
    fmt = str(create_temp_data / "a_{a:d}/b_{b:d}.txt")
    pf = ParaFrame.parse(fmt, a=0)
    assert pf.shape == (10, 3)
    assert pf["a"].unique() == 0

def test_glob_method_accepts_spin_formatter_type_and_builds_glob_method(create_temp_data_spin):
    fmt = str(create_temp_data_spin / "a{aspin}/b_{b:d}.txt")
    files, pattern = ParaFrame.glob_search(fmt, encoding = True, aspin="+0.5", return_pattern=True)
    norm = pattern.replace("\\", "/") # standardize output for Mac and PC OS
    assert norm.endswith("/a+0.5/b_*.txt")
    assert len(files) == 10

def test_parse_produces_float_spin_column(create_ParaFrame_spin):
    pf = create_ParaFrame_spin
    assert pd.api.types.is_float_dtype(pf["aspin"])
    assert set(pf["aspin"].unique()) == {-0.5, 0.0, 0.5}

def test_filtering_by_numeric_spin(create_ParaFrame_spin):
    pf = create_ParaFrame_spin
    pf_filtered = pf(aspin=0.5)
    assert len(pf_filtered) == 10
    assert set(pf_filtered["aspin"].unique()) == {0.5}

# def test_loading_yaml_file_for_test_spin_formatting_contents(create_temp_data_spin_with_m):
#     fmt = str(create_temp_data_spin_with_m / "{mag:d}_mag{aspin}_w{win:d}.h5")
#     params = load_encodings_yaml(fmt,path = Path("/tmp/encoding_tmp.yaml")) # default fmt should still be the first one
    
#     assert "encoding" in params
#     assert "aspin" in params["encoding"]

def test_m_type_for_spin_data_with_yaml_regex(create_temp_data_spin_with_m):
    fmt = str(create_temp_data_spin_with_m / "{mag:d}_mag{aspin}_w{win:d}.h5")
    pf = ParaFrame.parse(fmt, encoding= True, debug = True)
    
    pf_filtered = pf(aspin=-0.5)
    assert len(pf_filtered) == 20
    assert set(pf_filtered["aspin"].unique()) == {-0.5}

def test_m_type_for_spin_data_with_multiple_filters(create_temp_data_spin_with_m):
    fmt = str(create_temp_data_spin_with_m / "{mag:d}_mag{aspin}_w{win:d}.h5")
    pf = ParaFrame.parse(fmt,encoding=True, debug = True)
    pf_filtered = pf(aspin=[-0.5,0.0])
    assert len(pf_filtered) == 40