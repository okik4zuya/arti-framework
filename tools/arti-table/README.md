# arti-table

Table lane for ARTi-figure: a JSON spec in, an editable Markdown table out. Pure stdlib.

```
"~/.arti/python/python.exe" "~/.arti/tools/arti-table/render.py" --spec figures/Table_1.json --out-dir figures
```

Spec keys: `table` (name, also the output file name), `columns`, `rows`, optional `align`
(`left`/`center`/`right` per column) and `caption`. Output is `<table>.md`, ready to paste into the
manuscript source.
