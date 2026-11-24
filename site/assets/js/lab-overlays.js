(function () {
  "use strict";

  var COHORT_LABELS = {
    main_ai_lab: "Main AI Lab",
    safety_lab_researcher: "Safety Lab / Researcher"
  };

  var PAGE_STEP = 30;

  function clearChildren(node) {
    while (node && node.firstChild) {
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

  function parseBundle() {
    var scriptNode = document.getElementById("lab-overlays-data");
    if (!scriptNode) return null;
    try {
      return JSON.parse(scriptNode.textContent || "{}");
    } catch (err) {
      return null;
    }
  }

  function buildPipMeter(score) {
    var n = Math.max(1, Math.min(5, Number(score) || 1));
    var wrap = el("span", {
      className: "lo-pip-meter",
      role: "img",
      "aria-label": "Readiness " + n + " out of 5"
    });
    for (var i = 1; i <= 5; i++) {
      wrap.appendChild(
        el("span", {
          className: i <= n ? "lo-pip-cell is-filled" : "lo-pip-cell",
          "aria-hidden": "true"
        })
      );
    }
    wrap.appendChild(
      el("span", {
        className: "lo-pip-num",
        textContent: n + "/5"
      })
    );
    return wrap;
  }

  function extractHost(url) {
    try {
      var parsed = new URL(url);
      return parsed.hostname.replace(/^www\./, "");
    } catch (err) {
      return "official website";
    }
  }

  function initLedgerDomains(domains) {
    var railNode = document.getElementById("lo-domain-rail");
    var stageNode = document.getElementById("lo-domain-stage");
    var statusNode = document.getElementById("lo-domain-status");
    if (!railNode || !stageNode || !Array.isArray(domains) || !domains.length) return;

    var activeId = domains[0].id;

    function renderDomain() {
      var active = domains[0];
      for (var i = 0; i < domains.length; i++) {
        if (domains[i].id === activeId) {
          active = domains[i];
          break;
        }
      }

      if (statusNode) {
        statusNode.textContent = active.code + " · " + active.title.toUpperCase();
      }

      var btns = railNode.querySelectorAll("button[data-domain-id]");
      for (var b = 0; b < btns.length; b++) {
        var isMatch = btns[b].getAttribute("data-domain-id") === active.id;
        btns[b].classList.toggle("is-active", isMatch);
        btns[b].setAttribute("aria-pressed", isMatch ? "true" : "false");
      }

      clearChildren(stageNode);

      var grid = el("div", { className: "lo-domain-cells" }, [
        el("div", { className: "lo-domain-cell lo-domain-cell--warn" }, [
          el("p", { className: "lo-kicker" }, [
            el("span", { className: "st-pip st-pip--warn", "aria-hidden": "true" }),
            " 01 · Current institutional blind spot"
          ]),
          el("p", { className: "lo-cell-copy", textContent: active.today_failure })
        ]),
        el("div", { className: "lo-domain-cell" }, [
          el("p", { className: "lo-kicker" }, [
            el("span", { className: "st-pip", "aria-hidden": "true" }),
            " 02 · Shared ledger & privacy principle"
          ]),
          el("p", { className: "lo-cell-copy", textContent: active.ledger_principle })
        ]),
        el("div", { className: "lo-domain-cell" }, [
          el("p", { className: "lo-kicker" }, [
            el("span", { className: "st-pip", "aria-hidden": "true" }),
            " 03 · How it affects one person"
          ]),
          el("p", { className: "lo-cell-copy", textContent: active.individual_effect })
        ]),
        el("div", { className: "lo-domain-cell" }, [
          el("p", { className: "lo-kicker" }, [
            el("span", { className: "st-pip st-pip--amber", "aria-hidden": "true" }),
            " 04 · How it affects labs, courts & agencies"
          ]),
          el("p", { className: "lo-cell-copy", textContent: active.institutional_effect })
        ])
      ]);

      var hardBar = el("div", { className: "lo-domain-hard" }, [
        el("span", { className: "lo-kicker", textContent: "OPEN RESEARCH EDGE · " }),
        el("span", { textContent: active.open_hard_problem })
      ]);

      stageNode.appendChild(grid);
      stageNode.appendChild(hardBar);
    }

    clearChildren(railNode);
    for (var d = 0; d < domains.length; d++) {
      (function (dom) {
        var li = el("li");
        var btn = el(
          "button",
          {
            type: "button",
            className: dom.id === activeId ? "st-matrix-btn is-active" : "st-matrix-btn",
            "data-domain-id": dom.id,
            "aria-pressed": dom.id === activeId ? "true" : "false"
          },
          [
            el("span", { className: "st-matrix-idx", textContent: dom.code.replace("DOM-", "") }),
            el("span", { className: "st-matrix-copy" }, [
              el("span", { className: "st-matrix-title", textContent: dom.title }),
              el("span", { className: "st-matrix-sub", textContent: dom.code + " societal overlay" })
            ]),
            el("span", { className: "st-matrix-leader", "aria-hidden": "true", textContent: "--■" })
          ]
        );
        btn.addEventListener("click", function () {
          activeId = dom.id;
          renderDomain();
        });
        li.appendChild(btn);
        railNode.appendChild(li);
      })(domains[d]);
    }

    renderDomain();
  }

  function initWorkbenchAndDirectory(bundle) {
    var scenarios = Array.isArray(bundle.scenarios) ? bundle.scenarios : [];
    var orgs = Array.isArray(bundle.entities)
      ? bundle.entities
      : (Array.isArray(bundle.organizations) ? bundle.organizations : []);
    if (!scenarios.length || !orgs.length) return;

    var byId = {};
    var scenarioById = {};
    var regionsMap = {};
    for (var s = 0; s < scenarios.length; s++) {
      scenarioById[scenarios[s].id] = scenarios[s];
    }
    for (var i = 0; i < orgs.length; i++) {
      var o = orgs[i];
      byId[o.id] = o;
      regionsMap[o.region] = (regionsMap[o.region] || 0) + 1;
      var convJoined = Array.isArray(o.where_they_converge) ? o.where_they_converge.join(" ") : "";
      var devJoined = Array.isArray(o.where_they_deviate) ? o.where_they_deviate.join(" ") : "";
      o._searchBlob = (
        (o.code || "") + " " +
        (o.name || "") + " " +
        (o.subsector_label || "") + " " +
        (o.region || "") + " " +
        (o.key_teams_or_leads || "") + " " +
        (o.specialized_agent_id || "") + " " +
        (o.specialized_future_role || "") + " " +
        (o.current_focus || "") + " " +
        convJoined + " " +
        devJoined + " " +
        (o.engagement_brief || "") + " " +
        (o.technical_paper_url ? "technical paper flagship alignment governance" : "")
      ).toLowerCase();
      o._index = i;
    }

    var scenarioBar = document.getElementById("lo-scenario-bar");
    var scenarioBanner = document.getElementById("lo-scenario-banner");
    var wbStatus = document.getElementById("lo-wb-status");
    var selectA = document.getElementById("lo-select-a");
    var selectB = document.getElementById("lo-select-b");
    var swapBtn = document.getElementById("lo-swap-btn");
    var pairStage = document.getElementById("lo-pair-stage");

    var cohortBar = document.getElementById("lo-cohort-bar");
    var searchInput = document.getElementById("lo-search");
    var regionSelect = document.getElementById("lo-region");
    var sortSelect = document.getElementById("lo-sort");
    var resetBtn = document.getElementById("lo-reset");
    var countNode = document.getElementById("lo-count-status");
    var rowsHost = document.getElementById("lo-rows");
    var moreWrap = document.getElementById("lo-more-wrap");
    var moreBtn = document.getElementById("lo-more-btn");

    var defaultA = byId["anthropic"] ? "anthropic" : orgs[0].id;
    var defaultB = byId["uk_aisi"] ? "uk_aisi" : (orgs.length > 40 ? orgs[40].id : orgs[0].id);

    var state = {
      scenarioId: scenarios[0].id,
      slotA: defaultA,
      slotB: defaultB,
      cohort: "all",
      region: "all",
      sort: "index",
      query: "",
      limit: PAGE_STEP,
      expanded: {}
    };

    function populateSelects() {
      if (!selectA || !selectB) return;
      function fillOne(sel, activeVal) {
        clearChildren(sel);
        var labTotal = 0;
        var safTotal = 0;
        for (var m = 0; m < orgs.length; m++) {
          if (orgs[m].cohort === "main_ai_lab") labTotal++;
          else safTotal++;
        }
        var groupLabs = el("optgroup", {
          label: labTotal + " Main AI & GI Labs (LAB-01.." + (labTotal < 10 ? "0" + labTotal : labTotal) + ")"
        });
        var groupSafety = el("optgroup", {
          label: safTotal + " Safety Labs & Researchers (SAF-01.." + (safTotal < 10 ? "0" + safTotal : safTotal) + ")"
        });
        for (var k = 0; k < orgs.length; k++) {
          var item = orgs[k];
          var opt = el("option", {
            value: item.id,
            selected: item.id === activeVal,
            textContent: item.code + " · " + item.name + " (" + item.region + ")"
          });
          if (item.cohort === "main_ai_lab") {
            groupLabs.appendChild(opt);
          } else {
            groupSafety.appendChild(opt);
          }
        }
        sel.appendChild(groupLabs);
        sel.appendChild(groupSafety);
        sel.value = activeVal;
      }
      fillOne(selectA, state.slotA);
      fillOne(selectB, state.slotB);
    }

    function populateRegions() {
      if (!regionSelect) return;
      clearChildren(regionSelect);
      regionSelect.appendChild(
        el("option", { value: "all", selected: true, textContent: "All jurisdictions (" + orgs.length + ")" })
      );
      var regionOrder = [
        "United States",
        "United Kingdom",
        "European Union",
        "Canada",
        "Asia-Pacific",
        "Global / Multilateral"
      ];
      for (var r = 0; r < regionOrder.length; r++) {
        var reg = regionOrder[r];
        if (regionsMap[reg]) {
          regionSelect.appendChild(
            el("option", {
              value: reg,
              textContent: reg + " (" + regionsMap[reg] + ")"
            })
          );
        }
      }
    }

    function renderScenarioControls() {
      var activeScenario = scenarioById[state.scenarioId] || scenarios[0];
      if (wbStatus) {
        wbStatus.textContent = activeScenario.code + " · " + activeScenario.title.toUpperCase();
      }
      if (scenarioBar) {
        var btns = scenarioBar.querySelectorAll("button[data-scenario-id]");
        for (var i = 0; i < btns.length; i++) {
          var isOn = btns[i].getAttribute("data-scenario-id") === activeScenario.id;
          btns[i].classList.toggle("is-active", isOn);
          btns[i].setAttribute("aria-pressed", isOn ? "true" : "false");
        }
      }
      if (scenarioBanner) {
        clearChildren(scenarioBanner);
        scenarioBanner.appendChild(
          el("div", { className: "lo-scenario-meta" }, [
            el("span", { className: "st-tag" }, [
              el("span", { className: "st-pip", "aria-hidden": "true" }),
              " " + activeScenario.code + " · " + activeScenario.title
            ]),
            el("span", {
              className: "lo-tracks-ref",
              textContent: activeScenario.track_reference || activeScenario.tracks_ref || ""
            })
          ])
        );
        scenarioBanner.appendChild(
          el("p", { className: "lo-scenario-desc", textContent: activeScenario.summary })
        );
      }
    }

    function buildOrgColumn(org, slotTag) {
      var activeScenario = scenarioById[state.scenarioId] || scenarios[0];
      var overlay = (org.scenario_overlays && org.scenario_overlays[activeScenario.id]) || {
        readiness: 3,
        individual_impact: "",
        organization_impact: ""
      };

      var colClass = slotTag === "A" ? "lo-comp-col lo-comp-col--a" : "lo-comp-col lo-comp-col--b";
      var pipClass = org.cohort === "main_ai_lab" ? "st-pip" : "st-pip st-pip--amber";

      var scenarioStrip = el("div", { className: "lo-mini-scenarios" });
      for (var s = 0; s < scenarios.length; s++) {
        (function (scen) {
          var scOv = (org.scenario_overlays && org.scenario_overlays[scen.id]) || { readiness: 3 };
          var chip = el(
            "button",
            {
              type: "button",
              className: scen.id === activeScenario.id ? "lo-scen-chip is-active" : "lo-scen-chip",
              title: scen.title + " (" + scOv.readiness + "/5)",
              "aria-label": scen.title + ": readiness " + scOv.readiness + " of 5"
            },
            [
              el("span", { className: "lo-scen-chip-code", textContent: scen.code }),
              el("span", { className: "lo-scen-chip-val", textContent: scOv.readiness + "/5" })
            ]
          );
          chip.addEventListener("click", function () {
            state.scenarioId = scen.id;
            renderScenarioControls();
            renderComparator();
            renderDirectory();
          });
          scenarioStrip.appendChild(chip);
        })(scenarios[s]);
      }

      var convergeList = el("ul", { className: "lo-point-list" });
      var convArr = Array.isArray(org.where_they_converge) ? org.where_they_converge : [];
      for (var c = 0; c < convArr.length; c++) {
        convergeList.appendChild(
          el("li", null, [
            el("span", { className: "st-pip", "aria-hidden": "true" }),
            el("span", { textContent: convArr[c] })
          ])
        );
      }

      var deviateList = el("ul", { className: "lo-point-list lo-point-list--warn" });
      var devArr = Array.isArray(org.where_they_deviate) ? org.where_they_deviate : [];
      for (var d = 0; d < devArr.length; d++) {
        deviateList.appendChild(
          el("li", null, [
            el("span", { className: "st-pip st-pip--warn", "aria-hidden": "true" }),
            el("span", { textContent: devArr[d] })
          ])
        );
      }

      var linksRow = el("div", { className: "lo-links-row" });
      if (org.technical_paper_url) {
        linksRow.appendChild(
          el("a", {
            className: "st-action-btn lo-paper-btn",
            href: org.technical_paper_url,
            textContent: "Read Technical Paper ↗"
          })
        );
      }
      linksRow.appendChild(
        el("a", {
          className: "st-action-btn",
          href: org.url,
          target: "_blank",
          rel: "noopener noreferrer",
          textContent: extractHost(org.url) + " ↗"
        })
      );
      if (org.atlas_id) {
        var atlasScoreSuffix = org.atlas_alignment_score != null ? " (" + org.atlas_alignment_score + "/100)" : "";
        linksRow.appendChild(
          el("a", {
            className: "st-action-btn",
            href: "/labs/institutions/",
            textContent: "Institutional Atlas" + atlasScoreSuffix + " ↗"
          })
        );
      }

      return el("article", { className: colClass }, [
        el("div", { className: "lo-col-top" }, [
          el("span", { className: "st-tag" }, [
            el("span", { className: pipClass, "aria-hidden": "true" }),
            " SLOT " + slotTag + " · " + org.code + " · " + (COHORT_LABELS[org.cohort] || org.cohort)
          ]),
          buildPipMeter(overlay.readiness)
        ]),
        el("h3", { className: "lo-org-title", textContent: org.name }),
        el("p", {
          className: "lo-org-meta",
          textContent: org.region + " · " + org.subsector_label
        }),
        el("p", {
          className: "lo-org-focus",
          textContent: org.current_focus || ("Key work: " + (org.key_teams_or_leads || ""))
        }),
        scenarioStrip,
        el("div", { className: "lo-agent-box" }, [
          el("p", {
            className: "lo-kicker",
            textContent: "SPECIALIZED AGENT TEMPLATE · " + org.specialized_agent_id
          }),
          el("p", { className: "lo-cell-copy", textContent: org.specialized_future_role })
        ]),
        el("div", { className: "lo-impact-pair" }, [
          el("div", { className: "lo-impact-block" }, [
            el("p", {
              className: "lo-kicker",
              textContent: activeScenario.code + " · EFFECT ON THE INDIVIDUAL"
            }),
            el("p", { className: "lo-cell-copy", textContent: overlay.individual_impact })
          ]),
          el("div", { className: "lo-impact-block lo-impact-block--org" }, [
            el("p", {
              className: "lo-kicker",
              textContent: activeScenario.code + " · EFFECT ON THE ORGANIZATION"
            }),
            el("p", { className: "lo-cell-copy", textContent: overlay.organization_impact })
          ])
        ]),
        el("div", { className: "lo-conv-dev" }, [
          el("div", { className: "lo-conv-block" }, [
            el("p", { className: "lo-kicker", textContent: "WHERE THEY CONVERGE WITH CIN" }),
            convergeList
          ]),
          el("div", { className: "lo-dev-block" }, [
            el("p", { className: "lo-kicker lo-kicker--warn", textContent: "WHERE THEY DEVIATE TODAY" }),
            deviateList
          ])
        ]),
        el("div", { className: "lo-engage-block" }, [
          el("p", { className: "lo-kicker", textContent: "PROPOSED JOINT ENGAGEMENT BRIEF" }),
          el("p", { className: "lo-cell-copy", textContent: org.engagement_brief }),
          linksRow
        ])
      ]);
    }

    function renderComparator() {
      if (!pairStage) return;
      var orgA = byId[state.slotA] || orgs[0];
      var orgB = byId[state.slotB] || orgs[1] || orgs[0];
      clearChildren(pairStage);
      pairStage.appendChild(buildOrgColumn(orgA, "A"));
      pairStage.appendChild(buildOrgColumn(orgB, "B"));
    }

    function buildExpandedDrawer(org) {
      var activeScenario = scenarioById[state.scenarioId] || scenarios[0];
      var overlay = (org.scenario_overlays && org.scenario_overlays[activeScenario.id]) || {
        readiness: 3,
        individual_impact: "",
        organization_impact: ""
      };

      var convList = el("ul", { className: "lo-point-list" });
      for (var c = 0; c < (org.where_they_converge || []).length; c++) {
        convList.appendChild(
          el("li", null, [
            el("span", { className: "st-pip", "aria-hidden": "true" }),
            el("span", { textContent: org.where_they_converge[c] })
          ])
        );
      }

      var devList = el("ul", { className: "lo-point-list lo-point-list--warn" });
      for (var d = 0; d < (org.where_they_deviate || []).length; d++) {
        devList.appendChild(
          el("li", null, [
            el("span", { className: "st-pip st-pip--warn", "aria-hidden": "true" }),
            el("span", { textContent: org.where_they_deviate[d] })
          ])
        );
      }

      return el("div", { className: "lo-drawer" }, [
        el("div", { className: "lo-drawer-grid" }, [
          el("div", { className: "lo-drawer-cell" }, [
            el("p", {
              className: "lo-kicker",
              textContent: "SPECIALIZED AGENT · " + org.specialized_agent_id
            }),
            el("p", { className: "lo-cell-copy", textContent: org.specialized_future_role })
          ]),
          el("div", { className: "lo-drawer-cell" }, [
            el("p", {
              className: "lo-kicker",
              textContent: activeScenario.code + " · INDIVIDUAL IMPACT"
            }),
            el("p", { className: "lo-cell-copy", textContent: overlay.individual_impact })
          ]),
          el("div", { className: "lo-drawer-cell" }, [
            el("p", {
              className: "lo-kicker",
              textContent: activeScenario.code + " · ORGANIZATIONAL IMPACT"
            }),
            el("p", { className: "lo-cell-copy", textContent: overlay.organization_impact })
          ])
        ]),
        el("div", { className: "lo-drawer-split" }, [
          el("div", { className: "lo-drawer-half" }, [
            el("p", { className: "lo-kicker", textContent: "CONVERGENCE POINTS" }),
            convList
          ]),
          el("div", { className: "lo-drawer-half" }, [
            el("p", { className: "lo-kicker lo-kicker--warn", textContent: "DIVERGENCE POINTS" }),
            devList
          ])
        ]),
        el("div", { className: "lo-drawer-foot" }, [
          el("p", { className: "lo-cell-copy" }, [
            el("strong", { textContent: "Engagement brief: " }),
            org.engagement_brief
          ]),
          el("div", { className: "lo-links-row" }, [
            org.technical_paper_url
              ? el("a", {
                  className: "st-action-btn lo-paper-btn",
                  href: org.technical_paper_url,
                  textContent: "Read Technical Paper ↗"
                })
              : null,
            el("a", {
              className: "st-action-btn",
              href: org.url,
              target: "_blank",
              rel: "noopener noreferrer",
              textContent: extractHost(org.url) + " ↗"
            })
          ])
        ])
      ]);
    }

    function renderDirectory() {
      if (!rowsHost) return;
      var q = state.query.trim().toLowerCase();
      var activeScenario = scenarioById[state.scenarioId] || scenarios[0];

      var filtered = [];
      for (var i = 0; i < orgs.length; i++) {
        var o = orgs[i];
        if (state.cohort !== "all" && o.cohort !== state.cohort) continue;
        if (state.region !== "all" && o.region !== state.region) continue;
        if (q && o._searchBlob.indexOf(q) === -1) continue;
        filtered.push(o);
      }

      filtered.sort(function (a, b) {
        if (state.sort === "readiness") {
          var ra = (a.scenario_overlays && a.scenario_overlays[activeScenario.id] && a.scenario_overlays[activeScenario.id].readiness) || 0;
          var rb = (b.scenario_overlays && b.scenario_overlays[activeScenario.id] && b.scenario_overlays[activeScenario.id].readiness) || 0;
          if (rb !== ra) return rb - ra;
          return a._index - b._index;
        }
        if (state.sort === "name") {
          return a.name.localeCompare(b.name);
        }
        return a._index - b._index;
      });

      var shownCount = Math.min(filtered.length, state.limit);
      if (countNode) {
        countNode.textContent =
          "Showing " +
          shownCount +
          " of " +
          filtered.length +
          " matched organizations (active overlay: " +
          activeScenario.code +
          ")";
      }

      clearChildren(rowsHost);
      if (!filtered.length) {
        rowsHost.appendChild(
          el("p", {
            className: "lo-empty",
            textContent: "No AI lab or safety group matched those filters. Reset filters to inspect all " + orgs.length + " specialized overlays."
          })
        );
      } else {
        for (var r = 0; r < shownCount; r++) {
          (function (org) {
            var isOpen = Boolean(state.expanded[org.id]);
            var ov = (org.scenario_overlays && org.scenario_overlays[activeScenario.id]) || { readiness: 3 };
            var pipCls = org.cohort === "main_ai_lab" ? "st-pip" : "st-pip st-pip--amber";

            var scenarioTotal = scenarios.length || 6;
            var noteTotal =
              ((org.where_they_converge && org.where_they_converge.length) || 0) +
              ((org.where_they_deviate && org.where_they_deviate.length) || 0);
            var inspectBtn = el("button", {
              type: "button",
              className: "st-action-btn",
              "aria-expanded": isOpen ? "true" : "false",
              textContent: isOpen
                ? "Close brief −"
                : ("Inspect brief + (" + scenarioTotal + " scenarios · " + noteTotal + " notes)")
            });
            var pinABtn = el("button", {
              type: "button",
              className: "st-action-btn",
              textContent: "Slot A"
            });
            var pinBBtn = el("button", {
              type: "button",
              className: "st-action-btn",
              textContent: "Slot B"
            });

            inspectBtn.addEventListener("click", function () {
              state.expanded[org.id] = !state.expanded[org.id];
              renderDirectory();
            });
            pinABtn.addEventListener("click", function () {
              state.slotA = org.id;
              if (selectA) selectA.value = org.id;
              renderComparator();
              var wb = document.getElementById("lo-workbench");
              if (wb && wb.scrollIntoView) wb.scrollIntoView({ behavior: "smooth", block: "start" });
            });
            pinBBtn.addEventListener("click", function () {
              state.slotB = org.id;
              if (selectB) selectB.value = org.id;
              renderComparator();
              var wb = document.getElementById("lo-workbench");
              if (wb && wb.scrollIntoView) wb.scrollIntoView({ behavior: "smooth", block: "start" });
            });

            var rowWrap = el("div", { className: isOpen ? "lo-dir-item is-open" : "lo-dir-item" });
            var rowLine = el("div", { className: "lo-dir-row" }, [
              el("div", { className: "lo-dir-code" }, [
                el("span", { className: pipCls, "aria-hidden": "true" }),
                " " + org.code
              ]),
              el("div", { className: "lo-dir-main" }, [
                el("h3", { className: "lo-dir-name", textContent: org.name }),
                el("p", {
                  className: "lo-dir-sub",
                  textContent:
                    org.region +
                    " · " +
                    org.subsector_label +
                    (org.key_teams_or_leads ? " · " + org.key_teams_or_leads : "")
                }),
                el("p", {
                  className: "lo-dir-role",
                  textContent: org.current_focus || org.specialized_future_role || ""
                })
              ]),
              el("div", { className: "lo-dir-readiness" }, [
                el("span", { className: "lo-readiness-tag", textContent: activeScenario.code }),
                buildPipMeter(ov.readiness)
              ]),
              el("div", { className: "lo-dir-actions" }, [
                org.technical_paper_url
                  ? el("a", {
                      className: "st-action-btn lo-paper-btn",
                      href: org.technical_paper_url,
                      textContent: "Technical Paper ↗"
                    })
                  : null,
                inspectBtn,
                pinABtn,
                pinBBtn
              ])
            ]);

            rowWrap.appendChild(rowLine);
            if (isOpen) {
              rowWrap.appendChild(buildExpandedDrawer(org));
            }
            rowsHost.appendChild(rowWrap);
          })(filtered[r]);
        }
      }

      if (moreWrap && moreBtn) {
        var remaining = filtered.length - shownCount;
        if (remaining > 0) {
          moreWrap.hidden = false;
          moreBtn.textContent =
            "Show " + Math.min(PAGE_STEP, remaining) + " more (" + remaining + " remaining)";
        } else {
          moreWrap.hidden = true;
        }
      }
    }

    if (scenarioBar) {
      clearChildren(scenarioBar);
      for (var idx = 0; idx < scenarios.length; idx++) {
        (function (scen) {
          var li = el("li");
          var btn = el(
            "button",
            {
              type: "button",
              className: scen.id === state.scenarioId ? "st-station-btn is-active" : "st-station-btn",
              "data-scenario-id": scen.id,
              "aria-pressed": scen.id === state.scenarioId ? "true" : "false"
            },
            [
              el("span", { className: "st-pip", "aria-hidden": "true" }),
              " " + scen.title
            ]
          );
          btn.addEventListener("click", function () {
            state.scenarioId = scen.id;
            renderScenarioControls();
            renderComparator();
            renderDirectory();
          });
          li.appendChild(btn);
          scenarioBar.appendChild(li);
        })(scenarios[idx]);
      }
    }

    populateSelects();
    populateRegions();
    renderScenarioControls();
    renderComparator();
    renderDirectory();

    if (selectA) {
      selectA.addEventListener("change", function () {
        state.slotA = selectA.value;
        renderComparator();
      });
    }
    if (selectB) {
      selectB.addEventListener("change", function () {
        state.slotB = selectB.value;
        renderComparator();
      });
    }
    if (swapBtn) {
      swapBtn.addEventListener("click", function () {
        var tmp = state.slotA;
        state.slotA = state.slotB;
        state.slotB = tmp;
        if (selectA) selectA.value = state.slotA;
        if (selectB) selectB.value = state.slotB;
        renderComparator();
      });
    }

    if (cohortBar) {
      var cBtns = cohortBar.querySelectorAll("button[data-cohort]");
      for (var c = 0; c < cBtns.length; c++) {
        (function (btn) {
          btn.addEventListener("click", function () {
            state.cohort = btn.getAttribute("data-cohort") || "all";
            state.limit = PAGE_STEP;
            for (var j = 0; j < cBtns.length; j++) {
              var on = cBtns[j] === btn;
              cBtns[j].classList.toggle("is-active", on);
              cBtns[j].setAttribute("aria-pressed", on ? "true" : "false");
            }
            renderDirectory();
          });
        })(cBtns[c]);
      }
    }

    if (searchInput) {
      searchInput.addEventListener("input", function () {
        state.query = searchInput.value || "";
        state.limit = PAGE_STEP;
        renderDirectory();
      });
    }
    if (regionSelect) {
      regionSelect.addEventListener("change", function () {
        state.region = regionSelect.value || "all";
        state.limit = PAGE_STEP;
        renderDirectory();
      });
    }
    if (sortSelect) {
      sortSelect.addEventListener("change", function () {
        state.sort = sortSelect.value || "index";
        renderDirectory();
      });
    }
    if (resetBtn) {
      resetBtn.addEventListener("click", function () {
        state.cohort = "all";
        state.region = "all";
        state.sort = "index";
        state.query = "";
        state.limit = PAGE_STEP;
        if (searchInput) searchInput.value = "";
        if (regionSelect) regionSelect.value = "all";
        if (sortSelect) sortSelect.value = "index";
        if (cohortBar) {
          var btns = cohortBar.querySelectorAll("button[data-cohort]");
          for (var j = 0; j < btns.length; j++) {
            var isAll = btns[j].getAttribute("data-cohort") === "all";
            btns[j].classList.toggle("is-active", isAll);
            btns[j].setAttribute("aria-pressed", isAll ? "true" : "false");
          }
        }
        renderDirectory();
      });
    }
    if (moreBtn) {
      moreBtn.addEventListener("click", function () {
        state.limit += PAGE_STEP;
        renderDirectory();
      });
    }
  }

  function boot() {
    var bundle = parseBundle();
    if (!bundle) return;
    initLedgerDomains(bundle.ledger_societal_domains || bundle.ledger_domains);
    initWorkbenchAndDirectory(bundle);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
