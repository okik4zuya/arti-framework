/* arti-annotate: JS mirror of tools/arti-annotate/annot.py (inline CriticMarkup annotations).
 * Parser/mutation behavior is pinned to tools/arti-annotate/fixtures.json by
 * tools/arti-annotate/test_annot_js.js -- change both implementations together.
 * The DOM helpers (markersToDom) are browser-only; everything else is pure. */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.ArtiAnnotate = factory();
})(typeof self !== "undefined" ? self : this, function () {
  var META = '(?<meta>\\{>>#(?<id>a\\d+) (?<status>open|revised)' +
    '(?: \\| was (?<was>"(?:[^"\\\\]|\\\\.)*"))?' +
    '(?: \\| (?<note>.*?))?<<\\})';
  var COMMENT_RE = new RegExp("\\{==(?<text>(?:(?!==\\}).)*)==\\}" + META, "gs");
  var SUGGEST_RE = new RegExp("\\{~~(?<old>(?:(?!~>|~~\\}).)*)~>(?<new>(?:(?!~~\\}).)*)~~\\}" + META, "gs");
  var FENCE_RE = /^[ \t]{0,3}(`{3,}|~{3,}).*?(?:^[ \t]{0,3}\1[`~]*[ \t]*$|(?![\s\S]))/gms;
  var INLINE_CODE_RE = /(`+)(?!`).+?(?<!`)\1(?!`)/gs;
  var MK = "";

  function protectedRanges(text) {
    var ranges = [], m;
    FENCE_RE.lastIndex = 0;
    while ((m = FENCE_RE.exec(text))) { ranges.push([m.index, m.index + m[0].length]); if (!m[0].length) FENCE_RE.lastIndex++; }
    INLINE_CODE_RE.lastIndex = 0;
    while ((m = INLINE_CODE_RE.exec(text))) {
      var s = m.index;
      if (!ranges.some(function (r) { return r[0] <= s && s < r[1]; })) ranges.push([s, s + m[0].length]);
    }
    return ranges;
  }

  function parse(text) {
    var prot = protectedRanges(text), out = [];
    [["comment", COMMENT_RE], ["suggestion", SUGGEST_RE]].forEach(function (pair) {
      var kind = pair[0], rx = pair[1], m;
      rx.lastIndex = 0;
      while ((m = rx.exec(text))) {
        var start = m.index;
        if (prot.some(function (r) { return r[0] <= start && start < r[1]; })) continue;
        var g = m.groups;
        var a = {
          id: g.id, kind: kind, status: g.status, start: start, end: start + m[0].length,
          metaStart: start + m[0].length - g.meta.length,
          was: g.was ? JSON.parse(g.was) : null, note: g.note || ""
        };
        if (kind === "comment") a.text = g.text; else { a.old = g.old; a.new = g.new; }
        out.push(a);
      }
    });
    out.sort(function (a, b) { return a.start - b.start; });
    return out;
  }

  function find(text, id) {
    var list = parse(text);
    for (var i = 0; i < list.length; i++) if (list[i].id === id) return list[i];
    throw new Error("annotation " + id + " not found");
  }
  function splice(text, a, rep) { return text.slice(0, a.start) + rep + text.slice(a.end); }
  function quoteWas(s) { return JSON.stringify(s).split("<<}").join("\\u003c<}"); }
  function cleanNote(n) { return (n || "").split("<<}").join("< <}").replace(/\s*\n\s*/g, " ").trim(); }
  function metaOf(id, status, was, note) {
    note = cleanNote(note);
    return "{>>#" + id + " " + status + (was !== null && was !== undefined ? " | was " + quoteWas(was) : "") +
      (note ? " | " + note : "") + "<<}";
  }

  function strip(text) {
    var list = parse(text);
    for (var i = list.length - 1; i >= 0; i--) {
      var a = list[i];
      text = splice(text, a, a.kind === "comment" ? a.text : a.old);
    }
    return text;
  }
  function accept(text, id) {
    var a = find(text, id);
    return splice(text, a, a.kind === "comment" ? a.text : a.new);
  }
  function revert(text, id) {
    var a = find(text, id);
    if (a.kind === "suggestion") return splice(text, a, a.old);
    return splice(text, a, a.status === "revised" && a.was !== null ? a.was : a.text);
  }
  function nextId(text) {
    var max = 0;
    parse(text).forEach(function (a) { max = Math.max(max, parseInt(a.id.slice(1), 10)); });
    return "a" + (max + 1);
  }
  function checkFree(text, start, end) {
    parse(text).forEach(function (a) {
      if (start < a.end && end > a.start) throw new Error("span overlaps annotation " + a.id);
    });
    protectedRanges(text).forEach(function (r) {
      if (start < r[1] && end > r[0]) throw new Error("span touches code");
    });
  }
  function addComment(text, start, end, note) {
    var span = text.slice(start, end);
    if (!span || span.indexOf("==}") >= 0) throw new Error("cannot annotate this span");
    checkFree(text, start, end);
    return text.slice(0, start) + "{==" + span + "==}" + metaOf(nextId(text), "open", null, note) + text.slice(end);
  }
  function addSuggestion(text, start, end, newText, note) {
    var old = text.slice(start, end);
    if (!old || /~>|~~\}/.test(old) || /~>|~~\}/.test(newText)) throw new Error("cannot suggest an edit on this span");
    checkFree(text, start, end);
    return text.slice(0, start) + "{~~" + old + "~>" + newText + "~~}" + metaOf(nextId(text), "open", null, note) + text.slice(end);
  }
  // Dashboard-only helpers (no Python twin needed: the CLI/Claude never edits notes this way).
  function setNote(text, id, note) {
    var a = find(text, id);
    var meta = metaOf(id, a.status, a.was, note);
    return text.slice(0, a.metaStart) + meta + text.slice(a.end);
  }
  function setSuggestionNew(text, id, newText) {
    var a = find(text, id);
    if (a.kind !== "suggestion" || /~>|~~\}/.test(newText)) throw new Error("cannot edit this suggestion");
    return text.slice(0, a.start) + "{~~" + a.old + "~>" + newText + "~~}" + text.slice(a.metaStart);
  }

  // ---- rendering: swap annotations for private-use markers before marked.parse,
  // then turn the markers into <mark> elements after the HTML is in the DOM, so a
  // span crossing paragraph/inline-format boundaries never produces broken nesting.
  function repOf(a) {
    return a.kind === "comment"
      ? MK + "C" + a.id + MK + a.text + MK + "/" + MK
      : MK + "S" + a.id + MK + a.old + MK + "|" + MK + a.new + MK + "/" + MK;
  }
  function toMarkers(text) {
    var list = parse(text);
    for (var i = list.length - 1; i >= 0; i--) text = splice(text, list[i], repOf(list[i]));
    return { text: text, annotations: list };
  }
  // Offset in toMarkers(text).text -> offset in the original text (an offset inside a
  // replaced annotation maps to that annotation's start).
  function markedToRaw(annotations, p) {
    var delta = 0;
    for (var i = 0; i < annotations.length; i++) {
      var a = annotations[i], rl = repOf(a).length, ns = a.start + delta;
      if (p >= ns + rl) { delta += (a.end - a.start) - rl; continue; }
      if (p > ns) return a.start;
      break;
    }
    return p + delta;
  }

  function markersToDom(rootEl, annotations) {
    var byId = {};
    annotations.forEach(function (a) { byId[a.id] = a; });
    var doc = rootEl.ownerDocument;
    var walker = doc.createTreeWalker(rootEl, 4 /* SHOW_TEXT */);
    var nodes = [], n;
    while ((n = walker.nextNode())) nodes.push(n);
    var state = null; // {id, kind: "comment"|"del"|"ins"}
    var re = /([^]*)/g;
    function wrap(str) {
      var a = byId[state.id];
      var mark = doc.createElement("mark");
      mark.setAttribute("data-id", state.id);
      mark.className = "annot " + (state.kind === "comment" ? "annot-" + (a ? a.status : "open") : "annot-suggest");
      var inner = mark;
      if (state.kind !== "comment") inner = mark.appendChild(doc.createElement(state.kind));
      inner.textContent = str;
      return mark;
    }
    nodes.forEach(function (node) {
      var s = node.nodeValue;
      if (!state && s.indexOf(MK) < 0) return;
      var frag = doc.createDocumentFragment(), last = 0, m;
      re.lastIndex = 0;
      function emit(str) {
        if (!str) return;
        frag.appendChild(state ? wrap(str) : doc.createTextNode(str));
      }
      while ((m = re.exec(s))) {
        emit(s.slice(last, m.index));
        last = m.index + m[0].length;
        var code = m[1];
        if (code.charAt(0) === "C") state = { id: code.slice(1), kind: "comment" };
        else if (code.charAt(0) === "S") state = { id: code.slice(1), kind: "del" };
        else if (code === "|" && state) state = { id: state.id, kind: "ins" };
        else if (code === "/") state = null;
      }
      emit(s.slice(last));
      node.parentNode.replaceChild(frag, node);
    });
  }

  // ---- selection -> source offsets ----
  function commonSuffixLen(a, b) {
    var i = 0;
    while (i < a.length && i < b.length && a[a.length - 1 - i] === b[b.length - 1 - i]) i++;
    return i;
  }
  function commonPrefixLen(a, b) {
    var i = 0;
    while (i < a.length && i < b.length && a[i] === b[i]) i++;
    return i;
  }
  // Find `selected` in `source`. Occurrences inside annotation notes are ignored; if several
  // remain, rendered-text context (prefix/suffix) picks the unique best one. Returns
  // {start,end} or null (not found / ambiguous).
  function locate(source, selected, prefix, suffix) {
    var sel = (selected || "").replace(/\r\n/g, "\n").trim();
    if (!sel) return null;
    var metas = parse(source).map(function (a) { return [a.metaStart, a.end]; });
    var hits = [], from = 0, i;
    while ((i = source.indexOf(sel, from)) >= 0) {
      from = i + 1;
      if (metas.some(function (r) { return i < r[1] && i + sel.length > r[0]; })) continue;
      hits.push(i);
    }
    if (!hits.length) return null;
    if (hits.length === 1) return { start: hits[0], end: hits[0] + sel.length };
    var best = -1, bestScore = 0, tie = false;
    hits.forEach(function (h) {
      var sc = commonSuffixLen(source.slice(Math.max(0, h - 40), h), prefix || "") +
               commonPrefixLen(source.slice(h + sel.length, h + sel.length + 40), suffix || "");
      if (sc > bestScore) { best = h; bestScore = sc; tie = false; } else if (sc === bestScore) tie = true;
    });
    return best >= 0 && !tie ? { start: best, end: best + sel.length } : null;
  }

  return {
    parse: parse, strip: strip, accept: accept, revert: revert, nextId: nextId,
    addComment: addComment, addSuggestion: addSuggestion, setNote: setNote,
    setSuggestionNew: setSuggestionNew, toMarkers: toMarkers, markedToRaw: markedToRaw, markersToDom: markersToDom,
    locate: locate, protectedRanges: protectedRanges
  };
});
