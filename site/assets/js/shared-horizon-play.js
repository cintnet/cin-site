/* Collective Intelligence Network — Shared Horizon 5-Phase Process & Case Explorer
 * Progressive enhancement for /labs/shared-horizon/.
 * Strict DOM attribute/textContent updates only; zero innerHTML, eval, or network calls.
 */
(function () {
  "use strict";

  function initPhaseSlideshow() {
    var section = document.getElementById("sh-process-section");
    if (!section) return;

    var stations = Array.prototype.slice.call(
      section.querySelectorAll("[data-phase-target]")
    );
    var stepBtns = Array.prototype.slice.call(
      section.querySelectorAll("[data-phase-btn]")
    );
    var panels = Array.prototype.slice.call(
      section.querySelectorAll("[data-phase-panel]")
    );
    var prevBtn = document.getElementById("sh-phase-prev");
    var nextBtn = document.getElementById("sh-phase-next");
    var counter = document.getElementById("sh-phase-counter");

    if (!panels.length) return;
    var total = panels.length;
    var activePhase = 1;

    function setPhase(nextNum) {
      var n = parseInt(String(nextNum), 10);
      if (isNaN(n) || n < 1) n = 1;
      if (n > total) n = total;
      activePhase = n;
      var key = String(activePhase);

      stations.forEach(function (st) {
        var match = st.getAttribute("data-phase-target") === key;
        st.classList.toggle("is-active", match);
        st.setAttribute("aria-pressed", match ? "true" : "false");
      });

      stepBtns.forEach(function (btn) {
        var match = btn.getAttribute("data-phase-btn") === key;
        btn.classList.toggle("is-active", match);
        btn.setAttribute("aria-selected", match ? "true" : "false");
      });

      panels.forEach(function (panel) {
        var match = panel.getAttribute("data-phase-panel") === key;
        if (match) {
          panel.removeAttribute("hidden");
        } else {
          panel.setAttribute("hidden", "");
        }
      });

      if (counter) {
        counter.textContent = "Step " + key + " of " + String(total);
      }
      if (prevBtn) {
        prevBtn.disabled = activePhase <= 1;
      }
      if (nextBtn) {
        nextBtn.disabled = activePhase >= total;
      }
    }

    stations.forEach(function (st) {
      st.addEventListener("click", function () {
        setPhase(st.getAttribute("data-phase-target"));
      });
      st.addEventListener("keydown", function (ev) {
        if (ev.key === "Enter" || ev.key === " ") {
          ev.preventDefault();
          setPhase(st.getAttribute("data-phase-target"));
        }
      });
    });

    stepBtns.forEach(function (btn) {
      btn.addEventListener("click", function () {
        setPhase(btn.getAttribute("data-phase-btn"));
      });
      btn.addEventListener("keydown", function (ev) {
        if (ev.key === "ArrowRight") {
          ev.preventDefault();
          var nextIdx = Math.min(total, activePhase + 1);
          setPhase(nextIdx);
          if (stepBtns[nextIdx - 1]) stepBtns[nextIdx - 1].focus();
        } else if (ev.key === "ArrowLeft") {
          ev.preventDefault();
          var prevIdx = Math.max(1, activePhase - 1);
          setPhase(prevIdx);
          if (stepBtns[prevIdx - 1]) stepBtns[prevIdx - 1].focus();
        }
      });
    });

    if (prevBtn) {
      prevBtn.addEventListener("click", function () {
        if (activePhase > 1) setPhase(activePhase - 1);
      });
    }
    if (nextBtn) {
      nextBtn.addEventListener("click", function () {
        if (activePhase < total) setPhase(activePhase + 1);
      });
    }

    setPhase(1);
  }

  function initCaseStudies() {
    var section = document.getElementById("sh-cases-section");
    if (!section) return;

    var tabs = Array.prototype.slice.call(
      section.querySelectorAll("[data-case-btn]")
    );
    var panels = Array.prototype.slice.call(
      section.querySelectorAll("[data-case-panel]")
    );
    if (!tabs.length || !panels.length) return;

    var activeCase = 1;
    var total = panels.length;

    function setCase(nextNum) {
      var n = parseInt(String(nextNum), 10);
      if (isNaN(n) || n < 1) n = 1;
      if (n > total) n = total;
      activeCase = n;
      var key = String(activeCase);

      tabs.forEach(function (tab) {
        var match = tab.getAttribute("data-case-btn") === key;
        tab.classList.toggle("is-active", match);
        tab.setAttribute("aria-selected", match ? "true" : "false");
      });

      panels.forEach(function (panel) {
        var match = panel.getAttribute("data-case-panel") === key;
        if (match) {
          panel.removeAttribute("hidden");
        } else {
          panel.setAttribute("hidden", "");
        }
      });
    }

    tabs.forEach(function (tab) {
      tab.addEventListener("click", function () {
        setCase(tab.getAttribute("data-case-btn"));
      });
      tab.addEventListener("keydown", function (ev) {
        if (ev.key === "ArrowRight") {
          ev.preventDefault();
          var nextIdx = Math.min(total, activeCase + 1);
          setCase(nextIdx);
          if (tabs[nextIdx - 1]) tabs[nextIdx - 1].focus();
        } else if (ev.key === "ArrowLeft") {
          ev.preventDefault();
          var prevIdx = Math.max(1, activeCase - 1);
          setCase(prevIdx);
          if (tabs[prevIdx - 1]) tabs[prevIdx - 1].focus();
        }
      });
    });

    setCase(1);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      initPhaseSlideshow();
      initCaseStudies();
    });
  } else {
    initPhaseSlideshow();
    initCaseStudies();
  }
})();
