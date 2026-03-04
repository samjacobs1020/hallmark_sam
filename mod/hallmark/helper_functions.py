from pathlib import Path
import yaml
import re

_user_yaml_path = None

def set_rel_yaml_path(path = None):
    from .core import ParaFrame
    if ParaFrame.repo_path is None:
        global _user_yaml_path
        _user_yaml_path = Path(path)
        _user_yaml_path = Path(str(_user_yaml_path) + '/' )   
def get_rel_yaml_path():
    if _user_yaml_path is not None:
        return _user_yaml_path
    return Path(__file__).parent / ".hallmark.yaml"

def load_encodings_yaml():
    path = get_rel_yaml_path()
    yaml_path = Path(path).resolve()
    f = path.open("r", encoding="utf-8")
    yaml_file = yaml.safe_load(f)
    encodings = yaml_file["data"]
    # Resolve path_to_fmt relative to the yaml file's directory
    for entry in encodings:
        if "path_to_fmt" in entry:
            entry["path_to_fmt"] = str(
                (yaml_path.parent / entry["path_to_fmt"]).resolve()
            )

    return encodings

def find_spec_by_fmt(fmt):
    path = get_rel_yaml_path()
    f = path.open("r", encoding="utf-8")
    yaml_file = yaml.safe_load(f)
    encodings = yaml_file["data"]
    for spec in encodings:
        if spec.get("fmt") == fmt:
            return spec
    return None

def regex_sub(f, yaml_encodings):

    fmt = f

    if yaml_encodings is None:
        return fmt

    enc = yaml_encodings.get("encoding", None)
    if not enc:
        return fmt

    regex = enc.get("aspin", "")
    if not regex:
        return fmt

    if re.search(regex, fmt):
        matches = re.finditer(regex, fmt)
        for match in matches:
            k = match.group(0)
            k_num = "-" + str(match.group(1))
            fmt = re.sub(k, k_num, fmt)

    return fmt