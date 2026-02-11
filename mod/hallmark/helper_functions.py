from pathlib import Path
import yaml
import re

ENCODINGS_YAML = Path(__file__).parents[2] / "encodings.yaml"

def load_encodings_yaml(index = 0, path=ENCODINGS_YAML):
    f = path.open("r", encoding="utf-8")
    yaml_file = yaml.safe_load(f)
    encodings = yaml_file["data"]
    return encodings[index]

def regex_sub(f, yaml_encodings):
    fmt = f
    regex = yaml_encodings["encoding"]["aspin"]
    if re.search(regex, fmt) and len(regex)>0: 
        matches = re.finditer(regex, fmt)
        for match in matches:
            k = match.group(0)
            k_num =  "-" + str(match.group(1))
            fmt = re.sub(k,k_num , fmt)

    return fmt

