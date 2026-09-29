# Free, open-source MCP options (no subscription at all)
## 1. OneCite — github.com/HzaCode/OneCite

MIT license, completely free, no API key needed for core use
Resolves DOIs/PMIDs/arXiv IDs/ISBNs/messy plain-text refs against Crossref, PubMed, arXiv; outputs BibTeX/CSL-JSON
Ambiguous matches get flagged for human review rather than silently guessed — good fit for ARTi-ref's dedup/verification step
Not a citation-sentiment tool like scite (doesn't tell you if a paper supports/contradicts a claim) — it's reference verification, not evidence classification


## 2. CiteTrue — citetrue.com

Resolves every reference against real bibliographic databases (not an LLM guessing) — closest match to scite's "does this citation actually check out" use case
Ships web, Chrome extension, Mac app, API, and MCP server
Couldn't confirm exact pricing (page didn't expose it), worth checking citetrue.com/pricing directly before committing

## 3. Community aggregator MCP servers (all free, open source, wrap Semantic Scholar + OpenAlex + Crossref + PubMed + arXiv):

openags/paper-search-mcp — broadest source coverage (arXiv, PubMed, bioRxiv, Semantic Scholar, OpenAlex, CORE, Zenodo, etc.)
xingyulu23/Academix — OpenAlex + DBLP + Semantic Scholar + arXiv + CrossRef, unified interface
pipeworx-io/mcp-openalex — OpenAlex only, good for citation-graph/institutional analysis These give you literature search + basic citation graphs for $0, but none classify citations as supporting/contradicting the way scite does — that's genuinely scite's differentiator.