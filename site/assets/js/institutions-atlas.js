(function () {
  "use strict";

  var ROLE_LABELS = {
    alignment_safety: "Safety & Alignment",
    frontier_lab: "Frontier & Open Labs",
    public_official: "Public Officials & Regulators",
    builder: "Independent Builders",
    civil_society: "Civil Society & Co-ops",
    general_public: "Public, Media & Civic"
  };

  var ROLE_ORDER = [
    "civil_society",
    "alignment_safety",
    "frontier_lab",
    "builder",
    "public_official",
    "general_public"
  ];

  var AXES = [
    { index: 0, label: "Oversight", shortLabel: "Oversight" },
    { index: 1, label: "Action receipts", shortLabel: "Receipts" },
    { index: 2, label: "Shared capacity", shortLabel: "Shared" },
    { index: 3, label: "Independent safety testing", shortLabel: "Safety" },
    { index: 4, label: "Public voice", shortLabel: "Voice" }
  ];

  var PAGE_INITIAL = 18;
  var PAGE_STEP = 24;

  function clearChildren(node) {
    while (node.firstChild) {
      node.removeChild(node.firstChild);
    }
  }

  function el(tag, props, children) {
    var node = document.createElement(tag);
    if (props) {
      var keys = Object.keys(props);
      for (var i = 0; i < keys.length; i++) {
        var k = keys[i];
        var v = props[k];
        if (v === undefined || v === null) continue;
        if (k === "className") {
          node.className = v;
        } else if (k === "textContent") {
          node.textContent = v;
        } else if (k === "hidden") {
          node.hidden = Boolean(v);
        } else if (k === "disabled") {
          node.disabled = Boolean(v);
        } else if (k === "value") {
          node.value = String(v);
        } else if (k === "selected") {
          node.selected = Boolean(v);
        } else if (k === "styleWidth") {
          node.style.width = String(v);
        } else {
          node.setAttribute(k, String(v));
        }
      }
    }
    if (children && children.length) {
      for (var j = 0; j < children.length; j++) {
        var child = children[j];
        if (child === undefined || child === null) continue;
        if (typeof child === "string") {
          node.appendChild(document.createTextNode(child));
        } else {
          node.appendChild(child);
        }
      }
    }
    return node;
  }

  function extractHost(url) {
    try {
      var parsed = new URL(url);
      return parsed.hostname.replace(/^www\./, "");
    } catch (err) {
      return "official site";
    }
  }

  function parseCatalog() {
    var dataNode = document.getElementById("institutions-atlas-data");
    if (!dataNode) return [];
    try {
      var raw = JSON.parse(dataNode.textContent || "[]");
      if (!Array.isArray(raw)) return [];
      return raw;
    } catch (err) {
      return [];
    }
  }

  function initAtlas() {
    var records = parseCatalog();
    if (!records.length) return;

    var byId = {};
    for (var i = 0; i < records.length; i++) {
      var rec = records[i];
      var roleText = ROLE_LABELS[rec.role] || rec.role;
      var stepJoined = Array.isArray(rec.steps) ? rec.steps.join(" ") : "";
      rec._searchBlob = (
        rec.name + " " +
        roleText + " " +
        rec.subsector + " " +
        rec.region + " " +
        rec.controls + " " +
        rec.bottleneck + " " +
        stepJoined
      ).toLowerCase();
      byId[rec.id] = rec;
    }

    var compSelectA = document.getElementById("ia-comp-a");
    var compSelectB = document.getElementById("ia-comp-b");
    var compSwapBtn = document.getElementById("ia-comp-swap");
    var compStage = document.getElementById("ia-comp-stage");

    var searchInput = document.getElementById("ia-search");
    var roleBar = document.getElementById("ia-role-pills");
    var regionSelect = document.getElementById("ia-region");
    var sortSelect = document.getElementById("ia-sort");
    var resetBtn = document.getElementById("ia-reset");
    var countStatus = document.getElementById("ia-count-status");
    var grid = document.getElementById("ia-grid");
    var loadMoreBtn = document.getElementById("ia-load-more");
    var loadMoreWrap = document.getElementById("ia-load-more-wrap");

    var defaultA = byId["openai"] ? "openai" : records[0].id;
    var defaultB = byId["platform-coop-consortium"]
      ? "platform-coop-consortium"
      : (records.length > 1 ? records[1].id : records[0].id);

    var state = {
      compA: compSelectA && compSelectA.value && byId[compSelectA.value] ? compSelectA.value : defaultA,
      compB: compSelectB && compSelectB.value && byId[compSelectB.value] ? compSelectB.value : defaultB,
      nextCompSlot: "B",
      query: "",
      role: "all",
      region: "all",
      sort: "score",
      limit: PAGE_INITIAL,
      expandedIds: {}
    };

    function populateComparatorSelects() {
      if (!compSelectA || !compSelectB) return;
      var grouped = {};
      for (var r = 0; r < ROLE_ORDER.length; r++) {
        grouped[ROLE_ORDER[r]] = [];
      }
      for (var k = 0; k < records.length; k++) {
        var item = records[k];
        if (!grouped[item.role]) grouped[item.role] = [];
        grouped[item.role].push(item);
      }
      for (var g = 0; g < ROLE_ORDER.length; g++) {
        var rk = ROLE_ORDER[g];
        grouped[rk].sort(function (a, b) {
          return a.name.localeCompare(b.name);
        });
      }

      function fillOne(selectNode, selectedId) {
        clearChildren(selectNode);
        for (var idx = 0; idx < ROLE_ORDER.length; idx++) {
          var roleKey = ROLE_ORDER[idx];
          var list = grouped[roleKey] || [];
          if (!list.length) continue;
          var groupEl = el("optgroup", { label: ROLE_LABELS[roleKey] || roleKey });
          for (var m = 0; m < list.length; m++) {
            var org = list[m];
            var opt = el("option", {
              value: org.id,
              selected: org.id === selectedId,
              textContent: org.name + " (" + org.region + " · " + org.score + "/100)"
            });
            groupEl.appendChild(opt);
          }
          selectNode.appendChild(groupEl);
        }
        selectNode.value = selectedId;
      }

      fillOne(compSelectA, state.compA);
      fillOne(compSelectB, state.compB);
    }

    function buildSummaryDelta(orgA, orgB) {
      if (orgA.id === orgB.id) {
        return "Both pickers currently point to " + orgA.name + ". Choose a second organisation above to contrast their governance scores and blind spots.";
      }
      var maxGap = -1;
      var maxAxis = AXES[0].label;
      var leaderName = orgA.name;
      for (var i = 0; i < AXES.length; i++) {
        var aVal = (orgA.scores && orgA.scores[i]) || 0;
        var bVal = (orgB.scores && orgB.scores[i]) || 0;
        var diff = Math.abs(aVal - bVal);
        if (diff > maxGap) {
          maxGap = diff;
          maxAxis = AXES[i].label.toLowerCase();
          leaderName = aVal >= bVal ? orgA.name : orgB.name;
        }
      }
      if (maxGap === 0) {
        return orgA.name + " and " + orgB.name + " match on all five rubric dimensions, though they hold different operational levers and bottlenecks below.";
      }
      return "Largest governance gap: " + leaderName + " scores " + maxGap + " point" + (maxGap === 1 ? "" : "s") + " higher on " + maxAxis + " (" + orgA.score + "/100 vs " + orgB.score + "/100 overall).";
    }

    function buildComparatorOrgCard(org, slotTag) {
      var stepItems = [];
      var steps = Array.isArray(org.steps) ? org.steps : [];
      for (var i = 0; i < steps.length; i++) {
        stepItems.push(el("li", { textContent: steps[i] }));
      }
      var host = extractHost(org.url);
      return el("article", { className: "ia-comp-card ia-comp-card-" + slotTag }, [
        el("div", { className: "ia-card-meta" }, [
          el("span", {
            className: "ia-pill ia-pill-slot-" + slotTag,
            textContent: (slotTag === "a" ? "Organisation A · " : "Organisation B · ") + (ROLE_LABELS[org.role] || org.role)
          }),
          el("span", { className: "ia-score-badge", textContent: "Alignment " + org.score + "/100" })
        ]),
        el("h3", { className: "ia-comp-title", textContent: org.name }),
        el("p", { className: "ia-submeta", textContent: org.region + " · " + org.subsector }),
        el("div", { className: "ia-dossier-block" }, [
          el("h4", { className: "ia-field-label", textContent: "What they control" }),
          el("p", { textContent: org.controls })
        ]),
        el("div", { className: "ia-dossier-block" }, [
          el("h4", { className: "ia-field-label", textContent: "Key bottleneck" }),
          el("p", { textContent: org.bottleneck })
        ]),
        el("div", { className: "ia-dossier-block" }, [
          el("h4", { className: "ia-field-label", textContent: "Recommended next steps" }),
          el("ul", { className: "ia-steps-list" }, stepItems)
        ]),
        el("p", { className: "ia-link-row" }, [
          el("a", {
            className: "ia-ext-link",
            href: org.url,
            rel: "noopener noreferrer",
            textContent: "Visit official website (" + host + ") \u2192"
          })
        ])
      ]);
    }

    function renderComparator() {
      if (!compStage) return;
      var orgA = byId[state.compA] || records[0];
      var orgB = byId[state.compB] || records[0];
      clearChildren(compStage);

      var axisRows = [];
      for (var i = 0; i < AXES.length; i++) {
        var axis = AXES[i];
        var valA = (orgA.scores && orgA.scores[i]) || 0;
        var valB = (orgB.scores && orgB.scores[i]) || 0;
        var pctA = Math.max(6, Math.min(100, valA * 20)) + "%";
        var pctB = Math.max(6, Math.min(100, valB * 20)) + "%";

        axisRows.push(
          el("div", { className: "ia-rubric-row" }, [
            el("div", { className: "ia-rubric-head" }, [
              el("span", { className: "ia-rubric-axis", textContent: axis.label }),
              el("span", {
                className: "ia-rubric-nums",
                textContent: "A: " + valA + "/5 · B: " + valB + "/5"
              })
            ]),
            el("div", { className: "ia-rubric-bars" }, [
              el("div", { className: "ia-bar-line" }, [
                el("span", { className: "ia-bar-tag ia-bar-tag-a", textContent: "A" }),
                el("div", { className: "ia-bar-track" }, [
                  el("div", { className: "ia-bar-fill ia-bar-fill-a", styleWidth: pctA })
                ]),
                el("span", { className: "ia-bar-val", textContent: valA + "/5" })
              ]),
              el("div", { className: "ia-bar-line" }, [
                el("span", { className: "ia-bar-tag ia-bar-tag-b", textContent: "B" }),
                el("div", { className: "ia-bar-track" }, [
                  el("div", { className: "ia-bar-fill ia-bar-fill-b", styleWidth: pctB })
                ]),
                el("span", { className: "ia-bar-val", textContent: valB + "/5" })
              ])
            ])
          ])
        );
      }

      var rubricBox = el("div", { className: "ia-rubric-panel" }, [
        el("div", { className: "ia-rubric-legend" }, [
          el("span", { className: "ia-legend-item" }, [
            el("span", { className: "ia-legend-swatch ia-swatch-a" }),
            el("strong", { textContent: "A: " + orgA.name }),
            " (" + orgA.score + "/100)"
          ]),
          el("span", { className: "ia-legend-item" }, [
            el("span", { className: "ia-legend-swatch ia-swatch-b" }),
            el("strong", { textContent: "B: " + orgB.name }),
            " (" + orgB.score + "/100)"
          ])
        ]),
        el("p", { className: "ia-comp-delta", textContent: buildSummaryDelta(orgA, orgB) }),
        el("div", { className: "ia-rubric-grid" }, axisRows)
      ]);

      var pairGrid = el("div", { className: "ia-comp-pair" }, [
        buildComparatorOrgCard(orgA, "a"),
        buildComparatorOrgCard(orgB, "b")
      ]);

      compStage.appendChild(rubricBox);
      compStage.appendChild(pairGrid);
    }

    function filterAndSort() {
      var tokens = state.query
        .toLowerCase()
        .trim()
        .split(/\s+/)
        .filter(Boolean);

      var matched = [];
      for (var i = 0; i < records.length; i++) {
        var r = records[i];
        if (state.role !== "all" && r.role !== state.role) continue;
        if (state.region !== "all" && r.region !== state.region) continue;
        if (tokens.length) {
          var ok = true;
          for (var t = 0; t < tokens.length; t++) {
            if (r._searchBlob.indexOf(tokens[t]) === -1) {
              ok = false;
              break;
            }
          }
          if (!ok) continue;
        }
        matched.push(r);
      }

      matched.sort(function (a, b) {
        if (state.sort === "name") {
          return a.name.localeCompare(b.name);
        }
        if (state.sort === "oversight") {
          var oa = (a.scores && a.scores[0]) || 0;
          var ob = (b.scores && b.scores[0]) || 0;
          if (ob !== oa) return ob - oa;
          if (b.score !== a.score) return b.score - a.score;
          return a.name.localeCompare(b.name);
        }
        if (state.sort === "voice") {
          var va = (a.scores && a.scores[4]) || 0;
          var vb = (b.scores && b.scores[4]) || 0;
          if (vb !== va) return vb - va;
          if (b.score !== a.score) return b.score - a.score;
          return a.name.localeCompare(b.name);
        }
        if (b.score !== a.score) return b.score - a.score;
        return a.name.localeCompare(b.name);
      });

      return matched;
    }

    function buildDossierCard(org) {
      var isExpanded = Boolean(state.expandedIds[org.id]);
      var dossierId = "ia-dossier-" + org.id;

      var miniAxes = [];
      for (var i = 0; i < AXES.length; i++) {
        var sc = (org.scores && org.scores[i]) || 0;
        var pct = Math.max(12, Math.min(100, sc * 20)) + "%";
        miniAxes.push(
          el("div", { className: "ia-mini-axis" }, [
            el("div", { className: "ia-mini-label-row" }, [
              el("span", { textContent: AXES[i].shortLabel }),
              el("strong", { textContent: sc + "/5" })
            ]),
            el("div", { className: "ia-mini-track" }, [
              el("div", { className: "ia-mini-fill", styleWidth: pct })
            ])
          ])
        );
      }

      var stepNodes = [];
      var steps = Array.isArray(org.steps) ? org.steps : [];
      for (var s = 0; s < steps.length; s++) {
        stepNodes.push(el("li", { textContent: steps[s] }));
      }

      var host = extractHost(org.url);
      var dossierPanel = el(
        "div",
        {
          className: "ia-dossier",
          id: dossierId,
          hidden: !isExpanded
        },
        [
          el("div", { className: "ia-dossier-block" }, [
            el("h4", { className: "ia-field-label", textContent: "What they control" }),
            el("p", { textContent: org.controls })
          ]),
          el("div", { className: "ia-dossier-block" }, [
            el("h4", { className: "ia-field-label", textContent: "Key bottleneck" }),
            el("p", { textContent: org.bottleneck })
          ]),
          el("div", { className: "ia-dossier-block" }, [
            el("h4", { className: "ia-field-label", textContent: "Recommended next steps" }),
            el("ul", { className: "ia-steps-list" }, stepNodes)
          ]),
          el("p", { className: "ia-link-row" }, [
            el("a", {
              className: "ia-ext-link",
              href: org.url,
              rel: "noopener noreferrer",
              textContent: "Visit official website (" + host + ") \u2192"
            })
          ])
        ]
      );

      var hiddenSummary = "3 fields · " + steps.length + " " + (steps.length === 1 ? "step" : "steps");
      var collapsedLabel = "Expand dossier + (" + hiddenSummary + ")";
      var expandedLabel = "Hide dossier −";

      var toggleBtn = el("button", {
        type: "button",
        className: "ia-dossier-btn",
        "aria-expanded": isExpanded ? "true" : "false",
        "aria-controls": dossierId,
        textContent: isExpanded ? expandedLabel : collapsedLabel
      });

      toggleBtn.addEventListener("click", function () {
        var nextState = !dossierPanel.hidden ? false : true;
        dossierPanel.hidden = !nextState;
        state.expandedIds[org.id] = nextState;
        toggleBtn.setAttribute("aria-expanded", nextState ? "true" : "false");
        toggleBtn.textContent = nextState ? expandedLabel : collapsedLabel;
      });

      var compareBtn = el("button", {
        type: "button",
        className: "ia-compare-btn",
        textContent: "Compare"
      });

      compareBtn.addEventListener("click", function () {
        if (state.nextCompSlot === "A") {
          state.compA = org.id;
          if (compSelectA) compSelectA.value = org.id;
          state.nextCompSlot = "B";
        } else {
          state.compB = org.id;
          if (compSelectB) compSelectB.value = org.id;
          state.nextCompSlot = "A";
        }
        renderComparator();
        var compSection = document.getElementById("ia-comparator");
        if (compSection && typeof compSection.scrollIntoView === "function") {
          compSection.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      });

      return el("article", { className: "ia-card" }, [
        el("div", { className: "ia-card-meta" }, [
          el("span", { className: "ia-pill", textContent: ROLE_LABELS[org.role] || org.role }),
          el("span", { className: "ia-score-badge", textContent: org.score + "/100" })
        ]),
        el("h3", { className: "ia-card-title", textContent: org.name }),
        el("p", { className: "ia-submeta", textContent: org.region + " · " + org.subsector }),
        el("div", { className: "ia-mini-grid" }, miniAxes),
        el("div", { className: "ia-card-actions" }, [toggleBtn, compareBtn]),
        dossierPanel
      ]);
    }

    function renderGrid() {
      if (!grid) return;
      var matched = filterAndSort();
      var visible = matched.slice(0, state.limit);
      var isFiltered =
        state.role !== "all" ||
        state.region !== "all" ||
        state.query.trim().length > 0;

      if (countStatus) {
        if (!isFiltered) {
          countStatus.textContent =
            "Showing " + visible.length + " of " + records.length + " organisations";
        } else {
          countStatus.textContent =
            "Showing " + visible.length + " of " + matched.length +
            " matching organisations (" + records.length + " total)";
        }
      }

      clearChildren(grid);

      if (!matched.length) {
        grid.appendChild(
          el("div", { className: "ia-empty-state" }, [
            el("p", {
              textContent:
                "No organisations match those search and filter settings. Reset filters to view all 348 organisations."
            })
          ])
        );
      } else {
        for (var i = 0; i < visible.length; i++) {
          grid.appendChild(buildDossierCard(visible[i]));
        }
      }

      if (loadMoreBtn && loadMoreWrap) {
        var remaining = matched.length - visible.length;
        if (remaining > 0) {
          loadMoreWrap.hidden = false;
          loadMoreBtn.hidden = false;
          loadMoreBtn.textContent = "Show 24 more organisations (" + remaining + " remaining)";
        } else {
          loadMoreWrap.hidden = true;
          loadMoreBtn.hidden = true;
        }
      }
    }

    var svgNodes = document.querySelectorAll("#ex-institutions-overview .ia-svg-node");
    var directorySection = document.getElementById("ia-directory");

    function syncSvgNodes() {
      for (var s = 0; s < svgNodes.length; s++) {
        var node = svgNodes[s];
        var fRole = node.getAttribute("data-filter-role");
        var fRegion = node.getAttribute("data-filter-region");
        var active = false;
        if (fRole) {
          active = state.role === fRole;
        } else if (fRegion) {
          active = state.region === fRegion;
        }
        node.setAttribute("aria-pressed", active ? "true" : "false");
        node.classList.toggle("is-active", active);
      }
    }

    function syncRoleButtons() {
      if (!roleBar) return;
      var buttons = roleBar.querySelectorAll("button[data-role]");
      for (var i = 0; i < buttons.length; i++) {
        var btn = buttons[i];
        var active = btn.getAttribute("data-role") === state.role;
        btn.setAttribute("aria-pressed", active ? "true" : "false");
        if (active) {
          btn.classList.add("is-active");
        } else {
          btn.classList.remove("is-active");
        }
      }
      syncSvgNodes();
    }

    populateComparatorSelects();
    renderComparator();
    syncSvgNodes();
    renderGrid();

    if (compSelectA) {
      compSelectA.addEventListener("change", function () {
        state.compA = compSelectA.value;
        renderComparator();
      });
    }
    if (compSelectB) {
      compSelectB.addEventListener("change", function () {
        state.compB = compSelectB.value;
        renderComparator();
      });
    }
    if (compSwapBtn) {
      compSwapBtn.addEventListener("click", function () {
        var tmp = state.compA;
        state.compA = state.compB;
        state.compB = tmp;
        if (compSelectA) compSelectA.value = state.compA;
        if (compSelectB) compSelectB.value = state.compB;
        renderComparator();
      });
    }

    if (searchInput) {
      searchInput.addEventListener("input", function () {
        state.query = searchInput.value || "";
        state.limit = PAGE_INITIAL;
        renderGrid();
      });
    }

    if (roleBar) {
      var roleButtons = roleBar.querySelectorAll("button[data-role]");
      for (var b = 0; b < roleButtons.length; b++) {
        (function (btn) {
          btn.addEventListener("click", function () {
            state.role = btn.getAttribute("data-role") || "all";
            state.limit = PAGE_INITIAL;
            syncRoleButtons();
            renderGrid();
          });
        })(roleButtons[b]);
      }
    }

    if (regionSelect) {
      regionSelect.addEventListener("change", function () {
        state.region = regionSelect.value || "all";
        state.limit = PAGE_INITIAL;
        syncSvgNodes();
        renderGrid();
      });
    }

    for (var sn = 0; sn < svgNodes.length; sn++) {
      (function (node) {
        function activateSvgFilter() {
          var fRole = node.getAttribute("data-filter-role");
          var fRegion = node.getAttribute("data-filter-region");
          if (fRole) {
            state.role = state.role === fRole ? "all" : fRole;
            syncRoleButtons();
          } else if (fRegion) {
            state.region = state.region === fRegion ? "all" : fRegion;
            if (regionSelect) regionSelect.value = state.region;
            syncSvgNodes();
          }
          state.limit = PAGE_INITIAL;
          renderGrid();
          if (directorySection && typeof directorySection.scrollIntoView === "function") {
            var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
            directorySection.scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "start" });
          }
        }
        node.addEventListener("click", activateSvgFilter);
        node.addEventListener("keydown", function (ev) {
          if (ev.key === "Enter" || ev.key === " ") {
            ev.preventDefault();
            activateSvgFilter();
          } else if (ev.key === "Escape" && (state.role !== "all" || state.region !== "all")) {
            ev.preventDefault();
            state.role = "all";
            state.region = "all";
            if (regionSelect) regionSelect.value = "all";
            syncRoleButtons();
            renderGrid();
          }
        });
      })(svgNodes[sn]);
    }

    if (sortSelect) {
      sortSelect.addEventListener("change", function () {
        state.sort = sortSelect.value || "score";
        state.limit = PAGE_INITIAL;
        renderGrid();
      });
    }

    if (resetBtn) {
      resetBtn.addEventListener("click", function () {
        state.query = "";
        state.role = "all";
        state.region = "all";
        state.sort = "score";
        state.limit = PAGE_INITIAL;
        if (searchInput) searchInput.value = "";
        if (regionSelect) regionSelect.value = "all";
        if (sortSelect) sortSelect.value = "score";
        syncRoleButtons();
        renderGrid();
      });
    }

    if (loadMoreBtn) {
      loadMoreBtn.addEventListener("click", function () {
        state.limit += PAGE_STEP;
        renderGrid();
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAtlas);
  } else {
    initAtlas();
  }
})();
