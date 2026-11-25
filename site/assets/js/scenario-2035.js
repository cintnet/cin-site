(function () {
  "use strict";

  var root = document.getElementById("sc-branch-root");
  if (!root) return;

  var buttons = Array.prototype.slice.call(root.querySelectorAll("[data-branch-btn]"));
  var panels = Array.prototype.slice.call(root.querySelectorAll("[data-branch-panel]"));
  var jumpButtons = Array.prototype.slice.call(root.querySelectorAll("[data-switch-to]"));

  function setBranch(branchId, shouldScroll) {
    buttons.forEach(function (btn) {
      var active = btn.getAttribute("data-branch-btn") === branchId;
      btn.classList.toggle("is-active", active);
      btn.setAttribute("aria-selected", active ? "true" : "false");
    });

    panels.forEach(function (panel) {
      var id = panel.getAttribute("data-branch-panel");
      var visible = branchId === "compare" || id === branchId;
      panel.hidden = !visible;
    });

    root.setAttribute("data-active-branch", branchId);

    if (shouldScroll) {
      var hinge = document.getElementById("the-hinge");
      if (hinge && typeof hinge.scrollIntoView === "function") {
        hinge.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }
  }

  buttons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      setBranch(btn.getAttribute("data-branch-btn"), false);
    });
  });

  jumpButtons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      setBranch(btn.getAttribute("data-switch-to"), true);
    });
  });

  var initial = "cin";
  if (window.location.hash === "#timeline-unfused") initial = "unfused";
  else if (window.location.hash === "#timeline-compare") initial = "compare";
  setBranch(initial, false);
})();
