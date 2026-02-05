from pathlib import Path
import yaml
import re

# tmp_fmt = "/{mag:d}a{aspin@spin_UIUC}_w{win:d}/img_s{snapshot:d}_Rh{Rhigh:d}_i{inc:d}.h5"

ENCODINGS_YAML = Path(__file__).parent / "encodings.yaml"

_ENCODING_RE = re.compile(r"\{(\w+):@(\w+)\}")

def load_encodings_yaml(path=ENCODINGS_YAML):
    f = path.open("r", encoding="utf-8")
    data = yaml.safe_load(f)
    encodings = data["encodings"]
    return encodings

def pre_process_fmt(fmt):
    return None

def encoding_map(fmt):
    encoding_map = {}
    matches = list(_ENCODING_RE.finditer(fmt))
    print(matches)
    for m in matches:
        # print(m.group(0))
        name = m.group(1)
        encoding = m.group(2)
    encoding_map[name] = encoding
    return encoding_map