|hallmark|_
===========

    Reproducibility is the |hallmark|_ of the scientific method.

Modern science has become so complex that many science projects rely
on multiple software packages to work in unison, resulting in networks of
data products along the analyses.
Versioning and managing these data products are essential in making
modern data- and computation-intensive science reproducible.

Motivated by the `Event Horizon Telescope (EHT) <eht_>`_'s
observational data calibration pipelines and theory data analyses
tools, |hallmark|_ is a lightweight package designed to version
control and manage data products in a complex workflow.
It provides a simple abstraction and a uniform Application Programming
Interface (API) on top of different backend technologies such as
`POSIX file system <https://en.wikipedia.org/wiki/Unix_filesystem>`_,
`object storage    <https://aws.amazon.com/s3/>`_,
`globus            <https://www.globus.org/>`_,
`iRODS             <https://irods.org/>`_,
`stream            <https://en.wikipedia.org/wiki/Streaming_data>`_,
etc.
By using |hallmark|_ with other packages such as |yukon|_ and
|banyan|_ in `Project Laniakea <l6a_>`_, researchers can utilize
computing infrastructures in a global scale to accelerate their
science.


..  |hallmark| replace:: ``hallmark``
..  |yukon|    replace:: ``yukon``
..  |banyan|   replace:: ``banyan``

..  _l6a:      https://github.com/l6a
..  _hallmark: https://github.com/l6a/hallmark
..  _yukon:    https://github.com/l6a/yukon
..  _banyan:   https://github.com/l6a/banyan
..  _eht:      https://eventhorizontelescope.org


``ParaFrame``
-------------

When performing large scale parameter surveys and constructing
simulation libraries, it is common to encode parameter values in the
file paths.
Example include ``Ma+0.94_i70/sed_Rh160.h5``.
|hallmark|_ provides a subclassed ``pandas`` ``DataFrame``, called
``ParaFrame``, to decode file paths back to proper parameters, and put
the result into a ``pandas`` ``DataFrame``.
``ParaFrame`` uses python `parse` to parse the file paths.
Because ``parse`` is the opposite of ``format``, this means the format string
used to generate the surveys and libraries in the first place can be
reused.
In addition, ``ParaFrame`` has a nice interface to perform filter, which
makes parameter selection much easier than pure ``pandas``.

Tutorial
--------

Examples of using ``ParaFrame`` can be found in the Jupyter Notebook ``demos/ParaFrame.ipynb``.

