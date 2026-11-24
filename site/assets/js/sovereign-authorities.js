(function () {
  "use strict";

  var COHORT_LABELS = {
    national_authority: "National Jurisdiction",
    multilateral_authority: "Global / Multilateral Body"
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
    var scriptNode = document.getElementById("sovereign-authorities-data");
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
      className: "sa-pip-meter",
      role: "img",
      "aria-label": "Readiness " + n + " out of 5"
    });
    for (var i = 1; i <= 5; i++) {
      wrap.appendChild(
        el("span", {
          className: i <= n ? "sa-pip-cell is-filled" : "sa-pip-cell",
          "aria-hidden": "true"
        })
      );
    }
    wrap.appendChild(
      el("span", {
        className: "sa-pip-num",
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

  function initWorkbenchAndDirectory(bundle) {
    var axes = Array.isArray(bundle.axes) ? bundle.axes : [];
    var authorities = Array.isArray(bundle.entities) ? bundle.entities : [];
    if (!axes.length || !authorities.length) return;

    var byId = {};
    var axisById = {};
    var regionsMap = {};
    for (var a = 0; a < axes.length; a++) {
      axisById[axes[a].id] = axes[a];
    }
    for (var i = 0; i < authorities.length; i++) {
      var auth = authorities[i];
      byId[auth.id] = auth;
      regionsMap[auth.region] = (regionsMap[auth.region] || 0) + 1;
      var convJoined = Array.isArray(auth.where_they_converge) ? auth.where_they_converge.join(" ") : "";
      var devJoined = Array.isArray(auth.where_they_deviate) ? auth.where_they_deviate.join(" ") : "";
      var cellBits = [];
      if (auth.axis_overlays) {
        for (var x = 0; x < axes.length; x++) {
          var cellObj = auth.axis_overlays[axes[x].id];
          if (cellObj) {
            cellBits.push(cellObj.citizen_impact || "");
            cellBits.push(cellObj.state_and_lab_impact || "");
          }
        }
      }
      auth._searchBlob = (
        (auth.code || "") + " " +
        (auth.name || "") + " " +
        (auth.subsector_label || "") + " " +
        (auth.region || "") + " " +
        (auth.key_institutions_and_statutes || "") + " " +
        (auth.specialized_agent_id || "") + " " +
        (auth.sovereign_liaison_role || "") + " " +
        convJoined + " " +
        devJoined + " " +
        (auth.statutory_and_treaty_step || "") + " " +
        cellBits.join(" ") + " " +
        (auth.sovereign_paper_url ? "sovereign paper flagship treaty governance" : "")
      ).toLowerCase();
      auth._index = i;
    }

    var axisBar = document.getElementById("sa-axis-bar");
    var axisBanner = document.getElementById("sa-axis-banner");
    var wbStatus = document.getElementById("sa-wb-status");
    var selectA = document.getElementById("sa-select-a");
    var selectB = document.getElementById("sa-select-b");
    var swapBtn = document.getElementById("sa-swap-btn");
    var pairStage = document.getElementById("sa-pair-stage");

    var cohortBar = document.getElementById("sa-cohort-bar");
    var searchInput = document.getElementById("sa-search");
    var regionSelect = document.getElementById("sa-region");
    var sortSelect = document.getElementById("sa-sort");
    var resetBtn = document.getElementById("sa-reset");
    var countNode = document.getElementById("sa-count-status");
    var rowsHost = document.getElementById("sa-rows");
    var moreWrap = document.getElementById("sa-more-wrap");
    var moreBtn = document.getElementById("sa-more-btn");

    var defaultA = byId["united_states"] ? "united_states" : authorities[0].id;
    var defaultB = byId["china"] ? "china" : (authorities.length > 1 ? authorities[1].id : authorities[0].id);

    var state = {
      axisId: axes[0].id,
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
        var natTotal = 0;
        var mulTotal = 0;
        for (var m = 0; m < authorities.length; m++) {
          if (authorities[m].cohort === "national_authority") natTotal++;
          else mulTotal++;
        }
        var groupNat = el("optgroup", {
          label: natTotal + " National Jurisdictions (SOV-01.." + (natTotal < 10 ? "0" + natTotal : natTotal) + ")"
        });
        var groupMul = el("optgroup", {
          label: mulTotal + " Global & Multilateral Bodies (MUL-01.." + (mulTotal < 10 ? "0" + mulTotal : mulTotal) + ")"
        });
        for (var k = 0; k < authorities.length; k++) {
          var item = authorities[k];
          var opt = el("option", {
            value: item.id,
            selected: item.id === activeVal,
            textContent: item.code + " · " + item.name + " (" + item.region + ")"
          });
          if (item.cohort === "national_authority") {
            groupNat.appendChild(opt);
          } else {
            groupMul.appendChild(opt);
          }
        }
        sel.appendChild(groupNat);
        sel.appendChild(groupMul);
        sel.value = activeVal;
      }
      fillOne(selectA, state.slotA);
      fillOne(selectB, state.slotB);
    }

    function populateRegions() {
      if (!regionSelect) return;
      clearChildren(regionSelect);
      regionSelect.appendChild(
        el("option", {
          value: "all",
          selected: true,
          textContent: "All regions (" + authorities.length + ")"
        })
      );
      var regionOrder = [
        "United States",
        "European Union",
        "United Kingdom",
        "Canada",
        "Americas",
        "Asia-Pacific",
        "Middle East & Africa",
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

    function renderAxisControls() {
      var activeAxis = axisById[state.axisId] || axes[0];
      if (wbStatus) {
        wbStatus.textContent = activeAxis.title.toUpperCase();
      }
      if (axisBar) {
        var btns = axisBar.querySelectorAll("button[data-axis-id]");
        for (var i = 0; i < btns.length; i++) {
          var isOn = btns[i].getAttribute("data-axis-id") === activeAxis.id;
          btns[i].classList.toggle("is-active", isOn);
          btns[i].setAttribute("aria-pressed", isOn ? "true" : "false");
        }
      }
      if (axisBanner) {
        clearChildren(axisBanner);
        axisBanner.appendChild(
          el("div", { className: "sa-axis-meta" }, [
            el("span", { className: "st-tag" }, [
              el("span", { className: "st-pip", "aria-hidden": "true" }),
              " " + activeAxis.title
            ]),
            el("span", {
              className: "sa-tracks-ref",
              textContent: activeAxis.track_reference || ""
            })
          ])
        );
        axisBanner.appendChild(
          el("p", { className: "sa-axis-desc", textContent: activeAxis.summary })
        );
        axisBanner.appendChild(
          el("div", { className: "sa-axis-poles" }, [
            el("div", { className: "sa-axis-pole" }, [
              el("p", { className: "sa-kicker", textContent: "PUBLIC-INTEREST BENCHMARK" }),
              el("p", { className: "sa-cell-copy", textContent: activeAxis.public_interest_benchmark || "" })
            ]),
            el("div", { className: "sa-axis-pole sa-axis-pole--warn" }, [
              el("p", { className: "sa-kicker sa-kicker--warn", textContent: "CAPTURE OR OVERREACH RISK" }),
              el("p", { className: "sa-cell-copy", textContent: activeAxis.capture_or_overreach_risk || "" })
            ])
          ])
        );
      }
    }

    function buildAuthorityColumn(auth, slotTag) {
      var activeAxis = axisById[state.axisId] || axes[0];
      var overlay = (auth.axis_overlays && auth.axis_overlays[activeAxis.id]) || {
        score: 3,
        citizen_impact: "",
        state_and_lab_impact: ""
      };

      var colClass = slotTag === "A" ? "sa-comp-col sa-comp-col--a" : "sa-comp-col sa-comp-col--b";
      var pipClass = auth.cohort === "national_authority" ? "st-pip" : "st-pip st-pip--amber";

      var axisStrip = el("div", { className: "sa-mini-axes" });
      for (var x = 0; x < axes.length; x++) {
        (function (ax) {
          var axOv = (auth.axis_overlays && auth.axis_overlays[ax.id]) || { score: 3 };
          var chip = el(
            "button",
            {
              type: "button",
              className: ax.id === activeAxis.id ? "sa-axis-chip is-active" : "sa-axis-chip",
              title: ax.title + " (" + axOv.score + "/5)",
              "aria-pressed": ax.id === activeAxis.id ? "true" : "false"
            },
            [
              el("span", { className: "sa-axis-chip-code", textContent: ax.code }),
              el("span", { className: "sa-axis-chip-val", textContent: axOv.score + "/5" })
            ]
          );
          chip.addEventListener("click", function () {
            state.axisId = ax.id;
            renderAxisControls();
            renderComparator();
            renderDirectory();
          });
          axisStrip.appendChild(chip);
        })(axes[x]);
      }

      var convergeList = el("ul", { className: "sa-point-list" });
      var convArr = Array.isArray(auth.where_they_converge) ? auth.where_they_converge : [];
      for (var c = 0; c < convArr.length; c++) {
        convergeList.appendChild(
          el("li", null, [
            el("span", { className: "st-pip", "aria-hidden": "true" }),
            el("span", { textContent: convArr[c] })
          ])
        );
      }

      var deviateList = el("ul", { className: "sa-point-list sa-point-list--warn" });
      var devArr = Array.isArray(auth.where_they_deviate) ? auth.where_they_deviate : [];
      for (var d = 0; d < devArr.length; d++) {
        deviateList.appendChild(
          el("li", null, [
            el("span", { className: "st-pip st-pip--warn", "aria-hidden": "true" }),
            el("span", { textContent: devArr[d] })
          ])
        );
      }

      var linksRow = el("div", { className: "sa-links-row" });
      if (auth.sovereign_paper_url) {
        linksRow.appendChild(
          el("a", {
            className: "st-action-btn sa-paper-btn",
            href: auth.sovereign_paper_url,
            textContent: "Read Sovereign Paper ↗"
          })
        );
      }
      linksRow.appendChild(
        el("a", {
          className: "st-action-btn",
          href: auth.url,
          target: "_blank",
          rel: "noopener noreferrer",
          textContent: extractHost(auth.url) + " ↗"
        })
      );
      if (auth.atlas_id) {
        var atlasScoreSuffix = auth.atlas_alignment_score != null ? " (" + auth.atlas_alignment_score + "/100)" : "";
        linksRow.appendChild(
          el("a", {
            className: "st-action-btn",
            href: "/labs/institutions/",
            textContent: "Institutional Atlas" + atlasScoreSuffix + " ↗"
          })
        );
      }

      return el("article", { className: colClass }, [
        el("div", { className: "sa-col-top" }, [
          el("span", { className: "st-tag" }, [
            el("span", { className: pipClass, "aria-hidden": "true" }),
            " SLOT " + slotTag + " · " + auth.code + " · " + (COHORT_LABELS[auth.cohort] || auth.cohort)
          ]),
          buildPipMeter(overlay.score)
        ]),
        el("h3", { className: "sa-org-title", textContent: auth.name }),
        el("p", {
          className: "sa-org-meta",
          textContent: auth.region + " · " + auth.subsector_label
        }),
        el("p", {
          className: "sa-org-focus",
          textContent: "Key bodies & statutes: " + (auth.key_institutions_and_statutes || "")
        }),
        axisStrip,
        el("div", { className: "sa-agent-box" }, [
          el("p", {
            className: "sa-kicker",
            textContent: "SOVEREIGN LIAISON ROLE · " + auth.specialized_agent_id
          }),
          el("p", { className: "sa-cell-copy", textContent: auth.sovereign_liaison_role })
        ]),
        el("div", { className: "sa-impact-pair" }, [
          el("div", { className: "sa-impact-block" }, [
            el("p", {
              className: "sa-kicker",
              textContent: activeAxis.code + " · EFFECT ON CITIZENS & WORKERS"
            }),
            el("p", { className: "sa-cell-copy", textContent: overlay.citizen_impact })
          ]),
          el("div", { className: "sa-impact-block sa-impact-block--org" }, [
            el("p", {
              className: "sa-kicker",
              textContent: activeAxis.code + " · EFFECT ON DOMESTIC LABS & AGENCIES"
            }),
            el("p", { className: "sa-cell-copy", textContent: overlay.state_and_lab_impact })
          ])
        ]),
        el("div", { className: "sa-conv-dev" }, [
          el("div", { className: "sa-conv-block" }, [
            el("p", { className: "sa-kicker", textContent: "WHERE PUBLIC-INTEREST POLICY CONVERGES WITH CIN" }),
            convergeList
          ]),
          el("div", { className: "sa-dev-block" }, [
            el("p", {
              className: "sa-kicker sa-kicker--warn",
              textContent: "WHERE PRIVATE CAPTURE OR STATE OVERREACH DEVIATES TODAY"
            }),
            deviateList
          ])
        ]),
        el("div", { className: "sa-engage-block" }, [
          el("p", { className: "sa-kicker", textContent: "PROPOSED STATUTORY & TREATY STEP" }),
          el("p", { className: "sa-cell-copy", textContent: auth.statutory_and_treaty_step }),
          linksRow
        ])
      ]);
    }

    function renderComparator() {
      if (!pairStage) return;
      var authA = byId[state.slotA] || authorities[0];
      var authB = byId[state.slotB] || authorities[1] || authorities[0];
      clearChildren(pairStage);
      pairStage.appendChild(buildAuthorityColumn(authA, "A"));
      pairStage.appendChild(buildAuthorityColumn(authB, "B"));
    }

    function buildExpandedDrawer(auth) {
      var activeAxis = axisById[state.axisId] || axes[0];
      var overlay = (auth.axis_overlays && auth.axis_overlays[activeAxis.id]) || {
        score: 3,
        citizen_impact: "",
        state_and_lab_impact: ""
      };

      var convList = el("ul", { className: "sa-point-list" });
      for (var c = 0; c < (auth.where_they_converge || []).length; c++) {
        convList.appendChild(
          el("li", null, [
            el("span", { className: "st-pip", "aria-hidden": "true" }),
            el("span", { textContent: auth.where_they_converge[c] })
          ])
        );
      }

      var devList = el("ul", { className: "sa-point-list sa-point-list--warn" });
      for (var d = 0; d < (auth.where_they_deviate || []).length; d++) {
        devList.appendChild(
          el("li", null, [
            el("span", { className: "st-pip st-pip--warn", "aria-hidden": "true" }),
            el("span", { textContent: auth.where_they_deviate[d] })
          ])
        );
      }

      return el("div", { className: "sa-drawer" }, [
        el("div", { className: "sa-drawer-grid" }, [
          el("div", { className: "sa-drawer-cell" }, [
            el("p", {
              className: "sa-kicker",
              textContent: "SOVEREIGN LIAISON · " + auth.specialized_agent_id
            }),
            el("p", { className: "sa-cell-copy", textContent: auth.sovereign_liaison_role })
          ]),
          el("div", { className: "sa-drawer-cell" }, [
            el("p", {
              className: "sa-kicker",
              textContent: activeAxis.code + " · EFFECT ON CITIZENS & WORKERS"
            }),
            el("p", { className: "sa-cell-copy", textContent: overlay.citizen_impact })
          ]),
          el("div", { className: "sa-drawer-cell" }, [
            el("p", {
              className: "sa-kicker",
              textContent: activeAxis.code + " · EFFECT ON DOMESTIC LABS & AGENCIES"
            }),
            el("p", { className: "sa-cell-copy", textContent: overlay.state_and_lab_impact })
          ])
        ]),
        el("div", { className: "sa-drawer-split" }, [
          el("div", { className: "sa-drawer-half" }, [
            el("p", { className: "sa-kicker", textContent: "WHERE PUBLIC-INTEREST POLICY CONVERGES WITH CIN" }),
            convList
          ]),
          el("div", { className: "sa-drawer-half" }, [
            el("p", {
              className: "sa-kicker sa-kicker--warn",
              textContent: "WHERE PRIVATE CAPTURE OR STATE OVERREACH DEVIATES TODAY"
            }),
            devList
          ])
        ]),
        el("div", { className: "sa-drawer-foot" }, [
          el("p", { className: "sa-cell-copy" }, [
            el("strong", { textContent: "Proposed statutory & treaty step: " }),
            auth.statutory_and_treaty_step
          ]),
          el("div", { className: "sa-links-row" }, [
            auth.sovereign_paper_url
              ? el("a", {
                  className: "st-action-btn sa-paper-btn",
                  href: auth.sovereign_paper_url,
                  textContent: "Read Sovereign Paper ↗"
                })
              : null,
            el("a", {
              className: "st-action-btn",
              href: auth.url,
              target: "_blank",
              rel: "noopener noreferrer",
              textContent: extractHost(auth.url) + " ↗"
            })
          ])
        ])
      ]);
    }

    function renderDirectory() {
      if (!rowsHost) return;
      var q = state.query.trim().toLowerCase();
      var activeAxis = axisById[state.axisId] || axes[0];

      var filtered = [];
      for (var i = 0; i < authorities.length; i++) {
        var o = authorities[i];
        if (state.cohort !== "all" && o.cohort !== state.cohort) continue;
        if (state.region !== "all" && o.region !== state.region) continue;
        if (q && o._searchBlob.indexOf(q) === -1) continue;
        filtered.push(o);
      }

      filtered.sort(function (a, b) {
        if (state.sort === "readiness") {
          var ra = (a.axis_overlays && a.axis_overlays[activeAxis.id] && a.axis_overlays[activeAxis.id].score) || 0;
          var rb = (b.axis_overlays && b.axis_overlays[activeAxis.id] && b.axis_overlays[activeAxis.id].score) || 0;
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
          " matched authorities (active axis: " +
          activeAxis.code +
          ")";
      }

      clearChildren(rowsHost);
      if (!filtered.length) {
        rowsHost.appendChild(
          el("p", {
            className: "sa-empty",
            textContent:
              "No sovereign or multilateral authority matched those filters. Reset filters to inspect all " +
              authorities.length +
              " profiles."
          })
        );
      } else {
        for (var r = 0; r < shownCount; r++) {
          (function (auth) {
            var isOpen = Boolean(state.expanded[auth.id]);
            var ov = (auth.axis_overlays && auth.axis_overlays[activeAxis.id]) || { score: 3 };
            var pipCls = auth.cohort === "national_authority" ? "st-pip" : "st-pip st-pip--amber";

            var axisTotal = axes.length || 5;
            var noteTotal =
              ((auth.where_they_converge && auth.where_they_converge.length) || 0) +
              ((auth.where_they_deviate && auth.where_they_deviate.length) || 0);
            var inspectBtn = el("button", {
              type: "button",
              className: "st-action-btn",
              "aria-expanded": isOpen ? "true" : "false",
              textContent: isOpen
                ? "Close brief −"
                : ("Inspect brief + (" + axisTotal + " axes · " + noteTotal + " notes)")
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
              state.expanded[auth.id] = !state.expanded[auth.id];
              renderDirectory();
            });
            pinABtn.addEventListener("click", function () {
              state.slotA = auth.id;
              if (selectA) selectA.value = auth.id;
              renderComparator();
              var wb = document.getElementById("sa-workbench");
              if (wb && wb.scrollIntoView) wb.scrollIntoView({ behavior: "smooth", block: "start" });
            });
            pinBBtn.addEventListener("click", function () {
              state.slotB = auth.id;
              if (selectB) selectB.value = auth.id;
              renderComparator();
              var wb = document.getElementById("sa-workbench");
              if (wb && wb.scrollIntoView) wb.scrollIntoView({ behavior: "smooth", block: "start" });
            });

            var rowWrap = el("div", { className: isOpen ? "sa-dir-item is-open" : "sa-dir-item" });
            var rowLine = el("div", { className: "sa-dir-row" }, [
              el("div", { className: "sa-dir-code" }, [
                el("span", { className: pipCls, "aria-hidden": "true" }),
                " " + auth.code
              ]),
              el("div", { className: "sa-dir-main" }, [
                el("h3", { className: "sa-dir-name", textContent: auth.name }),
                el("p", {
                  className: "sa-dir-sub",
                  textContent:
                    auth.region +
                    " · " +
                    auth.subsector_label +
                    (auth.key_institutions_and_statutes ? " · " + auth.key_institutions_and_statutes : "")
                }),
                el("p", {
                  className: "sa-dir-role",
                  textContent: auth.sovereign_liaison_role || ""
                })
              ]),
              el("div", { className: "sa-dir-readiness" }, [
                el("span", { className: "sa-readiness-tag", textContent: activeAxis.code }),
                buildPipMeter(ov.score)
              ]),
              el("div", { className: "sa-dir-actions" }, [
                auth.sovereign_paper_url
                  ? el("a", {
                      className: "st-action-btn sa-paper-btn",
                      href: auth.sovereign_paper_url,
                      textContent: "Sovereign Paper ↗"
                    })
                  : null,
                inspectBtn,
                pinABtn,
                pinBBtn
              ])
            ]);

            rowWrap.appendChild(rowLine);
            if (isOpen) {
              rowWrap.appendChild(buildExpandedDrawer(auth));
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

    if (axisBar) {
      clearChildren(axisBar);
      for (var idx = 0; idx < axes.length; idx++) {
        (function (ax) {
          var li = el("li");
          var btn = el(
            "button",
            {
              type: "button",
              className: ax.id === state.axisId ? "st-station-btn is-active" : "st-station-btn",
              "data-axis-id": ax.id,
              "aria-pressed": ax.id === state.axisId ? "true" : "false"
            },
            [
              el("span", { className: "st-pip", "aria-hidden": "true" }),
              " " + (ax.short_label || ax.title)
            ]
          );
          btn.addEventListener("click", function () {
            state.axisId = ax.id;
            renderAxisControls();
            renderComparator();
            renderDirectory();
          });
          li.appendChild(btn);
          axisBar.appendChild(li);
        })(axes[idx]);
      }
    }

    populateSelects();
    populateRegions();
    renderAxisControls();
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
    initWorkbenchAndDirectory(bundle);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
