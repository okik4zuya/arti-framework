// Dev-only parity check: runs dashboard/lib/arti-annotate.js against fixtures.json.
// Usage: node test_annot_js.js   (not needed to run the dashboard; skipped if node is absent)
const assert = require("assert");
const path = require("path");
const A = require(path.join(__dirname, "..", "..", "dashboard", "lib", "arti-annotate.js"));
const fixtures = require("./fixtures.json");

for (const fx of fixtures) {
  const got = A.parse(fx.input);
  assert.strictEqual(got.length, fx.parse.length, fx.name + ": count");
  got.forEach((g, i) => { for (const k of Object.keys(fx.parse[i])) assert.deepStrictEqual(g[k], fx.parse[i][k], fx.name + ": " + k); });
  assert.strictEqual(A.strip(fx.input), fx.strip, fx.name + ": strip");
  for (const [id, want] of Object.entries(fx.accept)) assert.strictEqual(A.accept(fx.input, id), want, fx.name + ": accept " + id);
  for (const [id, want] of Object.entries(fx.revert)) assert.strictEqual(A.revert(fx.input, id), want, fx.name + ": revert " + id);
}

// mutations
let t = A.addComment("Make this concise. Keep that.", 0, 18, "shorter");
assert.strictEqual(t, "{==Make this concise.==}{>>#a1 open | shorter<<} Keep that.");
assert.strictEqual(A.setNote(t, "a1", "new note"), "{==Make this concise.==}{>>#a1 open | new note<<} Keep that.");
assert.throws(() => A.addComment(t, 0, 3, "x"), /overlaps/);
assert.throws(() => A.addComment("`code` here", 0, 4, "x"), /code/);
t = A.addSuggestion("We utilize it.", 3, 10, "use", "");
assert.strictEqual(A.accept(t, "a1"), "We use it.");
assert.strictEqual(A.setSuggestionNew(t, "a1", "employ"), "We {~~utilize~>employ~~}{>>#a1 open<<} it.");

// locate: unique, ambiguous resolved by context, note text ignored
assert.deepStrictEqual(A.locate("one two three", "two", "", ""), { start: 4, end: 7 });
const src = "cat sat. dog sat. cow sat.";
assert.deepStrictEqual(A.locate(src, "sat", "dog ", "."), { start: 13, end: 16 });
assert.strictEqual(A.locate(src, "sat", "", ""), null);
assert.strictEqual(A.locate("{==a==}{>>#a1 open | zebra<<} b", "zebra", "", ""), null);

// markers
const m = A.toMarkers("x {==hi==}{>>#a1 open<<} y {~~old~>new~~}{>>#a2 open<<}");
assert.strictEqual(m.annotations.length, 2);
assert.ok(!/\{==|\{~~/.test(m.text));
console.log("arti-annotate JS parity OK");
