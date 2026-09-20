# Vendored CodeMirror 6

Fully offline build of the CodeMirror 6 pieces the dashboard's file-edit mode
needs (`@codemirror/state`, `@codemirror/view`, `@codemirror/commands`,
`@codemirror/search`, plus their transitive dependencies). No file here ever
fetches anything from the network at runtime — every `import` is a relative
path to another file in this folder.

## Why not a single CDN bundle

CodeMirror 6 ships only as ES modules with no traditional single-file
UMD/global build (unlike `dashboard/lib/marked.min.js`, `katex.min.js`, or
`pdf.min.js`). The `codemirror` npm meta-package's own bundle
(`esm.sh/codemirror@6.x?bundle`) only re-exports `EditorView`/`basicSetup`/
`minimalSetup` — not the individual pieces (`EditorState`, `Prec`, `keymap`,
`search`, `setSearchQuery`, …) the dashboard's search-bar integration needs.
So instead this folder vendors the actual dependency graph as separate flat
files, each esm.sh `es2022` build with its import specifiers rewritten from
esm.sh's semver-range paths (e.g. `/@codemirror/state@^6.7.0?target=es2022`)
to plain local relative paths (`./state.mjs`).

## Files and versions vendored (2026-09-20)

| Local file | Package@version |
|---|---|
| `state.mjs` | `@codemirror/state@6.7.5` |
| `view.mjs` | `@codemirror/view@6.43.12` |
| `commands.mjs` | `@codemirror/commands@6.11.1` |
| `search.mjs` | `@codemirror/search@6.7.2` |
| `language.mjs` | `@codemirror/language@6.12.4` (transitive dep of `commands`/`view`) |
| `lezer-common.mjs` | `@lezer/common@1.5.2` |
| `lezer-highlight.mjs` | `@lezer/highlight@1.2.3` |
| `find-cluster-break.mjs` | `@marijn/find-cluster-break@1.0.4` |
| `crelt.mjs` | `crelt@1.0.7` |
| `style-mod.mjs` | `style-mod@4.1.4` |
| `w3c-keyname.mjs` | `w3c-keyname@2.2.8` |

Each file's header comment records its own source. All versions were
resolved consistently in one crawl of `https://esm.sh/@codemirror/{state,view,commands,search}`
(no version pin, letting esm.sh resolve each package's semver ranges), so
there is exactly one copy of every shared dependency (in particular
`state.mjs`, which both `view.mjs` and `commands.mjs` depend on) — no
duplicate/incompatible copies of CodeMirror's internal state machinery.

## Re-vendoring / upgrading

1. Fetch the four entry packages fresh (no version, so esm.sh resolves
   current latest-compatible versions consistently):
   `curl https://esm.sh/@codemirror/state`, `.../view`, `.../commands`,
   `.../search` — each returns a small shim `import`ing further esm.sh paths.
2. Follow every `from"/..."` / `import"/..."` specifier recursively, fetching
   each until no new absolute-path specifiers appear. Confirm each package
   name resolves to exactly one concrete version across the whole graph
   (that's what guarantees no duplication) before proceeding.
3. Copy each leaf `.../es2022/<name>.mjs` file into this folder under the
   flat names in the table above, then rewrite each file's remaining
   `/<pkg>@^<range>?target=es2022` import specifiers to the matching local
   `./<flatname>.mjs` path.
4. Update the version table above and each file's header comment.

## Usage

`dashboard/arti-dashboard.html` imports named exports directly from these
files in a `<script type="module">` block, e.g.
`import { EditorView, keymap, lineNumbers } from "/lib/codemirror/view.mjs";`
— see that file for the full list of imports and how they're assembled into
the file-edit editor.
