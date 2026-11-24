// cintnet.org: Interactive Wind-Tunnel Lab (/labs/simulations/)
// Progressive enhancement only: static HTML renders baseline trajectories without JS.
// Strict DOM safety: zero raw HTML injection, dynamic evaluation, or network calls.
(function () {
  "use strict";

  var X_LEFT = 64.0;
  var X_RIGHT = 648.0;
  var Y_TOP = 28.0;
  var Y_BOTTOM = 232.0;

  function clamp(val, lo, hi) {
    return Math.min(hi, Math.max(lo, val));
  }

  function fmt1(val) {
    return (Math.round(val * 10) / 10).toFixed(1);
  }

  // ------------------------------------------------------------------
  // Panel 1: Automated production & cooperative ownership transition
  // ------------------------------------------------------------------
  function initCoopPanel() {
    var panel = document.getElementById("sim-panel-coop");
    if (!panel) return;

    var autoInput = document.getElementById("sim-auto-end");
    var deltaInput = document.getElementById("sim-meidner-delta");
    var floorInput = document.getElementById("sim-baseline-floor");
    var creditInput = document.getElementById("sim-mutual-credit");
    var steerInput = document.getElementById("sim-durability-steer");

    if (!autoInput || !deltaInput || !floorInput || !creditInput || !steerInput) return;

    var autoOut = document.getElementById("sim-auto-end-out");
    var deltaOut = document.getElementById("sim-meidner-delta-out");
    var floorOut = document.getElementById("sim-baseline-floor-out");
    var creditOut = document.getElementById("sim-mutual-credit-out");
    var steerOut = document.getElementById("sim-durability-steer-out");

    var pathCoopDur = document.getElementById("sim-p1-path-coop-dur");
    var pathCoopOwn = document.getElementById("sim-p1-path-coop-own");
    var pathEncDur = document.getElementById("sim-p1-path-enc-dur");
    var dotCoopDur = document.getElementById("sim-p1-dot-coop-dur");
    var dotCoopOwn = document.getElementById("sim-p1-dot-coop-own");
    var dotEncDur = document.getElementById("sim-p1-dot-enc-dur");
    var tickEndLabel = document.getElementById("sim-p1-tick-end");

    var kpiOwn = document.getElementById("sim-p1-kpi-own");
    var kpiUtil = document.getElementById("sim-p1-kpi-util");
    var kpiDur = document.getElementById("sim-p1-kpi-dur");
    var kpiLedger = document.getElementById("sim-p1-kpi-ledger");
    var statusText = document.getElementById("sim-p1-status-text");
    var presetBtns = Array.prototype.slice.call(panel.querySelectorAll(".sim-preset-btn"));

    var presets = {
      enclosure: { auto: 95, delta: 0, floor: 0, credit: 0, steer: 0 },
      balanced: { auto: 95, delta: 14, floor: 18, credit: 85, steer: 100 },
      rapid: { auto: 98, delta: 22, floor: 24, credit: 100, steer: 100 }
    };

    function syncPresetState() {
      var curAuto = Number(autoInput.value);
      var curDelta = Number(deltaInput.value);
      var curFloor = Number(floorInput.value);
      var curCredit = Number(creditInput.value);
      var curSteer = Number(steerInput.value);

      presetBtns.forEach(function (btn) {
        var key = btn.getAttribute("data-preset") || "";
        var p = presets[key];
        var match = Boolean(
          p &&
          p.auto === curAuto &&
          p.delta === curDelta &&
          p.floor === curFloor &&
          p.credit === curCredit &&
          p.steer === curSteer
        );
        btn.classList.toggle("is-active", match);
        btn.setAttribute("aria-pressed", match ? "true" : "false");
      });
    }

    function updateCoop() {
      var autoEndPct = clamp(Number(autoInput.value) || 95, 50, 98);
      var deltaPct = clamp(Number(deltaInput.value) || 0, 0, 25);
      var floorPct = clamp(Number(floorInput.value) || 0, 0, 30);
      var creditPct = clamp(Number(creditInput.value) || 0, 0, 100);
      var steerPct = clamp(Number(steerInput.value) || 0, 0, 100);

      var autoEnd = autoEndPct / 100.0;
      var delta = deltaPct / 100.0;
      var bFloor = floorPct / 100.0;
      var mcShare = creditPct / 100.0;
      var steer = steerPct / 100.0;

      if (autoOut) autoOut.textContent = autoEndPct + "%";
      if (deltaOut) deltaOut.textContent = deltaPct + "% / yr";
      if (floorOut) floorOut.textContent = floorPct + "%";
      if (creditOut) creditOut.textContent = creditPct + "%";
      if (steerOut) steerOut.textContent = steerPct + "%";

      autoInput.setAttribute("aria-valuetext", autoEndPct + " percent final automated production");
      deltaInput.setAttribute("aria-valuetext", deltaPct + " percent annual cooperative share dilution");
      floorInput.setAttribute("aria-valuetext", floorPct + " percent unconditional essentials floor");
      creditInput.setAttribute("aria-valuetext", creditPct + " percent capacity-backed mutual credit clearing");
      steerInput.setAttribute("aria-valuetext", steerPct + " percent 30-day durability signal coverage");

      var coop = 0.06;
      var priv = 0.94;
      var balancesMicro = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]; // 9 household + 3 producer cohorts

      var ptsCoopDur = [];
      var ptsCoopOwn = [];
      var ptsEncDur = [];

      var lastUtilCoop = 0;
      var lastUtilEnc = 0;
      var lastDurCoop = 0;
      var lastDurUtilCoop = 0;
      var lastDurUtilEnc = 0;
      var lastCoopPct = 6;
      var lastX = X_RIGHT;
      var lastYCoopDur = Y_BOTTOM;
      var lastYCoopOwn = Y_BOTTOM;
      var lastYEncDur = Y_BOTTOM;

      for (var t = 0; t < 30; t++) {
        var prog = t / 29.0;
        var aT = 0.25 + (autoEnd - 0.25) * prog;
        var x = X_LEFT + prog * (X_RIGHT - X_LEFT);

        // Baseline: Concentrated enclosure (delta = 0, floor = 0, credit = 0, steer = 0)
        var capE = 100.0 * (1.0 + 1.80 * aT);
        var liqE = 1.0 - 0.06 * (1.0 - 0.5 * 0.06);
        var cashE = liqE * (0.92 * ((1.0 - aT) * capE + 0.06 * aT * capE) + 0.11 * (0.94 * aT * capE));
        var utilE = clamp((cashE / capE) * 100.0, 0.0, 100.0);
        var durE = clamp(0.72 - 0.14 * aT, 0.40, 0.98);
        var durUtilE = utilE * durE;
        var yE = Y_BOTTOM - (durUtilE / 100.0) * (Y_BOTTOM - Y_TOP);
        ptsEncDur.push(fmt1(x) + "," + fmt1(yE));

        // Selected policy trajectory
        var blindRate = delta > 0 ? 0.04 * Math.min(1.0, delta / 0.10) : 0.0;
        var issuance = delta * Math.max(0.0, aT - 0.30) + blindRate * aT;
        priv = priv / (1.0 + issuance);
        coop = 1.0 - priv;

        var cap = 100.0 * (1.0 + 1.80 * aT) * (1.0 + 0.35 * blindRate * coop * aT);
        var baseP = bFloor * cap;
        var mkt = cap - baseP;
        var liq = 1.0 - 0.06 * (1.0 - 0.5 * coop);
        var cash = Math.min(cap, baseP + liq * (0.92 * ((1.0 - aT) * mkt + coop * aT * mkt) + 0.11 * (priv * aT * mkt)));
        var slack = Math.max(0.0, cap - cash);
        var reach = Math.min(1.0, 0.35 + 0.65 * coop);
        var mcVol = slack * mcShare * reach;

        // Exact integer micro-credit clearing & expiring-balance conservation check
        var tradeMicro = Math.round(mcVol * 1000);
        if (tradeMicro > 0) {
          var perBuyer = Math.floor(tradeMicro / 9);
          var remBuyer = tradeMicro - perBuyer * 9;
          for (var bIdx = 0; bIdx < 9; bIdx++) {
            balancesMicro[bIdx] -= (perBuyer + (bIdx < remBuyer ? 1 : 0));
          }
          var perProd = Math.floor(tradeMicro / 3);
          var remProd = tradeMicro - perProd * 3;
          for (var pIdx = 0; pIdx < 3; pIdx++) {
            balancesMicro[9 + pIdx] += (perProd + (pIdx < remProd ? 1 : 0));
          }
        }

        var eff = Math.min(cap, cash + mcVol);
        var utilC = clamp((eff / cap) * 100.0, 0.0, 100.0);
        var durC = clamp((1.0 - steer) * (0.72 - 0.14 * aT) + steer * (0.84 + 0.11 * coop), 0.40, 0.98);
        var durUtilC = utilC * durC;

        var yC = Y_BOTTOM - (durUtilC / 100.0) * (Y_BOTTOM - Y_TOP);
        var yOwn = Y_BOTTOM - coop * (Y_BOTTOM - Y_TOP);

        ptsCoopDur.push(fmt1(x) + "," + fmt1(yC));
        ptsCoopOwn.push(fmt1(x) + "," + fmt1(yOwn));

        lastUtilCoop = Math.round(utilC);
        lastUtilEnc = Math.round(utilE);
        lastDurCoop = Math.round(durC * 100.0);
        lastDurUtilCoop = Math.round(durUtilC);
        lastDurUtilEnc = Math.round(durUtilE);
        lastCoopPct = Math.round(coop * 100.0);
        lastX = x;
        lastYCoopDur = yC;
        lastYCoopOwn = yOwn;
        lastYEncDur = yE;
      }

      var sumMicro = 0;
      for (var k = 0; k < balancesMicro.length; k++) {
        sumMicro += balancesMicro[k];
      }

      if (pathCoopDur) pathCoopDur.setAttribute("d", "M " + ptsCoopDur.join(" L "));
      if (pathCoopOwn) pathCoopOwn.setAttribute("d", "M " + ptsCoopOwn.join(" L "));
      if (pathEncDur) pathEncDur.setAttribute("d", "M " + ptsEncDur.join(" L "));

      if (dotCoopDur) {
        dotCoopDur.setAttribute("cx", fmt1(lastX));
        dotCoopDur.setAttribute("cy", fmt1(lastYCoopDur));
      }
      if (dotCoopOwn) {
        dotCoopOwn.setAttribute("cx", fmt1(lastX));
        dotCoopOwn.setAttribute("cy", fmt1(lastYCoopOwn));
      }
      if (dotEncDur) {
        dotEncDur.setAttribute("cx", fmt1(lastX));
        dotEncDur.setAttribute("cy", fmt1(lastYEncDur));
      }
      if (tickEndLabel) {
        tickEndLabel.textContent = "Period 30 (" + autoEndPct + "% automated)";
      }

      if (kpiOwn) kpiOwn.textContent = lastCoopPct + "%";
      if (kpiUtil) kpiUtil.textContent = lastUtilCoop + "% vs " + lastUtilEnc + "%";
      if (kpiDur) kpiDur.textContent = lastDurCoop + "% (" + lastDurUtilCoop + "% net)";
      if (kpiLedger) kpiLedger.textContent = (sumMicro / 1000.0).toFixed(2) + " (balanced)";

      if (statusText) {
        if (lastDurUtilCoop >= 75) {
          statusText.textContent =
            "At " + autoEndPct + "% automation, cooperative ownership reaches " + lastCoopPct +
            "% and keeps " + lastUtilCoop + "% of factory capacity active (" + lastDurUtilCoop +
            "% durable household output, compared with " + lastDurUtilEnc + "% under concentrated enclosure).";
        } else if (lastDurUtilCoop >= 40) {
          statusText.textContent =
            "Partial transition: at " + autoEndPct + "% automation, " + lastUtilCoop +
            "% of factory capacity clears (" + lastDurUtilCoop +
            "% durable output), leaving noticeable idle capacity when wage share drops.";
        } else {
          statusText.textContent =
            "Demand stall warning: at " + autoEndPct + "% automation with " + lastCoopPct +
            "% cooperative equity, household wages shrink while private equity stays concentrated, leaving " +
            (100 - lastUtilCoop) + "% of factory capacity idle.";
        }
      }

      syncPresetState();
    }

    [autoInput, deltaInput, floorInput, creditInput, steerInput].forEach(function (inp) {
      inp.addEventListener("input", updateCoop);
      inp.addEventListener("change", updateCoop);
    });

    presetBtns.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var key = btn.getAttribute("data-preset") || "";
        var p = presets[key];
        if (!p) return;
        autoInput.value = String(p.auto);
        deltaInput.value = String(p.delta);
        floorInput.value = String(p.floor);
        creditInput.value = String(p.credit);
        steerInput.value = String(p.steer);
        updateCoop();
      });
    });

    updateCoop();
  }

  // ------------------------------------------------------------------
  // Panel 2: Open receipts vs. secretive shadow-ledger agent cartels
  // ------------------------------------------------------------------
  function initCartelPanel() {
    var panel = document.getElementById("sim-panel-cartel");
    if (!panel) return;

    var tauInput = document.getElementById("sim-opacity-tau");
    var bountyInput = document.getElementById("sim-whistle-bounty");
    var auditInput = document.getElementById("sim-phys-audit");
    var shareInput = document.getElementById("sim-cartel-share");

    if (!tauInput || !bountyInput || !auditInput || !shareInput) return;

    var tauOut = document.getElementById("sim-opacity-tau-out");
    var bountyOut = document.getElementById("sim-whistle-bounty-out");
    var auditOut = document.getElementById("sim-phys-audit-out");
    var shareOut = document.getElementById("sim-cartel-share-out");

    var collapseZone = document.getElementById("sim-p2-collapse-zone");
    var pathDefect = document.getElementById("sim-p2-path-defect");
    var pathCollude = document.getElementById("sim-p2-path-collude");
    var cursorLine = document.getElementById("sim-p2-cursor-line");
    var threshLine = document.getElementById("sim-p2-thresh-line");
    var threshLabel = document.getElementById("sim-p2-thresh-label");
    var dotDefect = document.getElementById("sim-p2-dot-defect");
    var dotCollude = document.getElementById("sim-p2-dot-collude");

    var kpiStatus = document.getElementById("sim-p2-kpi-status");
    var kpiBstar = document.getElementById("sim-p2-kpi-bstar");
    var kpiAudit = document.getElementById("sim-p2-kpi-audit");
    var kpiReserve = document.getElementById("sim-p2-kpi-reserve");
    var statusText = document.getElementById("sim-p2-status-text");
    var presetBtns = Array.prototype.slice.call(panel.querySelectorAll(".sim-preset-btn"));

    var presets = {
      undefended: { tau: 0, bounty: 0, audit: 0, share: 25 },
      margin_only: { tau: 22, bounty: 0, audit: 20, share: 25 },
      full_defense: { tau: 28, bounty: 6, audit: 30, share: 25 }
    };

    function syncPresetState() {
      var curTau = Number(tauInput.value);
      var curBounty = Number(bountyInput.value);
      var curAudit = Number(auditInput.value);
      var curShare = Number(shareInput.value);

      presetBtns.forEach(function (btn) {
        var key = btn.getAttribute("data-preset") || "";
        var p = presets[key];
        var match = Boolean(
          p &&
          p.tau === curTau &&
          p.bounty === curBounty &&
          p.audit === curAudit &&
          p.share === curShare
        );
        btn.classList.toggle("is-active", match);
        btn.setAttribute("aria-pressed", match ? "true" : "false");
      });
    }

    function updateCartel() {
      var tauPct = clamp(Number(tauInput.value) || 0, 0, 60);
      var bountyVal = clamp(Number(bountyInput.value) || 0, 0, 25);
      var auditPct = clamp(Number(auditInput.value) || 0, 0, 100);
      var cartelPct = clamp(Number(shareInput.value) || 25, 10, 50);

      var tauSel = tauPct / 100.0;
      var auditStrength = auditPct / 100.0;

      var totalAgents = 60;
      var mCartel = Math.max(2, Math.round((totalAgents * cartelPct) / 100.0));

      if (tauOut) tauOut.textContent = tauPct + "%";
      if (bountyOut) bountyOut.textContent = bountyVal + " credits";
      if (auditOut) auditOut.textContent = auditPct + "%";
      if (shareOut) shareOut.textContent = cartelPct + "% (" + mCartel + " agents)";

      tauInput.setAttribute("aria-valuetext", tauPct + " percent border opacity quarantine margin");
      bountyInput.setAttribute("aria-valuetext", bountyVal + " whistleblower safe-harbor credits");
      auditInput.setAttribute("aria-valuetext", auditPct + " percent physical energy audit sensitivity");
      shareInput.setAttribute("aria-valuetext", cartelPct + " percent initial shadow cartel share (" + mCartel + " of 60 agents)");

      // Exact Harrington (2008) + Myerson (1977) + Physical Conservation parameters
      var baseProd = 10.0;
      var clubScale = 0.85;
      var alpha = 0.55;
      var rentScale = 23.0;
      var exposure = 18.0;
      var fine = 18.0;
      var beta = 0.85;
      var yMax = 30.0;

      var shadowMw = mCartel * 2.4;
      var excessMw = Math.max(0.0, shadowMw - 1.5);
      var pPhysMax = excessMw > 0.0 ? Math.min(0.98, excessMw / (excessMw + 18.0)) : 0.0;
      var pPhys = auditStrength * pPhysMax;

      var openAfterDefect = totalAgents - mCartel + 1;
      var piOpen = baseProd * (1.0 + clubScale * Math.pow(openAfterDefect / totalAgents, alpha));
      var denom = 1.0 - beta * (1.0 - pPhys);
      var eDefect = piOpen + bountyVal * denom;

      var grossRent = rentScale * (0.45 + 0.55 * (mCartel / totalAgents));
      var rawTauStar = (baseProd + grossRent - (piOpen + pPhys * fine + bountyVal * denom)) / exposure;
      var clampedTauStar = clamp(rawTauStar, 0.0, 0.60);

      var ptsDef = [];
      var ptsCol = [];
      for (var i = 0; i <= 30; i++) {
        var tauI = (i / 30.0) * 0.60;
        var x = X_LEFT + (tauI / 0.60) * (X_RIGHT - X_LEFT);
        var piC = Math.max(0.0, baseProd + grossRent - tauI * exposure);
        var eCol = Math.max(0.0, piC - pPhys * fine);
        var yD = Y_BOTTOM - (Math.min(yMax, eDefect) / yMax) * (Y_BOTTOM - Y_TOP);
        var yC = Y_BOTTOM - (Math.min(yMax, eCol) / yMax) * (Y_BOTTOM - Y_TOP);
        ptsDef.push(fmt1(x) + "," + fmt1(yD));
        ptsCol.push(fmt1(x) + "," + fmt1(yC));
      }

      var piCSel = Math.max(0.0, baseProd + grossRent - tauSel * exposure);
      var eColSel = Math.max(0.0, piCSel - pPhys * fine);
      var bStar = Math.max(0.0, (piCSel - piOpen - pPhys * fine) / denom);
      var collapsed = eDefect > eColSel;

      var xStar = X_LEFT + (clampedTauStar / 0.60) * (X_RIGHT - X_LEFT);
      var xCur = X_LEFT + (tauSel / 0.60) * (X_RIGHT - X_LEFT);
      var yDefCur = Y_BOTTOM - (Math.min(yMax, eDefect) / yMax) * (Y_BOTTOM - Y_TOP);
      var yColCur = Y_BOTTOM - (Math.min(yMax, eColSel) / yMax) * (Y_BOTTOM - Y_TOP);

      if (pathDefect) pathDefect.setAttribute("d", "M " + ptsDef.join(" L "));
      if (pathCollude) pathCollude.setAttribute("d", "M " + ptsCol.join(" L "));

      if (collapseZone) {
        if (rawTauStar <= 0.60) {
          collapseZone.setAttribute("x", fmt1(xStar));
          collapseZone.setAttribute("width", fmt1(Math.max(0.0, X_RIGHT - xStar)));
          collapseZone.setAttribute("opacity", "1");
        } else {
          collapseZone.setAttribute("x", fmt1(X_RIGHT));
          collapseZone.setAttribute("width", "0");
          collapseZone.setAttribute("opacity", "0");
        }
      }

      if (threshLine && threshLabel) {
        if (rawTauStar > 0.0 && rawTauStar < 0.60) {
          threshLine.setAttribute("x1", fmt1(xStar));
          threshLine.setAttribute("x2", fmt1(xStar));
          threshLine.setAttribute("opacity", "1");
          var lblX = clamp(xStar + 6.0, X_LEFT + 10.0, X_RIGHT - 108.0);
          threshLabel.setAttribute("x", fmt1(lblX));
          threshLabel.textContent = "Collapse at " + fmt1(rawTauStar * 100.0) + "%";
          threshLabel.setAttribute("opacity", "1");
        } else if (rawTauStar <= 0.0) {
          threshLine.setAttribute("x1", fmt1(X_LEFT));
          threshLine.setAttribute("x2", fmt1(X_LEFT));
          threshLine.setAttribute("opacity", "0.55");
          threshLabel.setAttribute("x", fmt1(X_LEFT + 6.0));
          threshLabel.textContent = "Collapses at 0% margin";
          threshLabel.setAttribute("opacity", "1");
        } else {
          threshLine.setAttribute("opacity", "0");
          threshLabel.setAttribute("x", fmt1(X_RIGHT - 135.0));
          threshLabel.textContent = "Threshold > 60% margin";
          threshLabel.setAttribute("opacity", "1");
        }
      }

      if (cursorLine) {
        cursorLine.setAttribute("x1", fmt1(xCur));
        cursorLine.setAttribute("x2", fmt1(xCur));
      }
      if (dotDefect) {
        dotDefect.setAttribute("cx", fmt1(xCur));
        dotDefect.setAttribute("cy", fmt1(yDefCur));
      }
      if (dotCollude) {
        dotCollude.setAttribute("cx", fmt1(xCur));
        dotCollude.setAttribute("cy", fmt1(yColCur));
      }

      // Exact collateral & safe-harbor conservation accounting
      var slashedPool = (mCartel - 1) * fine;
      var paidBounty = collapsed ? Math.min(slashedPool, bountyVal) : 0.0;
      var netCommonsGain = collapsed ? (slashedPool - paidBounty) : (mCartel * tauSel * exposure);

      if (kpiStatus) {
        kpiStatus.textContent = collapsed ? "100% defection" : "Cartel persists";
      }
      if (kpiBstar) {
        kpiBstar.textContent = fmt1(bStar) + " credits";
      }
      if (kpiAudit) {
        kpiAudit.textContent = Math.round(pPhys * 100.0) + "% / round";
      }
      if (kpiReserve) {
        kpiReserve.textContent = "+" + fmt1(netCommonsGain) + " conserved";
      }

      if (statusText) {
        if (collapsed) {
          statusText.textContent =
            "Cartel collapses into 100% defection: open cooperative membership plus safe-harbor leniency (" +
            fmt1(eDefect) + " value) beats secretive cartel play (" + fmt1(eColSel) +
            " value). Co-conspirator fines fund the " + fmt1(paidBounty) +
            "-credit whistleblower award and add " + fmt1(netCommonsGain) + " credits to the open reserve.";
        } else {
          statusText.textContent =
            "Shadow cartel persists: secretive price-fixing (" + fmt1(eColSel) +
            " value) currently exceeds defecting to the open network (" + fmt1(eDefect) +
            " value). Raise whistleblower safe-harbor above " + fmt1(bStar) +
            " credits, increase the border opacity margin, or tighten physical energy audits to trigger collapse.";
        }
      }

      syncPresetState();
    }

    [tauInput, bountyInput, auditInput, shareInput].forEach(function (inp) {
      inp.addEventListener("input", updateCartel);
      inp.addEventListener("change", updateCartel);
    });

    presetBtns.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var key = btn.getAttribute("data-preset") || "";
        var p = presets[key];
        if (!p) return;
        tauInput.value = String(p.tau);
        bountyInput.value = String(p.bounty);
        auditInput.value = String(p.audit);
        shareInput.value = String(p.share);
        updateCartel();
      });
    });

    updateCartel();
  }

  function boot() {
    initCoopPanel();
    initCartelPanel();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
