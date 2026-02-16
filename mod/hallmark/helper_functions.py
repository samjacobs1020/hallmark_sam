from pathlib import Path
import yaml
import re

ENCODINGS_YAML = Path(__file__).parents[2] / "encodings.yaml"

def load_encodings_yaml(index=0, path=ENCODINGS_YAML):

    f = path.open("r", encoding="utf-8")
    yaml_file = yaml.safe_load(f)
    encodings = yaml_file["data"]
    return encodings

def find_spec_by_fmt(fmt, path=ENCODINGS_YAML):

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