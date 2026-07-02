from __future__ import annotations
from pathlib import Path
import shutil
from hallmark import ParaFrame
from .fmt_detection import detect_fmt, KNOWN_META_FILES, _DELIM_PATTERN,\
                                 DRIVE_EXTS_LOWER, META_EXTS_LOWER
import parse
import re
from itertools import combinations
from .repo import Repo
from .repo_manifest import manifest_frame_from_pf

## Mapping of file extensions to archive formats for shutil.unpack_archive
_ARCHIVE_FORMAT_BY_EXT = {
    ".zip": "zip", ".tar": "tar", ".tgz": "gztar",
    ".gz": "gztar", ".bz2": "bztar", ".xz": "xztar",
}

def _sanitize_branch_name(name: str) -> str:
    """Replace characters git disallows in ref names."""
    for ch in ["{", "}", " ", "~", "^", ":", "?", "*", "[", "\\"]:
        name = name.replace(ch, "_")
    name = name.replace("..", "__")
    return name.strip("/")

def _compile_parsers(fmts: list[str], cache: dict) -> \
                        list[tuple[str, int, "parse.Parser"]]:
    """Compile every fmt and its trailing-dropped-parameter variants,
    reusing already-compiled parsers from `cache` when the exact same
    fmt string has been seen before."""
    parsers = []
    # normalize the deliminators for parsing
    for f in fmts:
        if f in cache:
            # reuse the parser from cache if this fmt has already been compiled
            parsers.extend(cache[f])
            continue
        # normalize the deliminators for parsing
        stem = re.sub(r"[\-.]", "_", f)
        tokens = stem.split("_")
        # find the indices of the tokens that are parameters
        param_indices = [i for i, t in enumerate(tokens)
                 if re.fullmatch(r"\{.*?\}", t)]
        # use set to avoid duplicates when dropping different combinations of parameters
        variants = set()
        # try dropping 0 to all parameters to create different fmt variants
        for drop_count in range(len(param_indices) + 1):
            # find the positions of the parameters to drop for this variant
            for drop_count in range(len(param_indices) + 1):
                for positions_to_drop in combinations(param_indices, drop_count):
                    positions_to_drop = set(positions_to_drop)
                    kept = [t for i, t in enumerate(tokens) 
                            if i not in positions_to_drop]
                    variants.add("_".join(kept))
            # create a new fmt variant with the selected parameters dropped
            kept = [t for i, t in enumerate(tokens) if i not in positions_to_drop]
            variants.add("_".join(kept))

        # compile a parser for each variant and store it in the cache
        f_parsers = [
            (f, len(v.split("_")), parse.compile(v, case_sensitive=True))
            for v in variants]
        cache[f] = f_parsers
        parsers.extend(f_parsers)

    return parsers

def _extract_drive(drive_path: Path) -> Path:
    # remove extension from drive name to create the extraction directory
    name = drive_path.name
    # remove extra drive extensions
    for double_ext in (".tar.gz", ".tar.bz2", ".tar.xz"):
        if name.lower().endswith(double_ext):
            stem = name[: -len(double_ext)]
            break
    else:
        stem = drive_path.stem
    extract_dir = drive_path.parent / stem
    
    # check that the drive has not already been extracted
    if not extract_dir.exists():
        archive_format = _ARCHIVE_FORMAT_BY_EXT.get(drive_path.suffix.lower())
        kwargs = {"filter": "data"} if archive_format in \
                    ("tar", "gztar", "bztar", "xztar") else {}
        if archive_format:
            # avoid errors with shutil in Python 3.14+ 
            shutil.unpack_archive(str(drive_path), str(extract_dir),
                                   format=archive_format, **kwargs)
        else:
            shutil.unpack_archive(str(drive_path), str(extract_dir))
    return extract_dir

# private function used by build_tree to create nested data branch
def _build_data_branches(root: Path, fmt: str | list[str] | None,
                          parser_cache: dict, tracked: set[str],
                          all_paths: list[Path]) -> dict:
    """
    Build the fmt/stem data structure for files matching the given fmt(s).

    Args:
        root:    Path to search for matching files.
        fmt:     Format string or list of format strings for parsing data files.
        parser_cache: Cache of compiled parsers for the format strings.
        tracked: Set of relative file paths already accounted for.
        all_paths: List of all file paths to consider.

    Returns:
        Dict of {fmt_str: {stem_key: ParaFrame, ..., "all": ParaFrame}}.
    """
    ### FMT STEMS OUTER DICT ###

    # detect the fmt(s) if not provided, and compile parsers for them
    fmts = detect_fmt(root) if fmt is None else ([fmt] if isinstance(fmt, str) else fmt)
    parsers = _compile_parsers(fmts, parser_cache)
    # group the parsers by their token count for efficient matching
    parsers_by_tc: dict[int, list] = {}
    parsers_by_fmt: dict[str, list] = {}
    for fmt_str, variant_token_count, parser in parsers:
        parsers_by_tc.setdefault(variant_token_count, []).append((fmt_str, parser))
        parsers_by_fmt.setdefault(fmt_str, []).append(parser)

    # dict of the different fmt stems initialization
    fmt_stems = {}
    unmatched_files = []
    # search all subdirectories from root
    for file in all_paths:
        # if the file isn't a dir or a drive
        relative_path = str(file.relative_to(root))
        if relative_path in tracked:
            continue
        # reset parse and fmt for each file
        parsed = None
        matched_fmt = None

        stem_only = re.sub(r"[\-.]", "_", file.stem)
        stem_with_ext = stem_only + re.sub(r"[\-.]", "_", file.suffix)
        # counts to see if ext was included in fmt
        stem_only_token_count = len(stem_only.split("_"))
        stem_with_ext_token_count = len(stem_with_ext.split("_")) 

        # parse the file name to extract fields, skip if it doesn't match the format
        matched = False
        # iterate over each candidate and its token count
        for candidate, candidate_tc in (
        (stem_only, stem_only_token_count),
        (stem_with_ext, stem_with_ext_token_count),):
            # iterate over each parser that matches this candidate's token count
            for fmt_str, parser in parsers_by_tc.get(candidate_tc, []):
                parsed = parser.parse(candidate)
                if parsed:
                    matched_fmt = fmt_str
                    matched = True
                    break
            # break out once the correct parser has been found for this candidate
            if matched:
                break

        if parsed:
            # get path to file from data root
            relative_path = str(file.relative_to(root))
            # create unique stem name based on fmt parameters excluding extension
            stem_key = "_".join(str(value) for key, value in parsed.named.items() 
                                if key != "ext")
            if not stem_key:
                stem_key = "None"
            # create a row for this file to add to relevant Paraframe
            row = {
                "path": relative_path,
                # normalize ext to not have period
                "ext": Path(relative_path).suffix.lstrip("."),
                # one column for each different parsed field
                **{key: value for key, value in parsed.named.items() if key != "ext"},}
            # add row to dict, and create the dict if it doesn't exist yet
            fmt_stems.setdefault(matched_fmt, {}).setdefault(stem_key, []).append(row)
            tracked.add(relative_path)
        else:
            extension = file.suffix.lstrip(".").lower()
            if extension not in DRIVE_EXTS_LOWER and extension not in META_EXTS_LOWER \
            and file.stem.split(".")[0] not in KNOWN_META_FILES:
                unmatched_files.append(file)

    # double check unmatched files to see if they match any fmt stems by literal tokens
    for file in unmatched_files:
        stem_tokens = set(re.split(_DELIM_PATTERN, file.stem))
        stem_only = re.sub(r"[\-.]", "_", file.stem)
        for fmt_str in list(fmt_stems.keys()):
            fmt_literals = {t for t in re.split(_DELIM_PATTERN, fmt_str)
                            if not re.fullmatch(r"\{p\d+\}", t)}
            # if there are no stem tokens in the fmt, this fmt isn't a candidate
            if not (stem_tokens & fmt_literals):
                continue

            # reset the parsed variable for each fmt
            parsed = None
            # iterate over each parser for this fmt to see if it can parse the stem
            for parser in parsers_by_fmt.get(fmt_str, []):
                parsed = parser.parse(stem_only)
                if parsed:
                    break

            relative_path = str(file.relative_to(root))
            # if the file matches the fmt, create a row for it and add it to the dict
            if parsed:
                stem_key = "_".join(str(v) for k, v
                                    in parsed.named.items() if k != "ext")
                if not stem_key:
                    continue
                row = {
                    "path": relative_path,
                    "ext": file.suffix.lstrip("."),
                    **{k: v for k, v in parsed.named.items() if k != "ext"},}
            else:
                param_names = re.findall(r"\{(p\d+)\}", fmt_str)
                row = {
                    "path": relative_path,
                    "ext": file.suffix.lstrip("."),
                    **{name: None for name in param_names},}
                # create a stem key with None for each parameter since it didn't match
                stem_key = "_".join(str(None) for _ in param_names)
                if not stem_key:
                    continue

            fmt_stems[fmt_str].setdefault(stem_key, []).append(row)
            tracked.add(relative_path)
            break

    ### FMT STEMS INNER DICTS ###
    # data structure initialization
    data_branches = {}
    # for every fmt and its stem dict
    for fmt_str, stems in fmt_stems.items():
        fmt_dict = {}
        # loop thru every stem for this fmt
        for stem_key, rows in stems.items():
            # create a Paraframe for each different stem
            stem_pf = ParaFrame(rows, base_path=root)
            # stem Paraframes are nested inside the fmt dict
            fmt_dict[stem_key] = stem_pf
        # each fmt broken into different data branches
        data_branches[fmt_str] = fmt_dict

    return data_branches


def build_tree(root: Path, fmt: str | list[str] | None = None, data_type: str = "L2",
                _parser_cache: dict | None = None) -> dict:
    """
    Build an in-memory pytree for an EHT dataset directory.

    Args:
        root: Path to the EHT dataset root directory.
        fmt: Format string for parsing data files.
        data_type: Type of data to build ("L1" or "L2")
        _parser_cache: Cache of compiled parsers for the format strings

    Returns:
        A dictionary with keys:
        - "meta"   : ParaFrame of housekeeping files
        - "drives" : ParaFrame of compressed archives
        - "data"   : dict of {stem -> ParaFrame}
    """
    # create clean root path
    root = Path(root).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"{root} is not a directory")
    # track files that are included in the tree to avoid double counting
    tracked = set()

    # compile parsers for the given fmt(s) if not already provided
    if _parser_cache is None:
        _parser_cache = {}

    # L1 data makes recursive calls for each directory, so use glob instead of rglob
    glob_fn = root.glob if data_type == "L1" else root.rglob
    all_paths = [p for p in glob_fn("*") if p.is_file()]

    ### DRIVES ###
    # collect all drive paths matching any supported extension
    extracted_dir_names = set()
    # add any file that has this ext to the drive paths list and tracked set
    for path in all_paths:
        if path.suffix.lstrip(".").lower() not in DRIVE_EXTS_LOWER:
            continue
        extract_dir = _extract_drive(path)
        # only L1 data needs to track the extracted directory names for recursion
        if data_type == "L1":
           extracted_dir_names.add(extract_dir.name)
        tracked.add(str(path.relative_to(root)))

    ### DATA ###
    data_branches = _build_data_branches(root, fmt, _parser_cache, tracked, all_paths) \
                    if data_type == "L2" else {}

    ### META ###
    # create a list of all files under root that aren't tracked
    meta_files = {
        str(file.relative_to(root))
        for file in all_paths
        # add inventory item if its not a dir, not the .hm, and not in tracked
        if ".hm" not in file.parts
           and str(file.relative_to(root)) not in tracked
    }
    # create a paraframe for the meta files with extensions column
    meta_pf = ParaFrame(
    [{"path": file, "ext": Path(file).suffix.lstrip(".")} 
     for file in sorted(meta_files)],
    base_path=root,)
    for _, row in meta_pf.iterrows():
        tracked.add(row["path"])

    # double check for repeated file names in the meta ParaFrame to make a new fmt
    if data_type == "L2" and not meta_pf.empty:
        name_counts = meta_pf["path"].apply(lambda p: Path(p).name).value_counts()
        # find the names that are repeated in the meta ParaFrame
        repeated_names = set(name_counts[name_counts > 1].index)
        # filter out known meta files and extensions from the repeated names
        repeated_names = {name for name in repeated_names
                          if Path(name).stem.split(".")[0] not in KNOWN_META_FILES
                       and Path(name).suffix.lstrip(".").lower() not in META_EXTS_LOWER
                       and name != ".DS_Store"}

        if repeated_names:
            # find the rows in the meta ParaFrame that have repeated names
            is_repeated = meta_pf["path"].apply(lambda p: 
                                                Path(p).name in repeated_names)
            repeated_rows = meta_pf[is_repeated]
            # remove the repeated rows from the meta ParaFrame to avoid double counting
            meta_pf = meta_pf[~is_repeated]

            for filename in repeated_names:
                fmt_key = Path(filename).stem
                # find the rows in the repeated rows that match this filename
                rows = repeated_rows[repeated_rows["path"]
                                 .apply(lambda p: Path(p).name) == filename]
                # create a ParaFrame for the repeated rows and add it to data_branches
                data_branches.setdefault(fmt_key, {})[fmt_key] = ParaFrame(
                                 rows.to_dict("records"), base_path=root)
        
    # create dict with three keys, only data has subbranches
    tree = {}
    if not meta_pf.empty:
        tree["meta"] = meta_pf
    if data_branches:
        tree["data"] = data_branches
 
    # recursive L1 tree construction
    if data_type == "L1":
        # call build_tree for each subdirectory
        for subdir in sorted(p for p in root.iterdir() if p.is_dir()):
            # calls with drives will end recursion
            next_level = "L2" if subdir.name in extracted_dir_names else "L1"
            # append each subdirectory to the tree
            tree[subdir.name] = build_tree(subdir, fmt, data_type=next_level,
                                            _parser_cache=_parser_cache)
 
    return tree


def build_repo(tree: dict, repo_path: Path, dataset_name: str,
               worktree_root: Path, overwrite: bool = False,
               parser_cache: dict | None = None) -> "Repo":
    """
    Build a hallmark repository from a build_tree output.

    Args:
        tree: Build tree dictionary from build_tree function.
        repo_path: Path to create the hallmark repository.
        dataset_name: Name of the dataset for the repository.
        worktree_root: Path to the root of the worktree containing the data files.
        overwrite: If True, overwrite existing repository at repo_path.
        parser_cache: Optional cache of compiled parsers for the format strings.

        Returns:
            A Repo object representing the created hallmark repository.
    """

    repo_path = Path(repo_path).expanduser().resolve()
    if repo_path.exists():
        if overwrite:
            # remove the existing repo directory and its contents if overwrite is True
            shutil.rmtree(repo_path)
        else:
            raise FileExistsError(f'Repo already exists at "{repo_path}".')

    repo = Repo.init(repo_path)
    worktree_root = Path(worktree_root).expanduser().resolve()

    # root meta.yaml creation and commit
    meta_dict = {"dataset": dataset_name}
    # find all meta files in the tree and add them to the meta_dict
    if "meta" in tree and not tree["meta"].empty:
        meta_dict["files"] = tree["meta"]["path"].tolist()
    repo.dothm.dump_yml(meta_dict, "meta")
    repo.dothm.index.add(["meta.yml"])
    repo.dothm.index.commit(f"Initialize dataset: {dataset_name}")

    # one branch per fmt, one sub-branch per stem
    for fmt_str, fmt_dict in tree.get("data", {}).items():
        for stem_key, stem_pf in fmt_dict.items():
            # skip the "all" stem and any non-ParaFrame stems
            if not isinstance(stem_pf, ParaFrame):
                continue
            # skip empty ParaFrames
            if stem_pf.empty:
                continue

            branch_name = _sanitize_branch_name(f"{fmt_str}/{stem_key}")
            # check if the branch already exists, and create it if not
            existing = {h.name for h in repo.dothm.heads}
            if branch_name in existing:
                repo.dothm.git.checkout(branch_name)
            else:
                repo.dothm.git.checkout("-b", branch_name)
            repo.state = repo.dothm.load()

            repo.set_config(fmt=fmt_str)
            # add sha1 to stem ParaFrame
            stem_pf = stem_pf.copy()
            stem_pf["sha1"] = [
                Repo.checksum(worktree_root / path)
                for path in stem_pf["path"]]

            # convert the ParaFrame to a manifest
            try:
                # compile parsers for the fmt and its variants with missing parameters
                manifest = manifest_frame_from_pf(stem_pf, fmt_str)
                repo.state.replace(manifest)
                repo.dothm.dump(repo.state)

                # store objects
                for _, row in repo.state.data.iterrows():
                    match = stem_pf[stem_pf["sha1"] == row["sha1"]]
                    if not match.empty:
                        # store the file in the repo objects using its sha1
                        repo.objects.store(
                            worktree_root / match.iloc[0]["path"],
                            row["sha1"])

            except Exception as e:
                # manifest build failed — write file list to meta.yml instead
                repo.dothm.dump_yml({
                    "error": str(e),
                    "stem_key": stem_key,
                    "files": stem_pf["path"].tolist(),
                }, "meta")
                repo.dothm.index.add(["meta.yml"])

            repo.dothm.index.commit(
                f"Add stem: {stem_key}\nFmt: {fmt_str}\nDataset: {dataset_name}")

    # return to main
    repo.dothm.git.checkout("main")
    repo.state = repo.dothm.load()
    return repo