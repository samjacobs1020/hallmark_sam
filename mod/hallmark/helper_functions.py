from pathlib import Path
import yaml
import re

# Specifies the path to encodings.yaml using __file__ as the current script
# and moving two directories above using parents[2] and appending "encodings.yaml" to path.
ENCODINGS_YAML = Path(__file__).parents[2] / "encodings.yaml"

def load_encodings_yaml(index = 0, path=ENCODINGS_YAML):
    """
    Load encoding rules from a YAML configuration file.

    Parameters:
        index : int
            Which encoding entry (specification) to return from the YAML file.
            Default is 0, which is the first entry.
        path : Path
            Path to the encodings.yaml file.

    Returns:
        dict
            A single encoding configuration containing rules such as the regex commands.
    """
    f = path.open("r", encoding="utf-8") # Opens the yaml file path
    yaml_file = yaml.safe_load(f) # Safely loads in the yaml data
    encodings = yaml_file["data"] # Extracts the encodings from the yaml file.
    return encodings[index]

def regex_sub(f, yaml_encodings):
    """
    Apply a regex substitution rule to a string using YAML-defined encoding.

    Parameters:
        f : str
            The input filepath as a string.
        yaml_encodings : dict
            An encoding dictionary loaded from YAML.

    Returns:
        str
            The transformed string after applying regex substitutions.
    """
    fmt = f # Assigns the format specified in the yaml file
    regex = yaml_encodings["encoding"]["aspin"] # Extracts the regex from the yaml file
    if re.search(regex, fmt) and len(regex)>0: # Proceeds if regex is not empty and finds what the regex intends to find
        matches = re.finditer(regex, fmt)
        for match in matches: # Iterating through the matches
            k = match.group(0) # Entire matched substring
            k_num =  "-" + str(match.group(1)) # Attaches '-' at the start of the first group
            fmt = re.sub(k,k_num , fmt) # Replaces it with the substituted string

    return fmt

