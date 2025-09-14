Design
======

|hallmark|_ follows the
`Unix philosophy <https://en.wikipedia.org/wiki/Unix_philosophy#Origin>`_:

    Write programs that do one thing and do it well.
    Write programs to work together.
    Write programs to handle text streams, because that is a universal
    interface.

    -- Douglas McIlroy

The "one thing" for |hallmark|_ is maintaining a reproducible data
index.
With a well-designed indexing mechanism, it becomes natural to expose
a small set of core functions:

1.  **Add/remove:**
    find data from any source and bring them into the index.

2.  **Index:**
    compute checksums of data objects and index their relationships.

3.  **Log:**
    append immutable records.

4.  **View:**
    emit manifests of subsets for other tools to consume.

As |hallmark|_ develops, some commonly used plug-ins may be
distributed together with the |hallmark|_ package for convenience.


..  |hallmark| replace:: ``hallmark``

..  _hallmark: https://github.com/l6a/hallmark
