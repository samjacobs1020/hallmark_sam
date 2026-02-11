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
import numpy as np
import string           # added for Formatter subclassing

from .helper_functions import *

class ParaFrame(pd.DataFrame):
    """
    A subclass of :class:`pandas.DataFrame` with added methods for
    parameterized file discovery and filtering.

    ``ParaFrame`` instances behave like ordinary DataFrames but add:

    * ``parse``: a classmethod that builds a table of file paths and parsed
      parameters from a format pattern (using ``glob`` + ``parse``).
    * ``__call__``/``filter``: convenience filtering by column values.
    """

    @property
    def _constructor(self):
        return ParaFrame

    def __call__(self, **kwds):
        return self.filter(**kwds)

    def filter(self, **kwargs):
        """
        Filter a pandas ``DataFrame`` by matching column values.

        This function utlizes provided **kwargs to filter an existing
        ``ParaFrame`` by masking based on column values. Filtering supports
        single- and multi-conditioned queries, returning rows that satisfy
        any of the provided conditions.

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
                mask |= np.isin(np.array(self[k]), np.array(v))
            else:
                mask |= np.array(self[k]) == v
        return self[mask]

    @classmethod
    def glob_search(cls, index = 0, _test_fmt = None, *args, debug=False, return_pattern=False,**kwargs):

        # Load and read Yaml file
        if _test_fmt != None:
            fmt = _test_fmt

            yaml_encodings = load_encodings_yaml(index,path=Path("/tmp/encoding_tmp.yaml"))
        else:
            yaml_encodings = load_encodings_yaml(index)
            fmt = yaml_encodings["fmt"]

        pmax = len(fmt) // 3  # to specify a parameter, we need at least
        # three characters '{p}'; the maximum number
        # of possible parameters is `len(fmt) // 3`.

        # Construct the glob pattern for search files
        pattern = fmt
        fmt_g = fmt


        for i in range(pmax):
            if debug:
                print(i, pattern, args, kwargs)
            try:
                pattern = pattern.format(*args, **kwargs)
                break
            except KeyError as e:
                k = e.args[0]
                pattern = re.sub(r"\{" + k + r":?.*?\}", "{" + k + ":s}", pattern)
                fmt_g = re.sub(r"\{" + k + r":?.*?\}", "{" + k + ":g}", fmt_g)
                kwargs[e.args[0]] = "*"

        # Obtain list of files based on the glob pattern
        globbed_files = sorted(glob(pattern))

        # Print the glob pattern and a summary of matches
        if debug == True:
            print(f'Pattern: "{pattern}"')
            n = len(globbed_files)
            if n > 1:
                print(f'{n} matches, e.g., "{globbed_files[0]}"')
            elif n > 0:
                print(f'{n} match, i.e., "{globbed_files[0]}"')
            else:
                print(f"No match; please check format string")

        return (globbed_files, pattern) if return_pattern else (yaml_encodings, fmt_g, globbed_files)

    @classmethod
    def parse(cls, index = 0, _test_fmt = None, *args, debug=False, **kwargs,): 
        """
        Construct a ``ParaFrame`` by parsing file paths that match a pattern.

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
    
        # Parse list of file names back to parameters

        yaml_encodings, fmt_g, globbed_files = cls.glob_search(index,_test_fmt, *args, debug=debug, **kwargs)
        parser = parse.compile(fmt_g)

        frame = []
        for f in globbed_files:
            f_new = regex_sub(f, yaml_encodings)
            r = parser.parse(f_new)
            if r is None:
                print(f'Failed to parse "{f}"')
            else:
                frame.append({'path':f, **r.named})
        return cls(frame)