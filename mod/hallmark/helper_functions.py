from pathlib import Path
import yaml
import re

# Default user .yaml file path
_user_yaml_path = None

def set_rel_yaml_path(path=None):
    """
        This function sets the relative .yaml file path.

        Args:
        path: Defaulted to None
    """
    if path is None:
        return
    global _user_yaml_path
    _user_yaml_path = Path(path) / ".hallmark.yaml"   

def get_rel_yaml_path(repo_path=None):
    """
        This function gets the relative .yaml file path.

        Args:
        repo_path: Path to the repo, where .yaml file is
        located.

        Returns: The path to the .yaml file.
    """

    if repo_path is not None:
        return Path(repo_path) / ".hallmark.yaml" # returns the path specified
    if _user_yaml_path is not None:
        return _user_yaml_path
    return Path.cwd() / ".hallmark.yaml" 
    # returns the current working directory

def load_encodings_yaml(repo_path=None):
    """
        This function loads contents in the .yaml file and
        resolves the path to the format string.

        Args:
        repo_path: Path to the repo, where .yaml file is
        located.

        Returns: The user specified encodings in the .yaml file.
    """
    path = get_rel_yaml_path(repo_path=repo_path) # path to the yaml file
    f = path.open("r", encoding="utf-8")
    yaml_file = yaml.safe_load(f)
    encodings = yaml_file["data"] # extract the encodings
    # Resolve path_to_fmt relative to the yaml file's directory
    notebook_dir = Path.cwd()
    for entry in encodings:
        if "path_to_fmt" in entry:
            entry["path_to_fmt"] = str(
                (notebook_dir / entry["path_to_fmt"]).resolve()
            )

    return encodings

def find_spec_by_fmt(fmt, repo_path=None):
    """
        This function find the user specifications in the
        .yaml file through the format string.

        Args:
        fmt: format string
        repo_path: Path to the repo, where .yaml file is
        located.

        Returns: The user specifications in the .yaml file if
        the format string in .parse matches the fmt in the .yaml file.
    """
    path = get_rel_yaml_path(repo_path=repo_path) # path to the yaml file
    f = path.open("r", encoding="utf-8")
    yaml_file = yaml.safe_load(f)
    encodings = yaml_file["data"]
    for spec in encodings:
        if spec.get("fmt") == fmt:
            return spec # returns specifications if format strings match
    return None

def regex_sub(f, yaml_encodings):
    """
        This function conducts the regex substitution if mentioned
        in the yaml file.

        Args:
        f: format string
        yaml_encodings: The encodings in the .yaml file.

        Returns: The format string through various conditionals including 
        evaulating the regex.
    """

    fmt = f

    # conditionals looking through .yaml files.
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
        for match in matches: # conducts the regex substitution
            k = match.group(0)
            k_num = "-" + str(match.group(1))
            fmt = re.sub(k, k_num, fmt)

    return fmt