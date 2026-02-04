from pathlib import Path
import yaml

cwd = Path.cwd()
ENCODINGS_YAML = Path(__file__).parent / "encodings.yaml"
print(ENCODINGS_YAML)

def load_encodings_yaml(path=ENCODINGS_YAML):
    f = path.open("r", encoding="utf-8")
    data = yaml.safe_load(f)
    encodings = data["encodings"]
    return encodings

