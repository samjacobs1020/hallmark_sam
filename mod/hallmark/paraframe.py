# Copyright 2019 Chi-kwan Chan
# Copyright 2019 Steward Observatory
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from glob import glob

import re
import parse
import pandas as pd


def filter(self, **kwargs):
    """Filter a pandas ``DataFrame`` by matching column values.

    This function is monkey-patched onto :class:`pandas.DataFrame` as
    ``__call__``.
    It allow direct filtering of DataFrames with keyword arguments.

    Args:
        **kwargs: Arbitrary keyword arguments specifying column names
            and values to filter by.
            * If the value is a tuple or list, rows where the column
              matches any of those values are selected.
            * If the value is a scalar, rows where the column equals
              the value are selected.

    Returns:
        pandas.DataFrame: A filtered DataFrame containing only rows
            that match the given conditions.

    """
    mask = [False] * len(self)
    for k, v in kwargs.items():
        if isinstance(v, (tuple, list)):
            mask |= self[k].isin(v)
        else:
            mask |= self[k] == v
    return self[mask]


# Monkey patch pandas DataFrame
pd.DataFrame.__call__ = filter


def ParaFrame(fmt, *args, debug=False, **kwargs):
    """Construct a ``ParaFrame`` by parsing file paths that match a pattern.

    This function searches for files whose names match a formatted
    string pattern.
    The pattern can include python-style format fields (e.g.,
    ``{param}``) that will be extracted as structured information.
    Matching files are parsed and returned as rows in a pandas
    DataFrame.

    Args:
        fmt (str): A format string specifying the expected file naming
            pattern.
            Fields wrapped in ``{}`` will be extracted into columns.
        *args: Positional arguments used to fill the format string.
        debug (bool, optional): If True, prints debugging information
            about the matching process.
            Defaults to False.
        **kwargs: Keyword arguments used to fill the format string.
            If missing keys are encountered, they will be replaced by
            a wildcard ``*`` for globbing.

    Returns:
        pandas.DataFrame: A DataFrame where each row corresponds to a
            matched file.
            Includes:
            * ``path``: the full file path
            * additional columns extracted from the format fields

    Example:
        >>> from hallmark import ParaFrame
        >>> pf = ParaFrame("data/run{run:d}_p{parameter:d}.csv")
        >>> print(pf)
           path               run parameter
        0  data/run1_p10.csv  1   10
        1  data/run2_p20.csv  2   20

    """
    pmax = len(fmt) // 3  # to specify a parameter, we need at least
                          # three characters '{p}'; the maximum number
                          # of possible parameters is `len(fmt) // 3`.

    # Construct the glob pattern for search files
    pattern = fmt
    for i in range(pmax):
        if debug:
            print(i, pattern, args, kwargs)

        try:
            pattern = pattern.format(*args, **kwargs)
            break
        except KeyError as e:
            k = e.args[0]
            pattern = re.sub(r'\{'+k+':?.*?\}', '{'+k+':s}', pattern)
            kwargs[e.args[0]] = '*'

    # Obtain list of files based on the glob pattern
    files = sorted(glob(pattern))

    if debug:
        print(f'Pattern: "{pattern}"')
        n = len(files)
        if n > 1:
            print(f'{n} matches, e.g., "{files[0]}"')
        elif n > 0:
            print(f'{n} match, i.e., "{files[0]}"')
        else:
            print(f'No match; please check format string')

    # Parse list of file names back to parameters
    parser = parse.compile(fmt)

    l = []
    for f in files:
        r = parser.parse(f)
        if r is None:
            print(f'Failed to parse "{f}"')
        else:
            l.append({'path':f, **r.named})
    return pd.DataFrame(l)
