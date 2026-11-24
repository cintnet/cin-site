/* ==========================================================================
   CIN Anti-Card Spatial & Tactile Stage Engine (stages.js)
   Progressive enhancement for:
     - [data-stage="bench"]       (keycaps [1][2][3], mode toggle, TTL & stamp)
     - [data-stage="matrix"]      (1px hairline coordinate rail + schematic)
     - [data-stage="switchboard"] (multi-station orthogonal trace router)
     - [data-stage="switchyard"]  (dual-rail lever & checkpoint switch)
   Pure DOM textContent and attribute updates; zero network calls.
   ========================================================================== */
(function () {
  "use strict";

  function isEditableTarget(el) {
    if (!el || !el.tagName) return false;
    var tag = el.tagName.toUpperCase();
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
    return el.getAttribute("contenteditable") === "true";
  }

  function computeHexDigest(seed) {
    var h1 = 0x811c9dc5;
    var h2 = 0x01000193;
    var str = String(seed || "cin-stage");
    for (var i = 0; i < str.length; i++) {
      var c = str.charCodeAt(i);
      h1 ^= c;
      h1 = Math.imul ? Math.imul(h1, 0x01000193) : (h1 * 16777619) | 0;
      h2 ^= (c + i) & 0xff;
      h2 = Math.imul ? Math.imul(h2, 0x85ebca6b) : (h2 * 2246822507) | 0;
    }
    var a = (h1 >>> 0).toString(16).toUpperCase();
    var b = (h2 >>> 0).toString(16).toUpperCase();
    while (a.length < 8) a = "0" + a;
    while (b.length < 8) b = "0" + b;
    return a.slice(0, 4) + "-" + b.slice(0, 4);
  }

  function formatSeconds(sec) {
    var s = Math.max(0, sec | 0);
    var m = Math.floor(s / 60);
    var r = s % 60;
    return (m < 10 ? "0" + m : String(m)) + ":" + (r < 10 ? "0" + r : String(r));
  }

  /* ------------------------------------------------------------------------
     1. [data-stage="bench"]
     ------------------------------------------------------------------------ */
  function initBenchStage(stage, benchRegistry) {
    var keyBtns = Array.prototype.slice.call(
      stage.querySelectorAll("[data-bench-key], [data-stage-key]")
    );
    var modeBtns = Array.prototype.slice.call(
      stage.querySelectorAll("[data-bench-mode]")
    );
    var specRows = Array.prototype.slice.call(
      stage.querySelectorAll("[data-stage-panel]")
    );
    var ttlNode = stage.querySelector("[data-receipt-ttl]");
    var stampBtn = stage.querySelector("[data-receipt-stamp]");
    var sealNode = stage.querySelector("[data-receipt-seal]");
    var receiptSlip = stage.querySelector(".st-receipt-slip");
    var svgEl = stage.querySelector("svg");

    var state = {
      key: stage.getAttribute("data-active-key") || "1",
      mode: stage.getAttribute("data-wire-state") || "valet",
      ttlInitial: ttlNode
        ? parseInt(ttlNode.getAttribute("data-receipt-ttl") || "120", 10) || 120
        : 120,
      ttlRemaining: 120,
      stamped: false,
      stampSeq: 0
    };
    state.ttlRemaining = state.ttlInitial;

    function getActiveKeyButton() {
      for (var i = 0; i < keyBtns.length; i++) {
        var k =
          keyBtns[i].getAttribute("data-bench-key") ||
          keyBtns[i].getAttribute("data-stage-key");
        if (k === state.key) return keyBtns[i];
      }
      return keyBtns[0] || null;
    }

    function setField(fieldName, text) {
      if (!text) return;
      var nodes = stage.querySelectorAll(
        '[data-receipt-field="' + fieldName + '"]'
      );
      for (var i = 0; i < nodes.length; i++) {
        nodes[i].textContent = text;
      }
    }

    function renderBench() {
      stage.setAttribute("data-active-key", state.key);
      stage.setAttribute("data-wire-state", state.mode);
      stage.setAttribute("data-wire-mode", state.mode);
      if (svgEl) {
        svgEl.setAttribute("data-active-key", state.key);
        svgEl.setAttribute("data-wire-state", state.mode);
      }

      for (var i = 0; i < keyBtns.length; i++) {
        var btn = keyBtns[i];
        var k =
          btn.getAttribute("data-bench-key") ||
          btn.getAttribute("data-stage-key");
        var isKeyActive = k === state.key;
        btn.setAttribute("aria-pressed", isKeyActive ? "true" : "false");
        btn.classList.toggle("is-active", isKeyActive);
      }

      for (var j = 0; j < modeBtns.length; j++) {
        var mBtn = modeBtns[j];
        var mVal = mBtn.getAttribute("data-bench-mode");
        var isModeActive = mVal === state.mode;
        mBtn.setAttribute("aria-pressed", isModeActive ? "true" : "false");
        mBtn.classList.toggle("is-active", isModeActive);
      }

      for (var p = 0; p < specRows.length; p++) {
        var row = specRows[p];
        var pKey = row.getAttribute("data-stage-panel");
        var isPanelActive = pKey === state.key;
        row.classList.toggle("is-active", isPanelActive);
        row.setAttribute("data-active", isPanelActive ? "true" : "false");
        if (row.hasAttribute("data-exclusive-panel")) {
          if (isPanelActive) {
            row.removeAttribute("hidden");
          } else {
            row.setAttribute("hidden", "");
          }
        }
      }

      var activeBtn = getActiveKeyButton();
      if (activeBtn) {
        var isMaster = state.mode === "master" || state.mode === "ambient";
        var taskText = activeBtn.getAttribute("data-receipt-task");
        var scopeText = isMaster
          ? activeBtn.getAttribute("data-master-scope") ||
            activeBtn.getAttribute("data-receipt-scope")
          : activeBtn.getAttribute("data-valet-scope") ||
            activeBtn.getAttribute("data-receipt-scope");
        var trapText = activeBtn.getAttribute("data-receipt-trap");
        var verdictText = isMaster
          ? activeBtn.getAttribute("data-master-verdict") ||
            activeBtn.getAttribute("data-receipt-verdict")
          : activeBtn.getAttribute("data-valet-verdict") ||
            activeBtn.getAttribute("data-receipt-verdict");

        setField("task", taskText);
        setField("scope", scopeText);
        setField("trap", trapText);
        setField("verdict", verdictText);
      }

      var digest = computeHexDigest(
        (stage.id || "bench") + ":" + state.key + ":" + state.mode
      );
      setField("digest", "RECEIPT #" + digest);

      if (ttlNode) {
        if (state.mode === "master" || state.mode === "ambient") {
          ttlNode.textContent = "NO EXPIRY (AMBIENT)";
        } else {
          ttlNode.textContent =
            formatSeconds(state.ttlRemaining) + " LEASE TTL";
        }
      }

      if (receiptSlip) {
        receiptSlip.setAttribute(
          "data-stamped",
          state.stamped ? "true" : "false"
        );
      }
      if (stampBtn) {
        stampBtn.setAttribute("aria-pressed", state.stamped ? "true" : "false");
      }
      if (sealNode) {
        if (state.stamped) {
          var stampHash = computeHexDigest(
            "OOB:" + state.key + ":" + state.mode + ":" + state.stampSeq
          );
          sealNode.textContent =
            "APPROVED · OUT-OF-BAND · SIG #" + stampHash;
        } else if (state.mode === "master" || state.mode === "ambient") {
          sealNode.textContent =
            "UNSTAMPED · Master key skips out-of-band check.";
        } else {
          sealNode.textContent =
            "AWAITING · Out-of-band human stamp required for side-effects.";
        }
      }
    }

    for (var i = 0; i < keyBtns.length; i++) {
      (function (btn) {
        btn.addEventListener("click", function () {
          var nextKey =
            btn.getAttribute("data-bench-key") ||
            btn.getAttribute("data-stage-key");
          if (nextKey) {
            state.key = nextKey;
            state.stamped = false;
            state.ttlRemaining = state.ttlInitial;
            renderBench();
          }
        });
      })(keyBtns[i]);
    }

    for (var m = 0; m < modeBtns.length; m++) {
      (function (mBtn) {
        mBtn.addEventListener("click", function () {
          var nextMode = mBtn.getAttribute("data-bench-mode");
          if (nextMode) {
            state.mode = nextMode;
            state.stamped = false;
            state.ttlRemaining = state.ttlInitial;
            renderBench();
          }
        });
      })(modeBtns[m]);
    }

    for (var s = 0; s < specRows.length; s++) {
      (function (row) {
        row.addEventListener("click", function (ev) {
          if (ev.target && ev.target.closest && ev.target.closest("a")) return;
          var pKey = row.getAttribute("data-stage-panel");
          if (pKey) {
            state.key = pKey;
            state.stamped = false;
            renderBench();
          }
        });
      })(specRows[s]);
    }

    if (stampBtn) {
      stampBtn.addEventListener("click", function () {
        state.stamped = !state.stamped;
        if (state.stamped) state.stampSeq += 1;
        renderBench();
        if (state.stamped && window.innerWidth <= 720) {
          var scrollTarget =
            sealNode || stage.querySelector(".st-receipt-verdict") || receiptSlip;
          if (scrollTarget && scrollTarget.scrollIntoView) {
            var reduceMotionNow =
              window.matchMedia &&
              window.matchMedia("(prefers-reduced-motion: reduce)").matches;
            scrollTarget.scrollIntoView({
              behavior: reduceMotionNow ? "auto" : "smooth",
              block: "nearest"
            });
          }
        }
      });
    }

    if (ttlNode) {
      var reduceMotion =
        window.matchMedia &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      if (!reduceMotion) {
        window.setInterval(function () {
          if (document.hidden) return;
          if (state.mode === "master" || state.mode === "ambient") return;
          state.ttlRemaining =
            state.ttlRemaining > 1 ? state.ttlRemaining - 1 : state.ttlInitial;
          ttlNode.textContent =
            formatSeconds(state.ttlRemaining) + " LEASE TTL";
        }, 1000);
      }
    }

    renderBench();

    benchRegistry.push({
      stage: stage,
      selectKey: function (k) {
        for (var idx = 0; idx < keyBtns.length; idx++) {
          var candidate =
            keyBtns[idx].getAttribute("data-bench-key") ||
            keyBtns[idx].getAttribute("data-stage-key");
          if (candidate === k) {
            state.key = k;
            state.stamped = false;
            state.ttlRemaining = state.ttlInitial;
            renderBench();
            return true;
          }
        }
        return false;
      }
    });
  }

  /* ------------------------------------------------------------------------
     2. [data-stage="matrix"]
     ------------------------------------------------------------------------ */
  function initMatrixStage(stage) {
    var triggers = Array.prototype.slice.call(
      stage.querySelectorAll("[data-matrix-trigger]")
    );
    if (!triggers.length) return;

    var statusNode = stage.querySelector("[data-matrix-status]");
    var readoutNode = stage.querySelector("[data-matrix-readout]");
    var activeId =
      stage.getAttribute("data-active-index") ||
      triggers[0].getAttribute("data-matrix-trigger");

    function activate(id) {
      activeId = id;
      stage.setAttribute("data-active-index", id);
      for (var i = 0; i < triggers.length; i++) {
        var btn = triggers[i];
        var tId = btn.getAttribute("data-matrix-trigger");
        var isCurrent = tId === id;
        btn.setAttribute("aria-pressed", isCurrent ? "true" : "false");
        btn.classList.toggle("is-active", isCurrent);
        if (isCurrent) {
          var stText = btn.getAttribute("data-status");
          var rdText = btn.getAttribute("data-readout");
          if (statusNode && stText) statusNode.textContent = stText;
          if (readoutNode && rdText) readoutNode.textContent = rdText;
        }
      }
    }

    for (var i = 0; i < triggers.length; i++) {
      (function (idx) {
        var btn = triggers[idx];
        btn.addEventListener("click", function () {
          activate(btn.getAttribute("data-matrix-trigger"));
        });
        btn.addEventListener("keydown", function (e) {
          var nextIdx = -1;
          if (e.key === "ArrowDown" || e.key === "ArrowRight") {
            nextIdx = (idx + 1) % triggers.length;
          } else if (e.key === "ArrowUp" || e.key === "ArrowLeft") {
            nextIdx = (idx - 1 + triggers.length) % triggers.length;
          } else if (e.key === "Home") {
            nextIdx = 0;
          } else if (e.key === "End") {
            nextIdx = triggers.length - 1;
          }
          if (nextIdx >= 0) {
            e.preventDefault();
            triggers[nextIdx].focus();
            activate(triggers[nextIdx].getAttribute("data-matrix-trigger"));
          }
        });
      })(i);
    }

    activate(activeId);
  }

  /* ------------------------------------------------------------------------
     3. [data-stage="switchboard"]
     ------------------------------------------------------------------------ */
  function initSwitchboardStage(stage) {
    var btns = Array.prototype.slice.call(
      stage.querySelectorAll("button[data-station]")
    );
    var svgStations = Array.prototype.slice.call(
      stage.querySelectorAll("svg [data-station-node]")
    );
    var traces = Array.prototype.slice.call(
      stage.querySelectorAll("svg [data-trace-for]")
    );
    var readoutNode = stage.querySelector("[data-telemetry-readout]");
    var stationTagNode = stage.querySelector("[data-telemetry-tag]");

    if (!btns.length) return;
    var activeStation =
      stage.getAttribute("data-active-station") ||
      btns[0].getAttribute("data-station");

    function selectStation(stationId) {
      activeStation = stationId;
      stage.setAttribute("data-active-station", stationId);

      for (var i = 0; i < btns.length; i++) {
        var b = btns[i];
        var sId = b.getAttribute("data-station");
        var isSel = sId === stationId;
        b.setAttribute("aria-pressed", isSel ? "true" : "false");
        b.classList.toggle("is-active", isSel);
        if (isSel) {
          var tele = b.getAttribute("data-telemetry");
          var tag = b.getAttribute("data-tag");
          if (readoutNode && tele) readoutNode.textContent = tele;
          if (stationTagNode && tag) stationTagNode.textContent = tag;
        }
      }

      for (var t = 0; t < traces.length; t++) {
        var tr = traces[t];
        var owners = (tr.getAttribute("data-trace-for") || "").split(/\s+/);
        var match =
          stationId === "all" || owners.indexOf(stationId) !== -1;
        tr.classList.toggle("is-active", match);
        tr.setAttribute("data-trace-active", match ? "true" : "false");
      }
    }

    for (var i = 0; i < btns.length; i++) {
      (function (btn) {
        btn.addEventListener("click", function () {
          selectStation(btn.getAttribute("data-station"));
        });
      })(btns[i]);
    }

    for (var s = 0; s < svgStations.length; s++) {
      (function (node) {
        node.style.cursor = "pointer";
        node.addEventListener("click", function () {
          var targetId = node.getAttribute("data-station-node");
          if (targetId) selectStation(targetId);
        });
      })(svgStations[s]);
    }

    selectStation(activeStation);
  }

  /* ------------------------------------------------------------------------
     4. [data-stage="switchyard"]
     ------------------------------------------------------------------------ */
  function initSwitchyardStage(stage) {
    var optionBtns = Array.prototype.slice.call(
      stage.querySelectorAll("button[data-rail-option], button[data-rail-mode]")
    );
    var flipBtn = stage.querySelector("button[data-rail-toggle]");
    var readoutNode = stage.querySelector("[data-rail-readout]");
    var statusNode = stage.querySelector("[data-rail-status]");
    var svgEl = stage.querySelector("svg");

    var currentMode = stage.getAttribute("data-rail-mode") || "separated";

    function applyMode(mode) {
      currentMode = mode;
      stage.setAttribute("data-rail-mode", mode);
      if (svgEl) svgEl.setAttribute("data-rail-mode", mode);

      for (var i = 0; i < optionBtns.length; i++) {
        var b = optionBtns[i];
        var bMode =
          b.getAttribute("data-rail-option") ||
          b.getAttribute("data-rail-mode");
        var isMatch = bMode === mode;
        b.setAttribute("aria-pressed", isMatch ? "true" : "false");
        b.classList.toggle("is-active", isMatch);
        if (isMatch) {
          var rd = b.getAttribute("data-readout");
          var st = b.getAttribute("data-status");
          if (readoutNode && rd) readoutNode.textContent = rd;
          if (statusNode && st) statusNode.textContent = st;
        }
      }
    }

    for (var i = 0; i < optionBtns.length; i++) {
      (function (btn) {
        btn.addEventListener("click", function () {
          var m =
            btn.getAttribute("data-rail-option") ||
            btn.getAttribute("data-rail-mode");
          if (m) applyMode(m);
        });
      })(optionBtns[i]);
    }

    if (flipBtn) {
      flipBtn.addEventListener("click", function () {
        var modeA = flipBtn.getAttribute("data-mode-a") || "shared";
        var modeB = flipBtn.getAttribute("data-mode-b") || "separated";
        applyMode(currentMode === modeA ? modeB : modeA);
      });
    }

    applyMode(currentMode);
  }

  /* ------------------------------------------------------------------------
     Bootstrap all stages & global [1] [2] [3] bench shortcut listener
     ------------------------------------------------------------------------ */
  function initAllStages() {
    var benchRegistry = [];
    var stages = document.querySelectorAll("[data-stage]");
    for (var i = 0; i < stages.length; i++) {
      var st = stages[i];
      var kind = st.getAttribute("data-stage");
      if (kind === "bench") {
        initBenchStage(st, benchRegistry);
      } else if (kind === "matrix") {
        initMatrixStage(st);
      } else if (kind === "switchboard") {
        initSwitchboardStage(st);
      } else if (kind === "switchyard") {
        initSwitchyardStage(st);
      }
    }

    if (benchRegistry.length > 0) {
      document.addEventListener("keydown", function (e) {
        if (e.ctrlKey || e.metaKey || e.altKey) return;
        if (isEditableTarget(e.target)) return;
        if (e.key === "1" || e.key === "2" || e.key === "3") {
          for (var b = 0; b < benchRegistry.length; b++) {
            var rect = benchRegistry[b].stage.getBoundingClientRect();
            if (rect.bottom > 0 && rect.top < window.innerHeight) {
              benchRegistry[b].selectKey(e.key);
              break;
            }
          }
        }
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAllStages);
  } else {
    initAllStages();
  }
})();
