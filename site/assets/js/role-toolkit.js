/* Collective Intelligence Network — Role-Tailored Safeguard Toolkit
 * Progressive enhancement for /get-involved/* self-check and verification checklists.
 * Zero network calls, zero tracking, strict DOM element construction only.
 */
(function () {
  "use strict";

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) {
      node.className = className;
    }
    if (text !== undefined && text !== null) {
      node.textContent = String(text);
    }
    return node;
  }

  function clearNode(node) {
    while (node.firstChild) {
      node.removeChild(node.firstChild);
    }
  }

  function toAbsoluteUrl(href) {
    if (!href) {
      return "https://cintnet.org/";
    }
    if (href.indexOf("http://") === 0 || href.indexOf("https://") === 0) {
      return href;
    }
    return "https://cintnet.org" + (href.charAt(0) === "/" ? href : "/" + href);
  }

  function fallbackCopy(text, onDone) {
    try {
      var area = document.createElement("textarea");
      area.value = text;
      area.setAttribute("readonly", "readonly");
      area.style.position = "fixed";
      area.style.top = "-9999px";
      area.style.left = "-9999px";
      document.body.appendChild(area);
      area.select();
      var ok = document.execCommand("copy");
      document.body.removeChild(area);
      onDone(Boolean(ok));
    } catch (_err) {
      onDone(false);
    }
  }

  function copyPlainText(text, onDone) {
    if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
      navigator.clipboard.writeText(text).then(
        function () {
          onDone(true);
        },
        function () {
          fallbackCopy(text, onDone);
        }
      );
      return;
    }
    fallbackCopy(text, onDone);
  }

  function initRoleToolkit() {
    var root = document.getElementById("role-toolkit");
    var dataNode = document.getElementById("role-toolkit-data");
    if (!root || !dataNode) {
      return;
    }

    var config;
    try {
      config = JSON.parse(dataNode.textContent || "{}");
    } catch (_err) {
      return;
    }

    if (!config || !Array.isArray(config.checks) || config.checks.length === 0) {
      return;
    }

    var checks = config.checks;
    var total = checks.length;
    var state = checks.map(function () {
      return false;
    });
    var copyTimer = null;

    clearNode(root);
    root.classList.add("rt-ready");

    /* 1. Readiness header + progress bar */
    var header = el("div", "rt-header");
    var statusRow = el("div", "rt-status-row");
    var roleBadge = el("span", "rt-role-badge", config.role || "Role self-check");
    var scoreText = el("p", "rt-score", "0 of " + total + " safeguards in place");
    scoreText.setAttribute("role", "status");
    scoreText.setAttribute("aria-live", "polite");
    scoreText.setAttribute("aria-atomic", "true");
    statusRow.appendChild(roleBadge);
    statusRow.appendChild(scoreText);

    var barTrack = el("div", "rt-bar-track");
    barTrack.setAttribute("role", "progressbar");
    barTrack.setAttribute("aria-label", (config.title || "Safeguard readiness") + " progress");
    barTrack.setAttribute("aria-valuemin", "0");
    barTrack.setAttribute("aria-valuemax", String(total));
    barTrack.setAttribute("aria-valuenow", "0");
    var barFill = el("div", "rt-bar-fill");
    barFill.style.width = "0%";
    barTrack.appendChild(barFill);

    header.appendChild(statusRow);
    header.appendChild(barTrack);
    root.appendChild(header);

    /* 2. Action toolbar */
    var toolbar = el("div", "rt-toolbar");
    toolbar.setAttribute("role", "group");
    toolbar.setAttribute("aria-label", "Safeguard checklist controls");

    var btnCheckAll = el("button", "rt-btn", "Check all");
    btnCheckAll.type = "button";

    var btnReset = el("button", "rt-btn", "Reset");
    btnReset.type = "button";

    var btnCopy = el("button", "rt-btn", "Copy plain-text checklist");
    btnCopy.type = "button";

    var btnPrint = el("button", "rt-btn rt-btn-primary", "Print checklist");
    btnPrint.type = "button";

    var copyStatus = el("span", "rt-copy-status", "");
    copyStatus.setAttribute("role", "status");
    copyStatus.setAttribute("aria-live", "polite");
    copyStatus.setAttribute("aria-atomic", "true");

    toolbar.appendChild(btnCheckAll);
    toolbar.appendChild(btnReset);
    toolbar.appendChild(btnCopy);
    toolbar.appendChild(btnPrint);
    toolbar.appendChild(copyStatus);
    root.appendChild(toolbar);

    /* 3. Interactive checklist fieldset */
    var fieldset = el("fieldset", "rt-fieldset");
    var legend = el(
      "legend",
      "rt-legend",
      config.legend || "Mark each safeguard already active in your setting:"
    );
    fieldset.appendChild(legend);

    var list = el("ul", "rt-list");
    var checkboxNodes = [];
    var itemNodes = [];

    checks.forEach(function (item, idx) {
      var li = el("li", "rt-item");
      var row = el("div", "rt-check-row");

      var chkId = "rt-check-" + (item.id || String(idx + 1));
      var input = document.createElement("input");
      input.type = "checkbox";
      input.className = "rt-checkbox";
      input.id = chkId;
      input.checked = false;

      var body = el("div", "rt-item-body");
      var label = document.createElement("label");
      label.className = "rt-item-label";
      label.setAttribute("for", chkId);

      var numSpan = el("span", "rt-num", String(idx + 1) + ". ");
      var titleSpan = el("span", "rt-label-text", item.label || "");
      label.appendChild(numSpan);
      label.appendChild(titleSpan);
      body.appendChild(label);

      if (item.detail) {
        var detailP = el("p", "rt-item-detail", item.detail);
        body.appendChild(detailP);
      }

      if (item.linkHref && item.linkLabel) {
        var linkWrap = el("p", "rt-item-link-wrap");
        var itemLink = el("a", "rt-item-link", item.linkLabel);
        itemLink.setAttribute("href", item.linkHref);
        linkWrap.appendChild(itemLink);
        body.appendChild(linkWrap);
      }

      input.addEventListener("change", function () {
        state[idx] = Boolean(input.checked);
        renderState();
      });

      row.appendChild(input);
      row.appendChild(body);
      li.appendChild(row);
      list.appendChild(li);

      checkboxNodes.push(input);
      itemNodes.push(li);
    });

    fieldset.appendChild(list);
    root.appendChild(fieldset);

    /* 4. Dynamic "Highest-priority next move" callout */
    var nextBox = el("div", "rt-next");
    nextBox.setAttribute("aria-live", "polite");
    nextBox.setAttribute("aria-atomic", "true");
    root.appendChild(nextBox);

    /* 5. Direct lab & reference links strip */
    if (Array.isArray(config.links) && config.links.length > 0) {
      var footer = el("div", "rt-footer");
      var footerLabel = el("span", "rt-footer-label", "Related CIN Labs and references:");
      var footerList = el("ul", "rt-footer-links");

      config.links.forEach(function (lnk) {
        if (!lnk || !lnk.href || !lnk.label) {
          return;
        }
        var fli = el("li", "");
        var fa = el("a", "rt-footer-link", lnk.label);
        fa.setAttribute("href", lnk.href);
        fli.appendChild(fa);
        footerList.appendChild(fli);
      });

      footer.appendChild(footerLabel);
      footer.appendChild(footerList);
      root.appendChild(footer);
    }

    function getCheckedCount() {
      var count = 0;
      for (var i = 0; i < state.length; i += 1) {
        if (state[i]) {
          count += 1;
        }
      }
      return count;
    }

    function getFirstUnchecked() {
      for (var i = 0; i < checks.length; i += 1) {
        if (!state[i]) {
          return { index: i, item: checks[i] };
        }
      }
      return null;
    }

    function renderState() {
      var checkedCount = getCheckedCount();
      var pct = total > 0 ? Math.round((checkedCount / total) * 100) : 0;

      scoreText.textContent = checkedCount + " of " + total + " safeguards in place";
      barTrack.setAttribute("aria-valuenow", String(checkedCount));
      barFill.style.width = pct + "%";

      for (var i = 0; i < itemNodes.length; i += 1) {
        checkboxNodes[i].checked = Boolean(state[i]);
        if (state[i]) {
          itemNodes[i].classList.add("is-checked");
        } else {
          itemNodes[i].classList.remove("is-checked");
        }
      }

      clearNode(nextBox);
      var firstMissing = getFirstUnchecked();
      if (firstMissing) {
        nextBox.classList.remove("is-complete");
        var kicker = el(
          "p",
          "rt-next-kicker",
          "Highest-priority next move · Safeguard " + (firstMissing.index + 1) + " of " + total
        );
        var title = el("h3", "rt-next-title", firstMissing.item.label || "");
        var actionText = el(
          "p",
          "rt-next-body",
          firstMissing.item.nextAction || firstMissing.item.detail || ""
        );
        nextBox.appendChild(kicker);
        nextBox.appendChild(title);
        nextBox.appendChild(actionText);

        if (firstMissing.item.linkHref && firstMissing.item.linkLabel) {
          var cta = el("a", "rt-next-cta", firstMissing.item.linkLabel);
          cta.setAttribute("href", firstMissing.item.linkHref);
          nextBox.appendChild(cta);
        }
      } else {
        nextBox.classList.add("is-complete");
        var doneKicker = el("p", "rt-next-kicker", "All " + total + " safeguards checked");
        var doneTitle = el(
          "h3",
          "rt-next-title",
          config.allCompleteHeading || "Baseline safeguards in place"
        );
        var doneBody = el(
          "p",
          "rt-next-body",
          config.allCompleteBody ||
            "All six baseline checks are marked active. Stress-test your assumptions in a live CIN Lab or share this verification checklist with your coalition partners."
        );
        nextBox.appendChild(doneKicker);
        nextBox.appendChild(doneTitle);
        nextBox.appendChild(doneBody);

        if (Array.isArray(config.links) && config.links.length > 0) {
          var doneCta = el("a", "rt-next-cta", config.links[0].label);
          doneCta.setAttribute("href", config.links[0].href);
          nextBox.appendChild(doneCta);
        }
      }
    }

    function formatPlainTextChecklist() {
      var checkedCount = getCheckedCount();
      var lines = [];
      lines.push("CIN SAFEGUARD CHECKLIST: " + (config.title || "Role safeguard self-check"));
      if (config.role) {
        lines.push("Role: " + config.role);
      }
      lines.push("Readiness: " + checkedCount + " of " + total + " safeguards in place");
      lines.push("");
      lines.push("Checklist:");
      for (var i = 0; i < checks.length; i += 1) {
        var c = checks[i];
        var mark = state[i] ? "[x]" : "[ ]";
        var line = mark + " " + (i + 1) + ". " + (c.label || "");
        if (c.detail) {
          line += " - " + c.detail;
        }
        if (c.linkHref) {
          line += " (" + toAbsoluteUrl(c.linkHref) + ")";
        }
        lines.push(line);
      }
      lines.push("");
      var firstMissing = getFirstUnchecked();
      if (firstMissing) {
        lines.push("Highest-priority next move:");
        lines.push(
          (firstMissing.index + 1) +
            ". " +
            (firstMissing.item.label || "") +
            ": " +
            (firstMissing.item.nextAction || firstMissing.item.detail || "")
        );
        if (firstMissing.item.linkHref) {
          lines.push("Open in CIN: " + toAbsoluteUrl(firstMissing.item.linkHref));
        }
      } else {
        lines.push(
          "Status: All " +
            total +
            " baseline safeguards marked in place. Stress-test edge cases in CIN Labs."
        );
      }
      if (config.pageUrl) {
        lines.push("");
        lines.push("Checklist URL: " + toAbsoluteUrl(config.pageUrl));
      }
      return lines.join("\n");
    }

    function announceStatus(msg) {
      copyStatus.textContent = msg;
      if (copyTimer) {
        window.clearTimeout(copyTimer);
      }
      copyTimer = window.setTimeout(function () {
        copyStatus.textContent = "";
      }, 4500);
    }

    btnCheckAll.addEventListener("click", function () {
      for (var i = 0; i < state.length; i += 1) {
        state[i] = true;
      }
      renderState();
      announceStatus("Marked all " + total + " safeguards as active.");
    });

    btnReset.addEventListener("click", function () {
      for (var i = 0; i < state.length; i += 1) {
        state[i] = false;
      }
      renderState();
      announceStatus("Checklist reset to 0 of " + total + " safeguards.");
    });

    btnCopy.addEventListener("click", function () {
      var text = formatPlainTextChecklist();
      copyPlainText(text, function (ok) {
        if (ok) {
          announceStatus("Plain-text checklist copied to clipboard.");
        } else {
          announceStatus("Clipboard unavailable; use Print checklist instead.");
        }
      });
    });

    function cleanupPrintMode() {
      document.body.classList.remove("printing-role-brief");
    }

    window.addEventListener("afterprint", cleanupPrintMode);

    btnPrint.addEventListener("click", function () {
      document.body.classList.add("printing-role-brief");
      window.print();
      window.setTimeout(cleanupPrintMode, 1500);
    });

    renderState();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initRoleToolkit);
  } else {
    initRoleToolkit();
  }
})();
