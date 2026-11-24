/* Progressive interactivity for /labs/observatory/ (Signpost & Calibration Ledger + Two Institutional Paths Diptych).
 * Strict static-site guardrails: zero network calls, zero dynamic HTML parsing, full keyboard + screen-reader support.
 */
(function () {
  "use strict";

  function bindToolbarArrows(buttons) {
    if (!buttons || buttons.length < 2) return;
    buttons.forEach(function (btn, idx) {
      btn.addEventListener("keydown", function (ev) {
        var nextIdx = -1;
        if (ev.key === "ArrowRight" || ev.key === "ArrowDown") {
          nextIdx = (idx + 1) % buttons.length;
        } else if (ev.key === "ArrowLeft" || ev.key === "ArrowUp") {
          nextIdx = (idx - 1 + buttons.length) % buttons.length;
        } else if (ev.key === "Home") {
          nextIdx = 0;
        } else if (ev.key === "End") {
          nextIdx = buttons.length - 1;
        }
        if (nextIdx >= 0) {
          ev.preventDefault();
          buttons[nextIdx].focus();
        }
      });
    });
  }

  function formatBrier(val) {
    return val.toFixed(2);
  }

  function initSignpostLedger() {
    var ledgerRoot = document.getElementById("obs-ledger-panel");
    var dataEl = document.getElementById("observatory-signposts-data");
    if (!ledgerRoot || !dataEl) return;

    var parsed = null;
    try {
      parsed = JSON.parse(dataEl.textContent || "{}");
    } catch (err) {
      return;
    }
    if (!parsed || !Array.isArray(parsed.signposts)) return;

    var spById = {};
    var domainCounts = { all: parsed.signposts.length };
    var domainLabels = { all: "all 4 domains" };

    if (Array.isArray(parsed.domains)) {
      parsed.domains.forEach(function (d) {
        if (d && d.id) {
          domainCounts[d.id] = 0;
          domainLabels[d.id] = d.label || d.id;
        }
      });
    }

    parsed.signposts.forEach(function (sp) {
      if (!sp || !sp.id) return;
      spById[sp.id] = sp;
      if (sp.domain) {
        domainCounts[sp.domain] = (domainCounts[sp.domain] || 0) + 1;
      }
    });

    var domainBtns = Array.prototype.slice.call(
      ledgerRoot.querySelectorAll(".obs-domain-btn[data-domain]")
    );
    var viewBtns = Array.prototype.slice.call(
      ledgerRoot.querySelectorAll(".obs-view-btn[data-view]")
    );
    var cards = Array.prototype.slice.call(
      ledgerRoot.querySelectorAll(".obs-signpost-card[data-signpost]")
    );
    var statusEl = document.getElementById("obs-ledger-status");

    domainBtns.forEach(function (btn) {
      var dom = btn.getAttribute("data-domain") || "all";
      var countSpan = btn.querySelector(".obs-pill-count");
      if (countSpan && typeof domainCounts[dom] === "number") {
        countSpan.textContent = String(domainCounts[dom]);
      }
    });

    bindToolbarArrows(domainBtns);
    bindToolbarArrows(viewBtns);

    var activeDomain = "all";
    var activeView = "both";
    var activeSignpostId = null;

    var brierState = {
      prob: 0.65,
      outcome: 1,
      label: "Multi-hour autonomous coding crosses an eight-hour median horizon"
    };

    var probBtns = Array.prototype.slice.call(
      ledgerRoot.querySelectorAll(".obs-brier-prob-btn[data-prob]")
    );
    var outcomeBtns = Array.prototype.slice.call(
      ledgerRoot.querySelectorAll(".obs-brier-outcome-btn[data-outcome]")
    );
    var sliderSlot = document.getElementById("obs-brier-slider-slot");
    var markerEl = document.getElementById("obs-brier-marker");
    var scoreValEl = document.getElementById("obs-brier-score-val");
    var readoutEl = document.getElementById("obs-brier-readout");
    var rangeInput = null;
    var rangePctBadge = null;
    var cardGradeBtns = [];

    bindToolbarArrows(probBtns);
    bindToolbarArrows(outcomeBtns);

    if (sliderSlot) {
      var wrapDiv = document.createElement("div");
      wrapDiv.className = "obs-brier-range-row";

      var rangeLabel = document.createElement("label");
      rangeLabel.setAttribute("for", "obs-brier-range");
      rangeLabel.className = "obs-brier-range-label";
      rangeLabel.textContent = "Fine-tune stated probability: ";

      rangePctBadge = document.createElement("strong");
      rangePctBadge.textContent = "65%";
      rangeLabel.appendChild(rangePctBadge);

      rangeInput = document.createElement("input");
      rangeInput.type = "range";
      rangeInput.id = "obs-brier-range";
      rangeInput.className = "obs-brier-range";
      rangeInput.min = "5";
      rangeInput.max = "95";
      rangeInput.step = "5";
      rangeInput.value = "65";

      rangeInput.addEventListener("input", function () {
        var pct = parseInt(rangeInput.value, 10);
        if (isNaN(pct)) return;
        activeSignpostId = null;
        brierState.prob = pct / 100;
        brierState.label = "Custom probability check";
        syncBrierUI();
      });

      wrapDiv.appendChild(rangeLabel);
      wrapDiv.appendChild(rangeInput);
      sliderSlot.appendChild(wrapDiv);
    }

    function syncBrierUI() {
      var p = brierState.prob;
      var pct = Math.round(p * 100);
      var out = brierState.outcome;
      var score = Math.pow(p - out, 2);
      var altScore = Math.pow(p - (1 - out), 2);
      var diff = 0.25 - score;

      if (rangeInput) {
        rangeInput.value = String(pct);
      }
      if (rangePctBadge) {
        rangePctBadge.textContent = pct + "%";
      }

      probBtns.forEach(function (btn) {
        var bp = parseFloat(btn.getAttribute("data-prob") || "0");
        var match = Math.abs(bp - p) < 0.005;
        btn.setAttribute("aria-pressed", match ? "true" : "false");
        btn.classList.toggle("is-active", match);
      });

      outcomeBtns.forEach(function (btn) {
        var bo = parseInt(btn.getAttribute("data-outcome") || "0", 10);
        var match = bo === out;
        btn.setAttribute("aria-pressed", match ? "true" : "false");
        btn.classList.toggle("is-active", match);
      });

      cardGradeBtns.forEach(function (entry) {
        var isSel = entry.id === activeSignpostId;
        entry.btn.setAttribute("aria-pressed", isSel ? "true" : "false");
        entry.card.classList.toggle("is-selected", isSel);
      });

      if (markerEl) {
        var clamped = Math.max(0, Math.min(1, score));
        markerEl.style.left = (clamped * 100).toFixed(1) + "%";
      }
      if (scoreValEl) {
        scoreValEl.textContent = formatBrier(score);
      }

      if (readoutEl) {
        var verdict = "";
        if (Math.abs(diff) < 0.005) {
          verdict = "matches the 0.25 coin-flip baseline exactly";
        } else if (diff > 0) {
          verdict = "beats the 0.25 coin-flip baseline by " + formatBrier(diff);
        } else {
          verdict = "scores " + formatBrier(Math.abs(diff)) + " worse than a 0.25 coin flip";
        }

        var outcomePhrase = out === 1
          ? "if the milestone happens (outcome 1)"
          : "if the disconfirming tripwire triggers instead (outcome 0)";
        var oppositePhrase = out === 1
          ? "If the tripwire triggers instead, the penalty rises to " + formatBrier(altScore) + "."
          : "If the milestone happens as called, the score improves to " + formatBrier(altScore) + ".";
        var prefix = activeSignpostId && spById[activeSignpostId]
          ? "Grading \"" + spById[activeSignpostId].title + "\" at " + pct + "%: "
          : "At a " + pct + "% forecast, ";

        readoutEl.textContent =
          prefix + outcomePhrase + ", the Brier score is " + formatBrier(score) +
          " (" + verdict + "). " + oppositePhrase;
      }
    }

    cards.forEach(function (card) {
      var spId = card.getAttribute("data-signpost") || "";
      var sp = spById[spId];
      if (!sp) return;

      var pct = Math.round(sp.prior * 100);
      var hitScore = formatBrier(Math.pow(sp.prior - 1, 2));
      var missScore = formatBrier(Math.pow(sp.prior - 0, 2));

      var footer = document.createElement("div");
      footer.className = "obs-sp-footer";

      var stakes = document.createElement("span");
      stakes.className = "obs-sp-stakes";
      stakes.textContent =
        "Brier stakes: " + hitScore + " if confirmed · " + missScore + " if tripwire";

      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "obs-sp-grade-btn";
      btn.setAttribute("aria-pressed", "false");
      btn.textContent = "Test " + pct + "% in Brier grader";

      btn.addEventListener("click", function () {
        activeSignpostId = spId;
        brierState.prob = sp.prior;
        brierState.label = sp.title;
        syncBrierUI();
        var inspector = document.getElementById("obs-brier-inspector");
        if (inspector && typeof inspector.scrollIntoView === "function") {
          var reduced = window.matchMedia &&
            window.matchMedia("(prefers-reduced-motion: reduce)").matches;
          inspector.scrollIntoView({
            behavior: reduced ? "auto" : "smooth",
            block: "nearest"
          });
        }
      });

      footer.appendChild(stakes);
      footer.appendChild(btn);
      card.appendChild(footer);
      cardGradeBtns.push({ id: spId, btn: btn, card: card });
    });

    probBtns.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var val = parseFloat(btn.getAttribute("data-prob") || "0.5");
        if (isNaN(val)) return;
        activeSignpostId = null;
        brierState.prob = val;
        brierState.label = "Selected probability preset";
        syncBrierUI();
      });
    });

    outcomeBtns.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var out = parseInt(btn.getAttribute("data-outcome") || "1", 10);
        if (out !== 0 && out !== 1) return;
        brierState.outcome = out;
        syncBrierUI();
      });
    });

    function syncLedgerFilter() {
      var visibleCount = 0;
      cards.forEach(function (card) {
        var cDom = card.getAttribute("data-domain") || "";
        var showCard = activeDomain === "all" || cDom === activeDomain;
        card.hidden = !showCard;
        if (showCard) visibleCount += 1;

        var evBlock = card.querySelector(".obs-evidence-block");
        var twBlock = card.querySelector(".obs-tripwire-block");
        if (evBlock) {
          evBlock.hidden = activeView === "tripwire";
        }
        if (twBlock) {
          twBlock.hidden = activeView === "evidence";
        }
      });

      domainBtns.forEach(function (btn) {
        var dom = btn.getAttribute("data-domain") || "all";
        var isAct = dom === activeDomain;
        btn.setAttribute("aria-pressed", isAct ? "true" : "false");
        btn.classList.toggle("is-active", isAct);
      });

      viewBtns.forEach(function (btn) {
        var vw = btn.getAttribute("data-view") || "both";
        var isAct = vw === activeView;
        btn.setAttribute("aria-pressed", isAct ? "true" : "false");
        btn.classList.toggle("is-active", isAct);
      });

      if (statusEl) {
        var domDesc = activeDomain === "all"
          ? "across all 4 domains"
          : "in " + (domainLabels[activeDomain] || activeDomain);
        var viewDesc = "both Evidence today and What would prove us wrong (tripwire)";
        if (activeView === "evidence") {
          viewDesc = "Evidence today only";
        } else if (activeView === "tripwire") {
          viewDesc = "What would prove us wrong (tripwire) only";
        }
        statusEl.textContent =
          "Showing " + visibleCount + " " +
          (visibleCount === 1 ? "signpost" : "signposts") + " " +
          domDesc + ", displaying " + viewDesc + ".";
      }
    }

    domainBtns.forEach(function (btn) {
      btn.addEventListener("click", function () {
        activeDomain = btn.getAttribute("data-domain") || "all";
        syncLedgerFilter();
      });
    });

    viewBtns.forEach(function (btn) {
      btn.addEventListener("click", function () {
        activeView = btn.getAttribute("data-view") || "both";
        syncLedgerFilter();
      });
    });

    syncBrierUI();
    syncLedgerFilter();
  }

  function initPathsDiptych() {
    var root = document.getElementById("obs-paths-panel");
    if (!root) return;

    var lensBtns = Array.prototype.slice.call(
      root.querySelectorAll(".obs-path-lens-btn[data-path-lens]")
    );
    var stepper = document.getElementById("obs-pair-stepper");
    var pairBtns = Array.prototype.slice.call(
      root.querySelectorAll(".obs-pair-btn[data-pair-target]")
    );
    var pairs = Array.prototype.slice.call(
      root.querySelectorAll(".obs-diptych-pair[data-pair]")
    );
    var statusEl = document.getElementById("obs-paths-status");

    bindToolbarArrows(lensBtns);
    bindToolbarArrows(pairBtns);

    var activeLens = "all";
    var activePair = "1";

    var pairNames = {
      "1": "Personal life, attention, and human skill",
      "2": "Automated production and household security",
      "3": "Agent traffic, shadow ledgers, and physical safety"
    };

    function syncPaths() {
      root.setAttribute("data-active-lens", activeLens);

      if (stepper) {
        stepper.hidden = activeLens !== "compare";
      }

      lensBtns.forEach(function (btn) {
        var lens = btn.getAttribute("data-path-lens") || "all";
        var isAct = lens === activeLens;
        btn.setAttribute("aria-pressed", isAct ? "true" : "false");
        btn.classList.toggle("is-active", isAct);
      });

      pairBtns.forEach(function (btn) {
        var target = btn.getAttribute("data-pair-target") || "1";
        var isAct = target === activePair;
        btn.setAttribute("aria-pressed", isAct ? "true" : "false");
        btn.classList.toggle("is-active", isAct);
      });

      pairs.forEach(function (pairEl) {
        var pNum = pairEl.getAttribute("data-pair") || "";
        var showPair = activeLens !== "compare" || pNum === activePair;
        pairEl.hidden = !showPair;

        var figs = Array.prototype.slice.call(
          pairEl.querySelectorAll(".obs-path-fig[data-side]")
        );
        figs.forEach(function (fig) {
          var side = fig.getAttribute("data-side") || "";
          if (activeLens === "drift") {
            fig.hidden = side !== "drift";
          } else if (activeLens === "governed") {
            fig.hidden = side !== "governed";
          } else {
            fig.hidden = false;
          }
        });
      });

      if (statusEl) {
        if (activeLens === "all") {
          statusEl.textContent =
            "Showing all 3 everyday comparison pairs side by side (6 vignettes).";
        } else if (activeLens === "compare") {
          statusEl.textContent =
            "Side-by-side spotlight: Pair " + activePair + " of 3, " +
            (pairNames[activePair] || "") + ".";
        } else if (activeLens === "drift") {
          statusEl.textContent =
            "Focus on drift risk: showing 3 vignettes where closed cloud lock-in, concentrated mills, and unmarked agent canals erode human oversight.";
        } else if (activeLens === "governed") {
          statusEl.textContent =
            "Focus on governed path: showing 3 vignettes where local sanctuary tools, cooperative mills, and lantern-lit canal locks keep people in charge.";
        }
      }
    }

    lensBtns.forEach(function (btn) {
      btn.addEventListener("click", function () {
        activeLens = btn.getAttribute("data-path-lens") || "all";
        syncPaths();
      });
    });

    pairBtns.forEach(function (btn) {
      btn.addEventListener("click", function () {
        activePair = btn.getAttribute("data-pair-target") || "1";
        syncPaths();
      });
    });

    syncPaths();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      initSignpostLedger();
      initPathsDiptych();
    });
  } else {
    initSignpostLedger();
    initPathsDiptych();
  }
})();
