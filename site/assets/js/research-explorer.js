// cintnet.org: Interactive Research Workspace & Planar Ledger Explorer (/research/)
// Progressive enhancement: static HTML renders the 7 track anchor rows and full 7-track directory without JS.
// Strict DOM safety: uses createElement and textContent only, with zero dynamic evaluation or network requests.
(function () {
  "use strict";

  var catalogEl = document.getElementById("research-catalog-data");
  var resultsEl = document.getElementById("rx-results");
  var ledgerColsEl = document.getElementById("rx-ledger-cols");
  var statusEl = document.getElementById("rx-result-status");
  var searchInput = document.getElementById("rx-search-input");
  var resetBtn = document.getElementById("rx-reset-btn");
  var moreWrap = document.getElementById("rx-more-wrap");
  var moreBtn = document.getElementById("rx-more-btn");
  var constellationFig = document.getElementById("ex-theme-constellation");
  var readoutEl = document.getElementById("rx-constellation-readout");
  var activeFilterBar = document.getElementById("rx-active-filter-bar");
  var mobileFiltersEl = document.getElementById("rx-mobile-filters");
  var mobileTrackLabelEl = document.getElementById("rx-mobile-track-label");

  if (!catalogEl || !resultsEl) return;

  var catalog;
  try {
    catalog = JSON.parse(catalogEl.textContent || "{}");
  } catch (err) {
    return;
  }

  var themes = Array.isArray(catalog.themes) ? catalog.themes : [];
  var items = Array.isArray(catalog.items) ? catalog.items : [];
  if (!items.length) return;

  var ANCHOR_IDS = ["M15", "M10", "M01", "M02", "M34", "M61", "M58"];

  var DEFAULT_ARCS = [
    {
      id: "M05+M09",
      parts: ["M05", "M09"],
      title: "Personal preference reclamation and on-device alignment",
      summary:
        "Part I (M05) separates genuine personal interests from engagement-bait clicks, and Part II (M09) aligns compact on-device preference models without flattening people into one global average."
    },
    {
      id: "M11+M12",
      parts: ["M11", "M12"],
      title: "Concentric privacy provenance and sub-second selective disclosure",
      summary:
        "Part I (M11) organizes shared provenance records into concentric trust circles, and Part II (M12) proves age, eligibility, or authority in under a second without exposing raw credentials."
    },
    {
      id: "M16+M18",
      parts: ["M16", "M18"],
      title: "Anti-collusion relay gateways and failure-pruned specialist routing",
      summary:
        "Part I (M16) bounds hidden signaling across multi-agent relays through rephrasing gateways, and Part II (M18) routes tasks across sparse specialist graphs that prune failing branches early."
    },
    {
      id: "M32+M33",
      parts: ["M32", "M33"],
      title: "Multi-dimensional contribution records and unlinkable competence credentials",
      summary:
        "Part I (M32) records upkeep, safety, ecological care, and mentorship on separate axes, and Part II (M33) verifies project-relevant skill without creating linkable global rankings."
    },
    {
      id: "M36+M37",
      parts: ["M36", "M37"],
      title: "Circulation-preserving mutual credit buffers and collusion-resistant community grants",
      summary:
        "Part I (M36) protects household baseline balances while recycling idle surplus above a high threshold, and Part II (M37) routes expiring surplus into cluster-audited community grants."
    },
    {
      id: "M41+M52",
      parts: ["M41", "M52"],
      title: "Autonomy-supportive civic quests and offline-inclusive batch governance",
      summary:
        "Part I (M41) decomposes civic maintenance into finite tasks without manipulative streaks, and Part II (M52) adds delay-tolerant batch relays so offline communities hold equal voice."
    },
    {
      id: "M42+M51",
      parts: ["M42", "M51"],
      title: "Socratic on-task skill scaffolding and developmental guardrails for young learners",
      summary:
        "Part I (M42) coaches adult learners step by step during real work to prevent skill atrophy, and Part II (M51) enforces attempt-first hints and non-anthropomorphic boundaries for students."
    },
    {
      id: "M43+M48",
      parts: ["M43", "M48"],
      title: "Fair chore-and-craft rotation with scheduled sabbatical cooldowns",
      summary:
        "Part I (M43) rotates shared chores and skilled craft around fatigue limits, and Part II (M48) enforces scheduled sabbaticals and workload caps against burnout."
    },
    {
      id: "M57+M59",
      parts: ["M57", "M59"],
      title: "Pre-deployment statutory stress-testing and verifiable municipal policy sharing",
      summary:
        "Part I (M57) stress-tests draft laws for clause conflicts and household harm before rollout, and Part II (M59) pairs participatory budgeting with runtime safety checks across cities."
    },
    {
      id: "M62+M63",
      parts: ["M62", "M63"],
      title: "Cross-chassis embodiment leases and hardware kinetic safety interlocks",
      summary:
        "Part I (M62) binds robot actuators across chassis types to expiring safety leases, and Part II (M63) enforces physical force limits in dedicated hardware interlocks."
    }
  ];

  var themeById = {};
  themes.forEach(function (t) {
    themeById[t.id] = t;
  });

  var itemById = {};
  var paperById = {};
  items.forEach(function (it) {
    itemById[it.id] = it;
    if (it.kind === "paper") {
      paperById[it.id] = it;
    }
  });

  function normText(val) {
    var s = String(val || "")
      .replace(/[\u2010-\u2015\u2212]/g, "-")
      .replace(/\u0131/g, "i");
    if (typeof s.normalize === "function") {
      s = s.normalize("NFKD").replace(/[\u0300-\u036f]/g, "");
    }
    return s.toLowerCase();
  }

  function pad2(num) {
    var n = parseInt(num, 10) || 0;
    return n < 10 ? "0" + String(n) : String(n);
  }

  // Precompute normalized search haystack for instant multi-token matching
  items.forEach(function (it) {
    var parts = [
      it.id || "",
      it.title || "",
      it.formal_title || "",
      it.summary || "",
      it.keywords || "",
      it.track || "",
      it.category || "",
      it.status || ""
    ];
    if (Array.isArray(it.themes)) {
      it.themes.forEach(function (tid) {
        var th = themeById[tid];
        if (th) {
          parts.push("theme " + tid);
          parts.push("track " + tid);
          parts.push("track " + pad2(tid));
          parts.push(th.short || "");
          parts.push(th.title || "");
        }
      });
    }
    if (Array.isArray(it.essays)) {
      it.essays.forEach(function (e) {
        if (e && e.title) parts.push(e.title);
      });
    }
    if (Array.isArray(it.papers)) {
      it.papers.forEach(function (pid) {
        parts.push(pid);
        if (paperById[pid]) {
          parts.push(paperById[pid].title || "");
          parts.push(paperById[pid].formal_title || "");
        }
      });
    }
    var joined = normText(parts.join(" "));
    it._haystack = " " + joined + " " + joined.replace(/-/g, " ") + " ";
  });

  // Build consolidated 2-part research arcs (69 distinct papers -> 59 consolidated arcs)
  var rawArcDefs = Array.isArray(catalog.arcs) && catalog.arcs.length ? catalog.arcs : DEFAULT_ARCS;
  var arcByPaperId = {};
  var arcsList = [];

  rawArcDefs.forEach(function (def) {
    if (!def || !Array.isArray(def.parts) || def.parts.length !== 2) return;
    var p1 = paperById[def.parts[0]];
    var p2 = paperById[def.parts[1]];
    if (!p1 || !p2) return;

    var mergedThemes = [];
    [p1.themes, p2.themes].forEach(function (tArr) {
      if (!Array.isArray(tArr)) return;
      tArr.forEach(function (tid) {
        if (mergedThemes.indexOf(tid) === -1) mergedThemes.push(tid);
      });
    });

    var mergedEssays = [];
    var seenEssayUrls = {};
    [p1.essays, p2.essays].forEach(function (eArr) {
      if (!Array.isArray(eArr)) return;
      eArr.forEach(function (es) {
        if (es && es.url && !seenEssayUrls[es.url]) {
          seenEssayUrls[es.url] = true;
          mergedEssays.push(es);
        }
      });
    });

    var s1 = p1.status || "Our proposal";
    var s2 = p2.status || "Our proposal";
    var statusLabel = s1 === s2 ? s1 : s1 + " \u00B7 " + s2;
    var primaryStatus = s1 === "Open question" || s2 === "Open question" ? "Open question" : s1;
    var arcId = def.id || (p1.id + "+" + p2.id);
    var codeLabel = "ARC \u00B7 " + p1.id + " + " + p2.id;
    var combinedPages = (parseInt(p1.pages, 10) || 0) + (parseInt(p2.pages, 10) || 0);

    var arcMetaJoined = normText([arcId, codeLabel, def.title || "", def.summary || ""].join(" "));
    var arcObj = {
      id: arcId,
      kind: "arc",
      codeLabel: codeLabel,
      parts: [p1.id, p2.id],
      part1: p1,
      part2: p2,
      title: def.title || (p1.title + " & " + p2.title),
      summary: def.summary || (p1.summary + " " + p2.summary),
      pages: combinedPages,
      themes: mergedThemes,
      status: primaryStatus,
      statusLabel: statusLabel,
      essays: mergedEssays,
      _sortKey: p1.id,
      _haystack:
        " " +
        arcMetaJoined +
        " " +
        arcMetaJoined.replace(/-/g, " ") +
        p1._haystack +
        p2._haystack
    };

    arcsList.push(arcObj);
    arcByPaperId[p1.id] = arcObj;
    arcByPaperId[p2.id] = arcObj;
  });

  var arcModeItems = [];
  var emittedArcIds = {};
  items.forEach(function (it) {
    if (it.kind === "paper" && arcByPaperId[it.id]) {
      var arc = arcByPaperId[it.id];
      if (!emittedArcIds[arc.id]) {
        emittedArcIds[arc.id] = true;
        arcModeItems.push(arc);
      }
    } else {
      arcModeItems.push(it);
    }
  });

  var viewBtns = Array.prototype.slice.call(document.querySelectorAll(".rx-view-btn[data-view-mode]"));
  var typeBtns = Array.prototype.slice.call(document.querySelectorAll(".rx-filter-btn[data-type]"));
  var themeBtns = Array.prototype.slice.call(document.querySelectorAll(".rx-theme-btn[data-theme-btn]"));
  var mapNodes = constellationFig
    ? Array.prototype.slice.call(constellationFig.querySelectorAll(".rx-node[data-theme]"))
    : [];
  var mapEdges = constellationFig
    ? Array.prototype.slice.call(constellationFig.querySelectorAll(".rx-edge"))
    : [];

  var state = {
    type: "all",
    theme: 0,
    query: "",
    view: "distinct",
    showAll: false,
    expanded: {}
  };

  function clearNode(el) {
    while (el.firstChild) {
      el.removeChild(el.firstChild);
    }
  }

  function makeEl(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  function statusPipClass(statusText) {
    if (statusText === "Established") return "rx-pip rx-pip-est";
    if (statusText === "Open question") return "rx-pip rx-pip-open";
    return "rx-pip rx-pip-prop";
  }

  function isPaperEntry(it) {
    return it.kind === "paper" || it.kind === "arc";
  }

  function buildArcPartSpec(partTag, paperObj) {
    var col = makeEl("div", "rx-arc-part");
    var kicker = makeEl("p", "rx-arc-part-kicker");
    kicker.appendChild(makeEl("span", statusPipClass(paperObj.status), "\u25A0 "));
    kicker.appendChild(
      document.createTextNode(
        partTag +
          " \u00B7 [" +
          paperObj.id +
          "] \u00B7 " +
          (paperObj.pages ? paperObj.pages + " pp." : "PDF") +
          " \u00B7 " +
          (paperObj.status || "Our proposal")
      )
    );
    col.appendChild(kicker);

    var h4 = makeEl("h4", "rx-arc-part-title");
    var pLink = makeEl("a", "rx-row-link", paperObj.title);
    pLink.setAttribute("href", paperObj.url);
    h4.appendChild(pLink);
    col.appendChild(h4);

    if (paperObj.summary) {
      col.appendChild(makeEl("p", "rx-arc-part-summary", paperObj.summary));
    }

    if (paperObj.formal_title) {
      var formalP = makeEl("p", "rx-arc-part-formal");
      formalP.appendChild(makeEl("strong", "rx-pairs-label", "Formal report title: "));
      formalP.appendChild(document.createTextNode(paperObj.formal_title));
      col.appendChild(formalP);
    }

    var pdfBtn = makeEl("a", "rx-btn-open", "[" + partTag + " PDF \u2197]");
    pdfBtn.setAttribute("href", paperObj.url);
    pdfBtn.setAttribute("aria-label", "Open " + partTag + " PDF for " + paperObj.id + ": " + paperObj.title);
    col.appendChild(pdfBtn);

    return col;
  }

  function buildArcRow(arc) {
    var p1 = arc.part1;
    var p2 = arc.part2;
    var row = makeEl("article", "rx-row rx-row-paper rx-row-arc");
    row.setAttribute("data-item-id", arc.id);
    row.setAttribute("data-arc-parts", p1.id + "," + p2.id);

    var mainGrid = makeEl("div", "rx-row-main rx-row-main-arc");

    // Col 1: Monospace arc index ("ARC · M05 + M09")
    var codeCell = makeEl("div", "rx-cell-code");
    var codeTag = makeEl("span", "rx-code-tag is-paper is-arc", arc.codeLabel);
    codeCell.appendChild(codeTag);
    mainGrid.appendChild(codeCell);

    // Col 2: Unified arc title + plain-language Part I + Part II scope summary
    var bodyCell = makeEl("div", "rx-cell-body");
    var h3 = makeEl("h3", "rx-row-title");
    var titleLink = makeEl("a", "rx-row-link", arc.title);
    titleLink.setAttribute("href", p1.url);
    h3.appendChild(titleLink);
    bodyCell.appendChild(h3);

    if (arc.summary) {
      bodyCell.appendChild(makeEl("p", "rx-row-formal", arc.summary));
    }
    mainGrid.appendChild(bodyCell);

    // Col 3: Primary Track + Epistemic status pip
    var trackCell = makeEl("div", "rx-cell-track");
    var primaryTid = Array.isArray(arc.themes) && arc.themes.length ? arc.themes[0] : 1;
    var trackBtn = makeEl("button", "rx-track-chip");
    trackBtn.setAttribute("type", "button");
    trackBtn.appendChild(makeEl("span", statusPipClass(arc.status), "\u25A0"));
    trackBtn.appendChild(document.createTextNode(" Track " + pad2(primaryTid)));
    trackBtn.setAttribute(
      "title",
      (themeById[primaryTid] ? themeById[primaryTid].title : "Track " + primaryTid) + " \u00B7 " + arc.statusLabel
    );
    trackBtn.addEventListener("click", function () {
      state.theme = state.theme === primaryTid ? 0 : primaryTid;
      state.showAll = false;
      render();
    });
    trackCell.appendChild(trackBtn);
    mainGrid.appendChild(trackCell);

    // Col 4: Combined page count
    var metaCell = makeEl("div", "rx-cell-extent", arc.pages + " pp.");
    metaCell.setAttribute(
      "title",
      "Combined extent: Part I (" + p1.id + ", " + p1.pages + " pp.) + Part II (" + p2.id + ", " + p2.pages + " pp.)"
    );
    mainGrid.appendChild(metaCell);

    // Col 5: Actions ([DETAILS +], [PART I PDF ↗], [PART II PDF ↗])
    var actionsCell = makeEl("div", "rx-cell-actions rx-cell-actions-arc");
    var drawerId = "rx-spec-" + String(arc.id).replace(/[^a-zA-Z0-9_-]/g, "-");
    var isOpen = Boolean(state.expanded[arc.id]);

    var arcEssayCount = Array.isArray(arc.essays) ? arc.essays.length : 0;
    var arcCollapsedText =
      "Details + (2 parts" + (arcEssayCount > 0 ? " \u00B7 " + arcEssayCount + (arcEssayCount === 1 ? " essay" : " essays") : "") + ")";
    var arcExpandedText = "Details \u2212";

    var detailsBtn = makeEl("button", "rx-btn-spec", isOpen ? arcExpandedText : arcCollapsedText);
    detailsBtn.setAttribute("type", "button");
    detailsBtn.setAttribute("aria-expanded", isOpen ? "true" : "false");
    detailsBtn.setAttribute("aria-controls", drawerId);

    var openPart1 = makeEl("a", "rx-btn-open", "[PART I PDF \u2197]");
    openPart1.setAttribute("href", p1.url);
    openPart1.setAttribute("aria-label", "Open Part I PDF for " + p1.id + ": " + p1.title);

    var openPart2 = makeEl("a", "rx-btn-open", "[PART II PDF \u2197]");
    openPart2.setAttribute("href", p2.url);
    openPart2.setAttribute("aria-label", "Open Part II PDF for " + p2.id + ": " + p2.title);

    actionsCell.appendChild(detailsBtn);
    actionsCell.appendChild(openPart1);
    actionsCell.appendChild(openPart2);
    mainGrid.appendChild(actionsCell);
    row.appendChild(mainGrid);

    // Expandable inline specification drawer covering both Part I and Part II
    var drawer = makeEl("div", "rx-row-drawer rx-arc-drawer");
    drawer.id = drawerId;
    drawer.hidden = !isOpen;

    var partsGrid = makeEl("div", "rx-arc-parts-grid");
    partsGrid.appendChild(buildArcPartSpec("PART I", p1));
    partsGrid.appendChild(buildArcPartSpec("PART II", p2));
    drawer.appendChild(partsGrid);

    var metaLine = makeEl("div", "rx-drawer-meta");
    var statusSpan = makeEl("span", "rx-drawer-status");
    statusSpan.appendChild(makeEl("span", statusPipClass(arc.status), "\u25A0 "));
    statusSpan.appendChild(document.createTextNode(arc.statusLabel));
    metaLine.appendChild(statusSpan);

    if (Array.isArray(arc.themes) && arc.themes.length) {
      arc.themes.forEach(function (tid) {
        var th = themeById[tid];
        if (!th) return;
        var jump = makeEl("a", "rx-drawer-tag", "Track " + pad2(tid) + " \u00B7 " + th.short);
        jump.setAttribute("href", th.anchor || ("#theme-" + tid));
        metaLine.appendChild(jump);
      });
    }
    drawer.appendChild(metaLine);

    if (Array.isArray(arc.essays) && arc.essays.length) {
      var pairsP = makeEl("p", "rx-drawer-pairs");
      pairsP.appendChild(makeEl("strong", "rx-pairs-label", "Companion essays: "));
      arc.essays.forEach(function (es, idx) {
        if (idx > 0) pairsP.appendChild(document.createTextNode(". "));
        var a = makeEl("a", null, es.title);
        a.setAttribute("href", es.url);
        pairsP.appendChild(a);
      });
      pairsP.appendChild(document.createTextNode("."));
      drawer.appendChild(pairsP);
    }

    detailsBtn.addEventListener("click", function () {
      var nextOpen = drawer.hidden;
      drawer.hidden = !nextOpen;
      state.expanded[arc.id] = nextOpen;
      detailsBtn.setAttribute("aria-expanded", nextOpen ? "true" : "false");
      detailsBtn.textContent = nextOpen ? arcExpandedText : arcCollapsedText;
    });

    row.appendChild(drawer);
    return row;
  }

  function buildLedgerRow(item) {
    if (item.kind === "arc") {
      return buildArcRow(item);
    }
    var isPaper = item.kind === "paper";
    var row = makeEl("article", isPaper ? "rx-row rx-row-paper" : "rx-row rx-row-essay");
    row.setAttribute("data-item-id", item.id);

    var mainGrid = makeEl("div", "rx-row-main");

    // Col 1: Monospace coordinate / ID cell
    var codeCell = makeEl("div", "rx-cell-code");
    var codeTag = makeEl("span", isPaper ? "rx-code-tag is-paper" : "rx-code-tag is-essay", isPaper ? "[" + item.id + "]" : "[ESSAY]");
    codeCell.appendChild(codeTag);
    mainGrid.appendChild(codeCell);

    // Col 2: Title + formal_title or summary preview
    var bodyCell = makeEl("div", "rx-cell-body");
    var h3 = makeEl("h3", "rx-row-title");
    var titleLink = makeEl("a", "rx-row-link", item.title);
    titleLink.setAttribute("href", item.url);
    h3.appendChild(titleLink);
    bodyCell.appendChild(h3);

    if (item.summary) {
      bodyCell.appendChild(makeEl("p", "rx-row-formal", item.summary));
    }
    mainGrid.appendChild(bodyCell);

    // Col 3: Primary Track + Epistemic status pip
    var trackCell = makeEl("div", "rx-cell-track");
    var primaryTid = Array.isArray(item.themes) && item.themes.length ? item.themes[0] : 1;
    var trackBtn = makeEl("button", "rx-track-chip");
    trackBtn.setAttribute("type", "button");
    trackBtn.appendChild(makeEl("span", statusPipClass(item.status), "\u25A0"));
    trackBtn.appendChild(document.createTextNode(" Track " + pad2(primaryTid)));
    trackBtn.setAttribute(
      "title",
      (themeById[primaryTid] ? themeById[primaryTid].title : "Track " + primaryTid) + " \u00B7 " + (item.status || "Our proposal")
    );
    trackBtn.addEventListener("click", function () {
      state.theme = state.theme === primaryTid ? 0 : primaryTid;
      state.showAll = false;
      render();
    });
    trackCell.appendChild(trackBtn);
    mainGrid.appendChild(trackCell);

    // Col 4: Extent (pages or reading minutes)
    var metaCell = makeEl(
      "div",
      "rx-cell-extent",
      isPaper ? (item.pages ? item.pages + " pp." : "PDF") : (item.minutes ? item.minutes + " min" : "Essay")
    );
    mainGrid.appendChild(metaCell);

    // Col 5: Actions (Details + hidden count and PDF ↗ / Essay ↗)
    var actionsCell = makeEl("div", "rx-cell-actions");
    var drawerId = "rx-spec-" + String(item.id).replace(/[^a-zA-Z0-9_-]/g, "-");
    var isOpen = Boolean(state.expanded[item.id]);

    var hiddenCountLabel = "";
    if (isPaper) {
      var cEssays = Array.isArray(item.essays) ? item.essays.length : 0;
      hiddenCountLabel = cEssays > 0 ? (cEssays + (cEssays === 1 ? " essay" : " essays")) : "2 notes";
    } else {
      var cPapers = Array.isArray(item.papers) ? item.papers.length : 0;
      hiddenCountLabel = cPapers > 0 ? (cPapers + (cPapers === 1 ? " paper" : " papers")) : "notes";
    }
    var collapsedBtnText = "Details + (" + hiddenCountLabel + ")";
    var expandedBtnText = "Details \u2212";

    var detailsBtn = makeEl("button", "rx-btn-spec", isOpen ? expandedBtnText : collapsedBtnText);
    detailsBtn.setAttribute("type", "button");
    detailsBtn.setAttribute("aria-expanded", isOpen ? "true" : "false");
    detailsBtn.setAttribute("aria-controls", drawerId);

    var openLink = makeEl("a", "rx-btn-open", isPaper ? "PDF \u2197" : "Essay \u2197");
    openLink.setAttribute("href", item.url);
    openLink.setAttribute("aria-label", (isPaper ? "Open PDF for " + item.id + ": " : "Read essay: ") + item.title);

    actionsCell.appendChild(detailsBtn);
    actionsCell.appendChild(openLink);
    mainGrid.appendChild(actionsCell);
    row.appendChild(mainGrid);

    // Expandable inline specification drawer
    var drawer = makeEl("div", "rx-row-drawer");
    drawer.id = drawerId;
    drawer.hidden = !isOpen;

    if (isPaper && item.formal_title) {
      var formalP = makeEl("p", "rx-drawer-summary");
      formalP.appendChild(makeEl("strong", "rx-pairs-label", "Formal report title: "));
      formalP.appendChild(document.createTextNode(item.formal_title));
      drawer.appendChild(formalP);
    } else if (item.summary) {
      drawer.appendChild(makeEl("p", "rx-drawer-summary", item.summary));
    }

    var metaLine = makeEl("div", "rx-drawer-meta");
    var statusSpan = makeEl("span", "rx-drawer-status");
    statusSpan.appendChild(makeEl("span", statusPipClass(item.status), "\u25A0 "));
    statusSpan.appendChild(document.createTextNode(item.status || "Our proposal"));
    metaLine.appendChild(statusSpan);

    if (Array.isArray(item.themes) && item.themes.length) {
      item.themes.forEach(function (tid) {
        var th = themeById[tid];
        if (!th) return;
        var jump = makeEl("a", "rx-drawer-tag", "Track " + pad2(tid) + " \u00B7 " + th.short);
        jump.setAttribute("href", th.anchor || ("#theme-" + tid));
        metaLine.appendChild(jump);
      });
    }
    drawer.appendChild(metaLine);

    if (isPaper && Array.isArray(item.essays) && item.essays.length) {
      var pairsP = makeEl("p", "rx-drawer-pairs");
      pairsP.appendChild(makeEl("strong", "rx-pairs-label", "Companion essays: "));
      item.essays.forEach(function (es, idx) {
        if (idx > 0) pairsP.appendChild(document.createTextNode(". "));
        var a = makeEl("a", null, es.title);
        a.setAttribute("href", es.url);
        pairsP.appendChild(a);
      });
      pairsP.appendChild(document.createTextNode("."));
      drawer.appendChild(pairsP);
    } else if (!isPaper && Array.isArray(item.papers) && item.papers.length) {
      var papersP = makeEl("p", "rx-drawer-pairs");
      papersP.appendChild(makeEl("strong", "rx-pairs-label", "Paired working papers: "));
      item.papers.forEach(function (pid, idx) {
        var pObj = paperById[pid];
        if (!pObj) return;
        if (idx > 0) papersP.appendChild(document.createTextNode(". "));
        var pa = makeEl("a", null, pid + " (" + pObj.title + ")");
        pa.setAttribute("href", pObj.url);
        papersP.appendChild(pa);
      });
      papersP.appendChild(document.createTextNode("."));
      drawer.appendChild(papersP);
    }

    detailsBtn.addEventListener("click", function () {
      var nextOpen = drawer.hidden;
      drawer.hidden = !nextOpen;
      state.expanded[item.id] = nextOpen;
      detailsBtn.setAttribute("aria-expanded", nextOpen ? "true" : "false");
      detailsBtn.textContent = nextOpen ? expandedBtnText : collapsedBtnText;
    });

    row.appendChild(drawer);
    return row;
  }

  function updateConstellationUI() {
    var activeTheme = state.theme;
    mapNodes.forEach(function (node) {
      var tid = parseInt(node.getAttribute("data-theme") || "0", 10);
      var isSelected = activeTheme !== 0 && tid === activeTheme;
      var isDimmed = activeTheme !== 0 && tid !== activeTheme;
      node.classList.toggle("is-active", isSelected);
      node.classList.toggle("is-dimmed", isDimmed);
      node.setAttribute("aria-pressed", isSelected ? "true" : "false");
    });

    mapEdges.forEach(function (edge) {
      var fromId = parseInt(edge.getAttribute("data-from") || "0", 10);
      var toId = parseInt(edge.getAttribute("data-to") || "0", 10);
      var touches = activeTheme !== 0 && (fromId === activeTheme || toId === activeTheme);
      var dimmed = activeTheme !== 0 && !touches;
      edge.classList.toggle("is-active", touches);
      edge.classList.toggle("is-dimmed", dimmed);
    });

    if (readoutEl) {
      clearNode(readoutEl);
      var totalEssayItems = items.filter(function (x) { return x.kind === "essay"; }).length;
      if (activeTheme === 0) {
        readoutEl.textContent =
          state.view === "arcs"
            ? "TELEMETRY: ALL 07 TRACKS ACTIVE \u00B7 Consolidated 59-arc view (10 two-part companion arcs + 49 standalone papers, " + totalEssayItems + " essays)."
            : "TELEMETRY: ALL 07 TRACKS ACTIVE \u00B7 Select any station above to trace cross-track dependencies and filter the " + items.length + "-item ledger.";
      } else {
        var th = themeById[activeTheme];
        if (th) {
          readoutEl.appendChild(makeEl("strong", null, "TRACK " + pad2(th.id) + " \u00B7 " + th.title + ": "));
          readoutEl.appendChild(document.createTextNode((th.connection || "") + " "));
          var jumpLink = makeEl("a", "rx-readout-jump", "Read Track " + pad2(th.id) + " notes \u2191");
          jumpLink.setAttribute("href", th.anchor || ("#theme-" + th.id));
          readoutEl.appendChild(jumpLink);
        }
      }
    }
  }

  function updateButtonsUI(allTypeMatches) {
    var totalAll = 0;
    var totalPapers = 0;
    var totalEssays = 0;

    allTypeMatches.forEach(function (it) {
      totalAll += 1;
      if (isPaperEntry(it)) totalPapers += 1;
      else if (it.kind === "essay") totalEssays += 1;
    });

    viewBtns.forEach(function (btn) {
      var mode = btn.getAttribute("data-view-mode") || "distinct";
      var active = mode === state.view;
      btn.classList.toggle("is-active", active);
      btn.setAttribute("aria-pressed", active ? "true" : "false");
    });

    typeBtns.forEach(function (btn) {
      var t = btn.getAttribute("data-type") || "all";
      var active = t === state.type;
      btn.classList.toggle("is-active", active);
      btn.setAttribute("aria-pressed", active ? "true" : "false");
      var countSpan = btn.querySelector(".rx-btn-count");
      if (countSpan) {
        if (t === "all") {
          countSpan.textContent = "(" + totalAll + ")";
        } else if (t === "paper") {
          if (state.view === "arcs") {
            countSpan.textContent = "(" + totalPapers + (totalPapers === 1 ? " arc)" : " arcs)");
          } else {
            countSpan.textContent = "(" + totalPapers + " PDFs)";
          }
        } else if (t === "essay") {
          countSpan.textContent = "(" + totalEssays + ")";
        }
      }
    });

    themeBtns.forEach(function (btn) {
      var tid = parseInt(btn.getAttribute("data-theme-btn") || "0", 10);
      var active = tid === state.theme;
      btn.classList.toggle("is-active", active);
      btn.setAttribute("aria-pressed", active ? "true" : "false");
    });

    var hasFilter =
      state.type !== "all" ||
      state.theme !== 0 ||
      state.query.trim().length > 0 ||
      state.view !== "distinct" ||
      state.showAll;
    if (resetBtn) {
      resetBtn.hidden = !hasFilter;
    }

    if (mobileTrackLabelEl) {
      if (state.theme !== 0 && themeById[state.theme]) {
        mobileTrackLabelEl.textContent = "Track " + pad2(state.theme) + " \u00B7 " + themeById[state.theme].short + ".";
      } else {
        mobileTrackLabelEl.textContent = "All 7 tracks.";
      }
    }

    var hasActiveQueryOrSlice =
      state.type !== "all" ||
      state.theme !== 0 ||
      state.query.trim().length > 0 ||
      state.view !== "distinct";
    if (activeFilterBar) {
      clearNode(activeFilterBar);
      if (!hasActiveQueryOrSlice) {
        activeFilterBar.hidden = true;
      } else {
        activeFilterBar.hidden = false;
        activeFilterBar.appendChild(makeEl("span", "rx-active-filter-kicker", "Active filters:"));
        if (state.theme !== 0 && themeById[state.theme]) {
          activeFilterBar.appendChild(
            makeEl("span", "rx-active-filter-chip", "Track " + pad2(state.theme) + " \u00B7 " + themeById[state.theme].short)
          );
        }
        if (state.type === "paper") {
          activeFilterBar.appendChild(
            makeEl("span", "rx-active-filter-chip", state.view === "arcs" ? "Format: Research arcs" : "Format: Working papers")
          );
        } else if (state.type === "essay") {
          activeFilterBar.appendChild(makeEl("span", "rx-active-filter-chip", "Format: Plain-language essays"));
        }
        if (state.view === "arcs") {
          activeFilterBar.appendChild(makeEl("span", "rx-active-filter-chip", "View: 59 consolidated arcs"));
        }
        if (state.query.trim()) {
          activeFilterBar.appendChild(makeEl("span", "rx-active-filter-chip", 'Search: "' + state.query.trim() + '"'));
        }
        var barResetBtn = makeEl("button", "rx-active-reset-btn", "Reset filters \u00D7");
        barResetBtn.setAttribute("type", "button");
        barResetBtn.addEventListener("click", function () {
          resetFilters();
          if (searchInput) searchInput.focus();
        });
        activeFilterBar.appendChild(barResetBtn);
      }
    }
  }

  function matchesToken(haystack, tok) {
    if (haystack.indexOf(tok) !== -1) return true;
    var tokSpace = tok.replace(/-/g, " ");
    if (/^[a-z0-9]-/.test(tok)) {
      return haystack.indexOf(" " + tokSpace + " ") !== -1;
    }
    return haystack.indexOf(tokSpace) !== -1;
  }

  function isExactIdMatch(item, rawQuery) {
    if (normText(item.id) === rawQuery) return true;
    if (item.kind === "arc" && Array.isArray(item.parts)) {
      return normText(item.parts[0]) === rawQuery || normText(item.parts[1]) === rawQuery;
    }
    return false;
  }

  function getMatches() {
    var rawQuery = normText(state.query).trim();
    var tokens = rawQuery ? rawQuery.split(/\s+/).filter(Boolean) : [];
    var isUnfilteredDefault =
      !tokens.length && state.theme === 0 && state.type === "all" && state.view === "distinct";

    var sourceList = state.view === "arcs" ? arcModeItems : items;
    var allTypeMatches = [];
    var filtered = [];

    sourceList.forEach(function (it) {
      if (state.theme !== 0) {
        if (!Array.isArray(it.themes) || it.themes.indexOf(state.theme) === -1) {
          return;
        }
      }
      if (tokens.length) {
        for (var i = 0; i < tokens.length; i++) {
          if (!matchesToken(it._haystack, tokens[i])) {
            return;
          }
        }
      }
      allTypeMatches.push(it);
      if (state.type === "all") {
        filtered.push(it);
      } else if (state.type === "paper" && isPaperEntry(it)) {
        filtered.push(it);
      } else if (state.type === "essay" && it.kind === "essay") {
        filtered.push(it);
      }
    });

    // Sort papers/arcs in canonical M01..M69 order before essays when browsing, or exact ID hits first when searching
    filtered.sort(function (a, b) {
      if (rawQuery) {
        var aExact = isExactIdMatch(a, rawQuery) ? 0 : 1;
        var bExact = isExactIdMatch(b, rawQuery) ? 0 : 1;
        if (aExact !== bExact) return aExact - bExact;
      }
      if (state.theme !== 0) {
        var aPrimary = Array.isArray(a.themes) && a.themes[0] === state.theme ? 0 : 1;
        var bPrimary = Array.isArray(b.themes) && b.themes[0] === state.theme ? 0 : 1;
        if (aPrimary !== bPrimary) return aPrimary - bPrimary;
      }
      var aPaper = isPaperEntry(a);
      var bPaper = isPaperEntry(b);
      if (aPaper !== bPaper) {
        return aPaper ? -1 : 1;
      }
      if (aPaper && bPaper) {
        var aKey = a._sortKey || a.id;
        var bKey = b._sortKey || b.id;
        return aKey.localeCompare(bKey);
      }
      return 0;
    });

    return {
      allTypeMatches: allTypeMatches,
      filtered: filtered,
      tokens: tokens,
      isUnfilteredDefault: isUnfilteredDefault
    };
  }

  function render() {
    var res = getMatches();
    var matches = res.filtered;

    updateConstellationUI();
    updateButtonsUI(res.allTypeMatches);

    clearNode(resultsEl);

    if (!matches.length) {
      if (ledgerColsEl) {
        ledgerColsEl.hidden = true;
      }
      var emptyBox = makeEl("div", "rx-empty");
      emptyBox.appendChild(
        makeEl(
          "p",
          null,
          "No working papers or essays matched your current filter. Clear the search query or switch back to All tracks."
        )
      );
      var clearBtn = makeEl("button", "rx-btn-spec", "Reset filters \u00D7");
      clearBtn.setAttribute("type", "button");
      clearBtn.addEventListener("click", resetFilters);
      emptyBox.appendChild(clearBtn);
      resultsEl.appendChild(emptyBox);

      if (statusEl) {
        statusEl.textContent = "0 items matched your current filter.";
      }
      if (moreWrap) {
        moreWrap.hidden = true;
      }
      return;
    }

    if (ledgerColsEl) {
      ledgerColsEl.hidden = false;
      ledgerColsEl.classList.toggle("is-arc-mode", state.view === "arcs");
    }

    // Default curated view: 7 flagship track anchor rows (zero layout jump from static HTML)
    var visible;
    var isCuratedAnchorView = res.isUnfilteredDefault && !state.showAll;
    if (isCuratedAnchorView) {
      visible = [];
      ANCHOR_IDS.forEach(function (aid) {
        if (itemById[aid]) visible.push(itemById[aid]);
      });
    } else {
      visible = matches;
    }

    var frag = document.createDocumentFragment();
    visible.forEach(function (it) {
      frag.appendChild(buildLedgerRow(it));
    });
    resultsEl.appendChild(frag);

    var paperEntryCount = 0;
    var underlyingPdfCount = 0;
    var pairArcCount = 0;
    var essayCount = 0;
    matches.forEach(function (it) {
      if (it.kind === "arc") {
        paperEntryCount += 1;
        pairArcCount += 1;
        underlyingPdfCount += 2;
      } else if (it.kind === "paper") {
        paperEntryCount += 1;
        underlyingPdfCount += 1;
      } else {
        essayCount += 1;
      }
    });

    if (statusEl) {
      if (isCuratedAnchorView) {
        statusEl.textContent =
          "Curated anchor index: 7 track flagship papers displayed (of " +
          underlyingPdfCount +
          " working papers and " +
          essayCount +
          " plain-language essays). Select a track, search by keyword, switch to 59 consolidated arcs, or expand all " +
          matches.length +
          " records.";
      } else {
        var parts = [];
        if (paperEntryCount > 0) {
          if (state.view === "arcs") {
            var arcPhrase =
              paperEntryCount +
              (paperEntryCount === 1 ? " consolidated research arc" : " consolidated research arcs") +
              " (" +
              underlyingPdfCount +
              (underlyingPdfCount === 1 ? " PDF" : " PDFs") +
              (pairArcCount > 0
                ? ", including " + pairArcCount + (pairArcCount === 1 ? " two-part arc" : " two-part arcs")
                : "") +
              ")";
            parts.push(arcPhrase);
          } else {
            parts.push(paperEntryCount + (paperEntryCount === 1 ? " working paper" : " working papers"));
          }
        }
        if (essayCount > 0) {
          parts.push(essayCount + (essayCount === 1 ? " plain-language essay" : " plain-language essays"));
        }
        var summaryStr = "Showing " + parts.join(" and ");
        if (state.theme !== 0 && themeById[state.theme]) {
          summaryStr += " in Track " + pad2(state.theme) + " (" + themeById[state.theme].title + ")";
        } else {
          summaryStr += " across all 07 tracks";
        }
        if (state.query.trim()) {
          summaryStr += ' matching "' + state.query.trim() + '"';
        }
        statusEl.textContent = summaryStr + ".";
      }
    }

    if (moreWrap && moreBtn) {
      if (isCuratedAnchorView) {
        moreWrap.hidden = false;
        moreBtn.textContent = "Show all " + matches.length + " working papers & plain-language essays +";
      } else {
        moreWrap.hidden = true;
      }
    }
  }

  function resetFilters() {
    state.type = "all";
    state.theme = 0;
    state.query = "";
    state.view = "distinct";
    state.showAll = false;
    if (searchInput) searchInput.value = "";
    render();
  }

  viewBtns.forEach(function (btn) {
    btn.addEventListener("click", function () {
      var nextMode = btn.getAttribute("data-view-mode") || "distinct";
      if (state.view === nextMode && state.showAll) return;
      state.view = nextMode;
      state.showAll = true;
      if (state.type === "essay") {
        state.type = "all";
      }
      render();
    });
  });

  typeBtns.forEach(function (btn) {
    btn.addEventListener("click", function () {
      state.type = btn.getAttribute("data-type") || "all";
      state.showAll = false;
      render();
    });
  });

  themeBtns.forEach(function (btn) {
    btn.addEventListener("click", function () {
      var nextTheme = parseInt(btn.getAttribute("data-theme-btn") || "0", 10);
      state.theme = state.theme === nextTheme && nextTheme !== 0 ? 0 : nextTheme;
      state.showAll = false;
      render();
    });
  });

  mapNodes.forEach(function (node) {
    var tid = parseInt(node.getAttribute("data-theme") || "0", 10);
    var toggleNode = function () {
      state.theme = state.theme === tid ? 0 : tid;
      state.showAll = false;
      render();
    };
    node.addEventListener("click", toggleNode);
    node.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        toggleNode();
      } else if (e.key === "Escape" && state.theme !== 0) {
        e.preventDefault();
        state.theme = 0;
        render();
      }
    });
  });

  if (searchInput) {
    searchInput.addEventListener("input", function () {
      state.query = searchInput.value || "";
      state.showAll = false;
      render();
    });
  }

  if (resetBtn) {
    resetBtn.addEventListener("click", function () {
      resetFilters();
      if (searchInput) searchInput.focus();
    });
  }

  if (moreBtn) {
    moreBtn.addEventListener("click", function () {
      state.showAll = true;
      render();
    });
  }

  if (window.innerWidth <= 640 && mobileFiltersEl) {
    mobileFiltersEl.open = false;
  }

  if (window.location && window.location.hash) {
    var m = window.location.hash.match(/^#theme-([1-7])$/);
    if (m) {
      state.theme = parseInt(m[1], 10);
    }
  }

  render();
})();
