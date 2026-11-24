// cintnet.org — progressive enhancement only. The site works fully without this file.
(function () {
  "use strict";
  var root = document.documentElement;

  var header = document.querySelector(".site-header");
  if (header) {
    var onScroll = function () { header.classList.toggle("scrolled", window.scrollY > 8); };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  // Reveal animations: mark elements already in the initial viewport as .is-visible
  // BEFORE adding .js on <html> so above-the-fold content never flashes invisible or delays LCP.
  var items = Array.prototype.slice.call(document.querySelectorAll(".reveal"));
  var mql = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : null;
  var reduce = mql && mql.matches;
  var viewH = window.innerHeight || root.clientHeight || 800;
  var belowFold = [];
  items.forEach(function (el) {
    if (reduce || !("IntersectionObserver" in window)) {
      el.classList.add("is-visible");
      return;
    }
    var r = el.getBoundingClientRect();
    if (r.top < viewH * 0.96 && r.bottom >= 0) {
      el.classList.add("is-visible");
    } else {
      belowFold.push(el);
    }
  });
  root.classList.add("js");

  if (!reduce && "IntersectionObserver" in window && belowFold.length) {
    // Stagger siblings in a grid by 80ms each.
    belowFold.forEach(function (el) {
      var parent = el.parentElement;
      if (!parent) return;
      var siblings = Array.prototype.filter.call(parent.children, function (c) { return c.classList.contains("reveal"); });
      var i = siblings.indexOf(el);
      if (i > 0) el.style.transitionDelay = Math.min(i, 5) * 80 + "ms";
    });
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) {
          var el = e.target;
          el.classList.add("is-visible");
          if (el.style.transitionDelay) {
            el.addEventListener("transitionend", function clearDelay() {
              el.style.transitionDelay = "";
              el.removeEventListener("transitionend", clearDelay);
            });
          }
          io.unobserve(el);
        }
      });
    }, { threshold: 0.01, rootMargin: "40px 0px 0px 0px" });
    belowFold.forEach(function (el) { io.observe(el); });

    if (mql && mql.addEventListener) {
      mql.addEventListener("change", function (ev) {
        if (ev.matches) {
          io.disconnect();
          belowFold.forEach(function (el) {
            el.style.transitionDelay = "";
            el.classList.add("is-visible");
          });
        }
      });
    }
  }

  // Skip link: transfer programmatic focus to #main on activation.
  var skip = document.querySelector(".skip");
  var main = document.getElementById("main");
  if (skip && main) {
    skip.addEventListener("click", function () {
      if (!main.hasAttribute("tabindex")) main.setAttribute("tabindex", "-1");
      main.focus({ preventScroll: true });
    });
  }

  // Mobile menu: close on link click, outside click, focus loss, Escape key, or desktop resize;
  // support Up/Down/Home/End arrow keys inside the open menu.
  var mobile = document.querySelector(".mobile-nav");
  if (mobile) {
    var summary = mobile.querySelector("summary");
    var menuLinks = Array.prototype.slice.call(mobile.querySelectorAll("nav a"));
    var closeMenu = function (restoreFocus) {
      if (!mobile.hasAttribute("open")) return;
      mobile.removeAttribute("open");
      if (restoreFocus && summary) summary.focus();
    };
    mobile.addEventListener("click", function (e) {
      if (e.target && e.target.closest && e.target.closest("a")) closeMenu(false);
    });
    document.addEventListener("click", function (e) {
      if (mobile.hasAttribute("open") && e.target && !mobile.contains(e.target)) {
        closeMenu(false);
      }
    });
    mobile.addEventListener("focusout", function (e) {
      if (mobile.hasAttribute("open") && e.relatedTarget && !mobile.contains(e.relatedTarget)) {
        closeMenu(false);
      }
    });
    document.addEventListener("keydown", function (e) {
      if (!mobile.hasAttribute("open")) return;
      if (e.key === "Escape" || e.key === "Esc") {
        e.preventDefault();
        closeMenu(true);
        return;
      }
      if (!menuLinks.length || !mobile.contains(document.activeElement)) return;
      var idx = menuLinks.indexOf(document.activeElement);
      if (e.key === "ArrowDown") {
        e.preventDefault();
        menuLinks[idx < 0 ? 0 : (idx + 1) % menuLinks.length].focus();
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        menuLinks[idx <= 0 ? menuLinks.length - 1 : idx - 1].focus();
      } else if (e.key === "Home") {
        e.preventDefault();
        menuLinks[0].focus();
      } else if (e.key === "End") {
        e.preventDefault();
        menuLinks[menuLinks.length - 1].focus();
      }
    });
    if (window.matchMedia) {
      var mqDesktop = window.matchMedia("(min-width: 981px)");
      if (mqDesktop.addEventListener) {
        mqDesktop.addEventListener("change", function (ev) {
          if (ev.matches) closeMenu(false);
        });
      }
    }
  }

  // Collapsible disclosures (.for-researchers, .footnotes-drawer, .faq-drawer):
  // 1) Escape collapses open <details> and returns focus to <summary>;
  // 2) beforeprint / afterprint expands all <details> for clean printing;
  // 3) Clicking any in-page anchor <a href="#..."> (such as <sup><a href="#fn-3">3</a></sup>)
  //    or loading a URL hash inside a closed <details> opens all closed <details> ancestors first
  //    and smoothly scrolls to the target element.
  var collapsibleDetails = Array.prototype.filter.call(
    document.querySelectorAll(
      ".for-researchers details, details.for-researchers, details.footnotes-drawer, .footnotes-drawer, details.faq-drawer, .faq-drawer details"
    ),
    function (el) { return el && el.tagName && el.tagName.toUpperCase() === "DETAILS"; }
  );
  if (collapsibleDetails.length) {
    collapsibleDetails.forEach(function (det) {
      det.addEventListener("keydown", function (e) {
        if ((e.key === "Escape" || e.key === "Esc") && det.hasAttribute("open")) {
          e.preventDefault();
          det.removeAttribute("open");
          var sum = det.querySelector("summary");
          if (sum) sum.focus();
        }
      });
    });
    window.addEventListener("beforeprint", function () {
      collapsibleDetails.forEach(function (d) {
        if (!d.hasAttribute("open")) {
          d.setAttribute("open", "");
          d.setAttribute("data-print-opened", "1");
        }
      });
    });
    window.addEventListener("afterprint", function () {
      collapsibleDetails.forEach(function (d) {
        if (d.getAttribute("data-print-opened") === "1") {
          d.removeAttribute("open");
          d.removeAttribute("data-print-opened");
        }
      });
    });
  }

  var openClosedDetailsAncestors = function (el) {
    var openedAny = false;
    var cur = el;
    while (cur && cur !== document.body && cur !== root) {
      if (cur.tagName && cur.tagName.toUpperCase() === "DETAILS" && !cur.hasAttribute("open")) {
        cur.setAttribute("open", "");
        openedAny = true;
      }
      cur = cur.parentElement;
    }
    return openedAny;
  };

  var highlightTarget = function (el) {
    var prev = Array.prototype.slice.call(document.querySelectorAll(".is-targeted"));
    prev.forEach(function (p) { p.classList.remove("is-targeted"); });
    if (el && el.classList) {
      el.classList.add("is-targeted");
    }
  };

  var decodeFragmentId = function (rawHash) {
    if (!rawHash || rawHash.length <= 1 || rawHash.charAt(0) !== "#") return "";
    var rawId = rawHash.slice(1);
    try {
      return decodeURIComponent(rawId);
    } catch (err) {
      return rawId;
    }
  };

  document.addEventListener("click", function (e) {
    if (e.defaultPrevented || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    if (typeof e.button === "number" && e.button !== 0) return;
    var link = e.target && e.target.closest ? e.target.closest('a[href^="#"]') : null;
    if (!link) return;
    var href = link.getAttribute("href");
    if (!href || href === "#") return;
    var id = decodeFragmentId(href);
    if (!id) return;
    var target = document.getElementById(id);
    if (!target) return;
    var hadClosedDetails = openClosedDetailsAncestors(target);
    if (hadClosedDetails) {
      e.preventDefault();
      highlightTarget(target);
      if (window.history && window.history.pushState) {
        window.history.pushState(null, "", href);
      }
      var reduceNow = mql && mql.matches;
      if (target.scrollIntoView) {
        target.scrollIntoView({ behavior: reduceNow ? "auto" : "smooth", block: "center" });
      }
    } else {
      highlightTarget(target);
    }
  });

  var revealInitialOrChangedHash = function (smooth) {
    if (!window.location.hash || window.location.hash.length <= 1) return;
    var id = decodeFragmentId(window.location.hash);
    if (!id) return;
    var target = document.getElementById(id);
    if (!target) return;
    var hadClosed = openClosedDetailsAncestors(target);
    highlightTarget(target);
    if (hadClosed && target.scrollIntoView) {
      var reduceNow = mql && mql.matches;
      target.scrollIntoView({ behavior: smooth && !reduceNow ? "smooth" : "auto", block: "center" });
    }
  };
  revealInitialOrChangedHash(false);
  window.addEventListener("hashchange", function () {
    revealInitialOrChangedHash(true);
  });

  // Automatic "In this essay" Table of Contents for articles with >= 4 direct-child h2 headings.
  var articleProse = document.querySelector("article.article .prose");
  if (articleProse) {
    var headings = Array.prototype.filter.call(
      articleProse.querySelectorAll("h2"),
      function (h2) { return h2.parentNode === articleProse; }
    );
    if (headings.length >= 4) {
      var usedIds = {};
      var nav = document.createElement("nav");
      nav.className = "article-toc";
      nav.setAttribute("aria-label", "In this essay");

      var label = document.createElement("p");
      label.className = "toc-label";
      label.textContent = "In this essay";
      nav.appendChild(label);

      var list = document.createElement("ol");
      list.className = "toc-list";

      headings.forEach(function (h2, idx) {
        var text = (h2.textContent || "").trim();
        if (!h2.id) {
          var slug = text
            .toLowerCase()
            .replace(/[\u2018\u2019']/g, "")
            .replace(/[^a-z0-9]+/g, "-")
            .replace(/^-+|-+$/g, "");
          var baseId = "sec-" + (slug || String(idx + 1));
          var candidate = baseId;
          var count = 2;
          while (usedIds[candidate] || document.getElementById(candidate)) {
            candidate = baseId + "-" + count;
            count += 1;
          }
          h2.id = candidate;
        }
        usedIds[h2.id] = true;

        var li = document.createElement("li");
        var link = document.createElement("a");
        link.setAttribute("href", "#" + h2.id);
        link.textContent = text;
        li.appendChild(link);
        list.appendChild(li);
      });

      nav.appendChild(list);
      var firstHeading = headings[0];
      if (firstHeading && firstHeading.parentNode === articleProse) {
        articleProse.insertBefore(nav, firstHeading);
      } else {
        articleProse.insertBefore(nav, articleProse.firstChild);
      }
    }
  }

  // Blog index category filter (progressive enhancement, strict createElement / textContent).
  var grids = Array.prototype.slice.call(document.querySelectorAll(".post-grid"));
  var blogGrid = null;
  for (var g = 0; g < grids.length; g++) {
    var candidate = grids[g];
    if (candidate.closest && candidate.closest(".recent")) continue;
    var candidateCards = candidate.querySelectorAll(".post-card");
    if (candidateCards.length > 3 || (window.location.pathname.indexOf("/blog") === 0 && candidateCards.length > 0)) {
      blogGrid = candidate;
      break;
    }
  }

  if (blogGrid) {
    var cards = Array.prototype.slice.call(blogGrid.querySelectorAll(".post-card"));
    var categories = [];
    var counts = {};

    cards.forEach(function (card) {
      var cat = card.getAttribute("data-category");
      if (!cat) {
        var metaEl = card.querySelector(".card-body .meta") || card.querySelector(".meta");
        if (metaEl && metaEl.textContent) {
          var parts = metaEl.textContent.split("\u00b7");
          cat = parts[0] ? parts[0].trim() : "";
        }
      } else {
        cat = cat.trim();
      }
      if (cat) {
        card.setAttribute("data-category", cat);
        if (categories.indexOf(cat) === -1) {
          categories.push(cat);
        }
        counts[cat] = (counts[cat] || 0) + 1;
      }
    });

    if (categories.length >= 2) {
      var slugifyCat = function (str) {
        return String(str || "").toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
      };

      var matchCategory = function (raw) {
        if (!raw) return "all";
        var cleaned = String(raw);
        try {
          cleaned = decodeURIComponent(cleaned);
        } catch (err) {
          cleaned = String(raw);
        }
        cleaned = cleaned.trim();
        if (!cleaned || cleaned.toLowerCase() === "all") return "all";
        var targetLower = cleaned.toLowerCase();
        var targetSlug = slugifyCat(cleaned);
        for (var i = 0; i < categories.length; i++) {
          if (categories[i].toLowerCase() === targetLower || slugifyCat(categories[i]) === targetSlug) {
            return categories[i];
          }
        }
        return "all";
      };

      var getCategoryFromUrl = function () {
        try {
          if (window.location.search && "URLSearchParams" in window) {
            var params = new URLSearchParams(window.location.search);
            var fromQuery = params.get("category") || params.get("cat") || params.get("filter");
            if (fromQuery) return matchCategory(fromQuery);
          }
          if (window.location.hash && window.location.hash.length > 1) {
            var hashVal = window.location.hash.slice(1);
            if (hashVal.indexOf("category=") === 0) return matchCategory(hashVal.slice(9));
            if (hashVal.indexOf("cat=") === 0) return matchCategory(hashVal.slice(4));
            var matchedHash = matchCategory(hashVal);
            if (matchedHash !== "all") return matchedHash;
          }
        } catch (err) {
          return "all";
        }
        return "all";
      };

      var getQueryFromUrl = function () {
        try {
          if (window.location.search && "URLSearchParams" in window) {
            var params = new URLSearchParams(window.location.search);
            return (params.get("q") || params.get("search") || "").trim();
          }
        } catch (err) {
          return "";
        }
        return "";
      };

      var cardSearchIndex = cards.map(function (card) {
        return (card.textContent || "").toLowerCase();
      });

      var toolbar = document.createElement("div");
      toolbar.setAttribute("class", "blog-filter");
      toolbar.setAttribute("role", "toolbar");
      toolbar.setAttribute("aria-label", "Filter articles by category or keyword");

      var searchWrap = document.createElement("div");
      searchWrap.setAttribute("class", "blog-search-wrap");

      var searchInput = document.createElement("input");
      searchInput.setAttribute("type", "search");
      searchInput.setAttribute("class", "blog-search-input");
      searchInput.setAttribute("placeholder", "Filter " + cards.length + " articles by keyword or topic...");
      searchInput.setAttribute("aria-label", "Filter " + cards.length + " articles by keyword or topic");
      searchInput.setAttribute("autocomplete", "off");
      searchWrap.appendChild(searchInput);
      toolbar.appendChild(searchWrap);

      var pills = [];
      var createPill = function (labelText, filterValue, count, isPressed) {
        var btn = document.createElement("button");
        btn.setAttribute("type", "button");
        btn.setAttribute("class", isPressed ? "filter-pill is-active" : "filter-pill");
        btn.setAttribute("data-filter", filterValue);
        btn.setAttribute("aria-pressed", isPressed ? "true" : "false");
        btn.textContent = labelText + " ";

        var badge = document.createElement("span");
        badge.setAttribute("class", "filter-count");
        badge.textContent = String(count);
        btn.appendChild(badge);

        return btn;
      };

      var allBtn = createPill("All", "all", cards.length, true);
      toolbar.appendChild(allBtn);
      pills.push(allBtn);

      categories.forEach(function (cat) {
        var btn = createPill(cat, cat, counts[cat] || 0, false);
        toolbar.appendChild(btn);
        pills.push(btn);
      });

      var statusEl = document.createElement("p");
      statusEl.setAttribute("class", "filter-status");
      statusEl.setAttribute("aria-live", "polite");
      statusEl.setAttribute("role", "status");
      statusEl.textContent = "Showing " + cards.length + " of " + cards.length + " essays";
      toolbar.appendChild(statusEl);

      if (blogGrid.parentNode) {
        blogGrid.parentNode.insertBefore(toolbar, blogGrid);
      }

      var currentCat = "all";
      var currentQuery = "";

      var applyFilter = function (selectedCat, rawQuery, syncUrl) {
        var activeCat = matchCategory(selectedCat);
        var cleanQuery = String(rawQuery || "").trim();
        var tokens = cleanQuery ? cleanQuery.toLowerCase().split(/\s+/) : [];
        currentCat = activeCat;
        currentQuery = cleanQuery;
        var shown = 0;

        cards.forEach(function (card, idx) {
          var cardCat = card.getAttribute("data-category") || "";
          var catMatch = activeCat === "all" || cardCat === activeCat;
          var textMatch = true;
          if (catMatch && tokens.length) {
            var hay = cardSearchIndex[idx] || "";
            for (var t = 0; t < tokens.length; t++) {
              if (hay.indexOf(tokens[t]) === -1) {
                textMatch = false;
                break;
              }
            }
          }
          var isMatch = catMatch && textMatch;
          if (isMatch) {
            card.removeAttribute("hidden");
            card.removeAttribute("aria-hidden");
            card.classList.remove("is-filtered-out");
            card.classList.add("is-visible");
            card.style.transitionDelay = "0ms";
            shown++;
          } else {
            card.setAttribute("hidden", "");
            card.setAttribute("aria-hidden", "true");
            card.classList.add("is-filtered-out");
          }
        });

        pills.forEach(function (pill) {
          var isSelected = pill.getAttribute("data-filter") === activeCat;
          pill.setAttribute("aria-pressed", isSelected ? "true" : "false");
          pill.setAttribute("class", isSelected ? "filter-pill is-active" : "filter-pill");
        });

        statusEl.textContent = "Showing " + shown + " of " + cards.length + " essays";

        if (syncUrl && window.history && window.history.replaceState) {
          var nextUrl = window.location.pathname;
          var queryParts = [];
          if (activeCat !== "all") {
            queryParts.push("category=" + encodeURIComponent(activeCat));
          }
          if (cleanQuery) {
            queryParts.push("q=" + encodeURIComponent(cleanQuery));
          }
          if (queryParts.length) {
            nextUrl += "?" + queryParts.join("&");
          }
          window.history.replaceState(null, "", nextUrl);
        }
      };

      pills.forEach(function (pill) {
        pill.addEventListener("click", function () {
          applyFilter(pill.getAttribute("data-filter") || "all", searchInput.value, true);
        });
      });

      searchInput.addEventListener("input", function () {
        applyFilter(currentCat, searchInput.value, true);
      });
      searchInput.addEventListener("search", function () {
        applyFilter(currentCat, searchInput.value, true);
      });
      searchInput.addEventListener("keydown", function (e) {
        if ((e.key === "Escape" || e.key === "Esc") && searchInput.value) {
          e.preventDefault();
          searchInput.value = "";
          applyFilter(currentCat, "", true);
        }
      });

      toolbar.addEventListener("keydown", function (e) {
        var idx = pills.indexOf(document.activeElement);
        if (idx === -1) return;
        var nextIdx = -1;
        if (e.key === "ArrowRight" || e.key === "ArrowDown") {
          nextIdx = (idx + 1) % pills.length;
        } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
          nextIdx = (idx - 1 + pills.length) % pills.length;
        } else if (e.key === "Home") {
          nextIdx = 0;
        } else if (e.key === "End") {
          nextIdx = pills.length - 1;
        }
        if (nextIdx !== -1) {
          e.preventDefault();
          pills[nextIdx].focus();
        }
      });

      var initialCat = getCategoryFromUrl();
      var initialQuery = getQueryFromUrl();
      if (initialQuery) {
        searchInput.value = initialQuery;
      }
      if (initialCat !== "all" || initialQuery) {
        applyFilter(initialCat, initialQuery, false);
      }

      window.addEventListener("popstate", function () {
        var q = getQueryFromUrl();
        searchInput.value = q;
        applyFilter(getCategoryFromUrl(), q, false);
      });
      window.addEventListener("hashchange", function () {
        applyFilter(getCategoryFromUrl(), searchInput.value, false);
      });
    }
  }

  // Progressive enhancement: Trust Arithmetic slider (#ex-trust-arithmetic)
  var trustFig = document.getElementById("ex-trust-arithmetic");
  if (trustFig) {
    var markerLine = document.getElementById("ex-trust-marker-line");
    var dotRecord = document.getElementById("ex-trust-dot-record");
    var dotPairs = document.getElementById("ex-trust-dot-pairs");
    var readN = document.getElementById("ex-trust-readout-n");
    var readRecord = document.getElementById("ex-trust-readout-record");
    var readPairs = document.getElementById("ex-trust-readout-pairs");

    var controls = document.createElement("div");
    controls.className = "ex-controls";

    var label = document.createElement("label");
    label.setAttribute("for", "ex-trust-slider");
    label.textContent = "Group size (n):";

    var slider = document.createElement("input");
    slider.setAttribute("type", "range");
    slider.setAttribute("id", "ex-trust-slider");
    slider.setAttribute("min", "2");
    slider.setAttribute("max", "20");
    slider.setAttribute("step", "1");
    slider.setAttribute("value", "10");
    slider.setAttribute("aria-label", "Group size from 2 to 20 people");

    var statusOut = document.createElement("span");
    statusOut.setAttribute("id", "ex-trust-slider-val");
    statusOut.setAttribute("aria-live", "polite");
    statusOut.textContent = "10 people · 45 pairs";

    controls.appendChild(label);
    controls.appendChild(slider);
    controls.appendChild(statusOut);

    var caption = trustFig.querySelector("figcaption");
    if (caption) {
      trustFig.insertBefore(controls, caption);
    } else {
      trustFig.appendChild(controls);
    }

    var updateTrust = function () {
      var n = parseInt(slider.value, 10) || 10;
      var pairs = (n * (n - 1)) / 2;
      var pRecord = Math.pow(0.97, n);
      var pPairs = Math.pow(0.90, pairs);
      var x = 80 + (n - 2) * 30;
      var yRecord = (270 - 200 * pRecord).toFixed(1);
      var yPairs = (270 - 200 * pPairs).toFixed(1);
      var pairLabel = n + " people \u00b7 " + pairs + (pairs === 1 ? " pair" : " pairs");

      if (markerLine) {
        markerLine.setAttribute("x1", String(x));
        markerLine.setAttribute("x2", String(x));
      }
      if (dotRecord) {
        dotRecord.setAttribute("cx", String(x));
        dotRecord.setAttribute("cy", String(yRecord));
      }
      if (dotPairs) {
        dotPairs.setAttribute("cx", String(x));
        dotPairs.setAttribute("cy", String(yPairs));
      }
      if (readN) readN.textContent = pairLabel;
      if (readRecord) readRecord.textContent = "Shared record: " + (pRecord * 100).toFixed(1) + "%";
      if (readPairs) {
        var pairPct = pPairs * 100;
        readPairs.textContent = "Pair-by-pair: " + (pairPct < 0.05 ? "<0.1%" : pairPct.toFixed(1) + "%");
      }
      statusOut.textContent = pairLabel;
    };

    slider.addEventListener("input", updateTrust);
    slider.addEventListener("change", updateTrust);
  }

  // Progressive enhancement: Action Receipt revoke toggle (#ex-action-receipt)
  var revokeBtns = Array.prototype.slice.call(document.querySelectorAll("#ex-revoke-btn, #ex-revoke-btn-m, .ex-revoke-btn"));
  var receiptStatuses = Array.prototype.slice.call(document.querySelectorAll("#ex-receipt-status, #ex-receipt-status-m, .ex-receipt-status"));
  if (revokeBtns.length && receiptStatuses.length) {
    var revoked = false;
    revokeBtns.forEach(function (btn) { btn.setAttribute("aria-pressed", "false"); });
    receiptStatuses.forEach(function (stat) { stat.setAttribute("aria-live", "polite"); });
    var toggleRevoke = function () {
      revoked = !revoked;
      revokeBtns.forEach(function (btn) {
        btn.setAttribute("aria-pressed", revoked ? "true" : "false");
        var btnText = btn.querySelector("text");
        if (btnText) btnText.textContent = revoked ? "Restore" : "Revoke";
      });
      receiptStatuses.forEach(function (stat) {
        stat.textContent = revoked ? "Status: Lease revoked" : "Status: Active lease";
      });
    };
    revokeBtns.forEach(function (btn) {
      btn.addEventListener("click", toggleRevoke);
      btn.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          toggleRevoke();
        }
      });
    });
  }

  // Progressive enhancement: Medical bill audit discrepancy toggle (#ex-medical-bill-audit)
  var billToggle = document.getElementById("ex-bill-toggle");
  var billStatus = document.getElementById("ex-bill-status");
  var billCodeRow = document.getElementById("ex-bill-code-row");
  var billAuditRow = document.getElementById("ex-bill-audit-row");
  if (billToggle && billStatus && billCodeRow && billAuditRow) {
    var inspected = false;
    billToggle.setAttribute("aria-pressed", "false");
    billStatus.setAttribute("aria-live", "polite");
    var toggleBtnText = billToggle.querySelector("text");
    var toggleAudit = function () {
      inspected = !inspected;
      billToggle.setAttribute("aria-pressed", inspected ? "true" : "false");
      billStatus.textContent = inspected ? "Audit: Overcharge flagged" : "Audit: Code discrepancy";
      billCodeRow.textContent = inspected ? "Clinical Notes: 20 min, minor rash" : "Billed: Emergency Level 5 (Code 99285)";
      billAuditRow.textContent = inspected ? "CMS NCCI Match: Level 2 (Code 99282)" : "Notes show minor care: Level 3 (99283)";
      if (toggleBtnText) toggleBtnText.textContent = inspected ? "Reset" : "Inspect";
    };
    billToggle.addEventListener("click", toggleAudit);
    billToggle.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        toggleAudit();
      }
    });
  }

  // Progressive enhancement: Portable profile comparison toggle (#ex-profile-portability)
  var profileToggle = document.getElementById("ex-profile-toggle");
  var profileStatus = document.getElementById("ex-profile-status");
  var profileLeftCard = document.getElementById("ex-profile-left-card");
  var profileRightCard = document.getElementById("ex-profile-right-card");
  if (profileToggle && profileStatus && profileLeftCard && profileRightCard) {
    var profileHighlighted = false;
    profileToggle.setAttribute("aria-pressed", "false");
    profileStatus.setAttribute("aria-live", "polite");
    var profileBtnText = profileToggle.querySelector("text");
    var toggleProfile = function () {
      profileHighlighted = !profileHighlighted;
      profileToggle.setAttribute("aria-pressed", profileHighlighted ? "true" : "false");
      profileStatus.textContent = profileHighlighted ? "Viewing: Portable profile" : "Portable Profile";
      profileLeftCard.setAttribute("opacity", profileHighlighted ? "0.35" : "1.0");
      if (profileBtnText) profileBtnText.textContent = profileHighlighted ? "Show Both" : "Highlight Portable";
    };
    profileToggle.addEventListener("click", toggleProfile);
    profileToggle.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        toggleProfile();
      }
    });
  }

  // Progressive enhancement: Buyer pool blind match toggle (#ex-buyer-pool)
  var poolToggle = document.getElementById("ex-pool-toggle");
  var poolStatus = document.getElementById("ex-pool-status");
  var poolVolume = document.getElementById("ex-pool-volume");
  var poolPrivacy = document.getElementById("ex-pool-privacy");
  var poolSupplier = document.getElementById("ex-pool-supplier");
  if (poolToggle && poolStatus && poolVolume && poolPrivacy && poolSupplier) {
    var poolInspected = false;
    poolToggle.setAttribute("aria-pressed", "false");
    poolStatus.setAttribute("aria-live", "polite");
    var poolBtnText = poolToggle.querySelector("text");
    var togglePool = function () {
      poolInspected = !poolInspected;
      poolToggle.setAttribute("aria-pressed", poolInspected ? "true" : "false");
      poolStatus.textContent = poolInspected ? "Audit: Verified blind match" : "Status: Tier unlocked";
      poolVolume.textContent = poolInspected ? "Tally: 40 + 30 + 50 = 120 boxes" : "120 boxes total · Meets wholesale tier";
      poolPrivacy.textContent = poolInspected ? "Cryptographic proof: Zero individual orders leaked" : "Individual order sizes stay strictly private";
      poolSupplier.textContent = poolInspected ? "Distributor: Single pooled invoice" : "Distributor sees only single bulk order";
      if (poolBtnText) poolBtnText.textContent = poolInspected ? "Reset" : "Inspect";
    };
    poolToggle.addEventListener("click", togglePool);
    poolToggle.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        togglePool();
      }
    });
  }

  // Progressive enhancement: Small assistants vs giant mind toggle (#ex-small-assistants)
  var astToggle = document.getElementById("ex-assistants-toggle");
  var astStatus = document.getElementById("ex-assistants-status");
  var astLeftNote = document.getElementById("ex-assistants-left-note");
  var astRightNote = document.getElementById("ex-assistants-right-note");
  var astLeftBadge = document.getElementById("ex-assistants-left-badge");
  var astRightBadge = document.getElementById("ex-assistants-right-badge");
  if (astToggle && astStatus && astLeftNote && astRightNote) {
    var astInspected = false;
    astToggle.setAttribute("aria-pressed", "false");
    astStatus.setAttribute("aria-live", "polite");
    var astBtnText = astToggle.querySelector("text");
    var toggleAssistants = function () {
      astInspected = !astInspected;
      astToggle.setAttribute("aria-pressed", astInspected ? "true" : "false");
      astStatus.textContent = astInspected
        ? "Scenario: Flaw injected \u2014 caught by diverse verifiers"
        : "Architecture: Independent verifiers bound to one person";
      astLeftNote.textContent = astInspected
        ? "Cascades to all 100,000 households"
        : "Unbounded blast radius across cloud";
      astRightNote.textContent = astInspected
        ? "Verifier flags flaw: zero blast radius"
        : "Independent verifier checks before action";
      if (astLeftBadge) {
        astLeftBadge.textContent = astInspected ? "ERROR PROPAGATED" : "FRAGILE COUPLING";
      }
      if (astRightBadge) {
        astRightBadge.textContent = astInspected ? "BLOCKED AT GATE" : "BOUNDED BLAST RADIUS";
      }
      if (astBtnText) astBtnText.textContent = astInspected ? "Reset" : "Test Blind Spot";
    };
    astToggle.addEventListener("click", toggleAssistants);
    astToggle.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        toggleAssistants();
      }
    });
  }

  // Progressive enhancement: Procurement rubric comparison toggle (#ex-procurement-rubric)
  var rubricToggle = document.getElementById("ex-rubric-toggle");
  var rubricStatus = document.getElementById("ex-rubric-status");
  var rubricLeftPanel = document.getElementById("ex-rubric-left-panel");
  var rubricRightPanel = document.getElementById("ex-rubric-right-panel");
  if (rubricToggle && rubricStatus && rubricLeftPanel && rubricRightPanel) {
    var rubricInspected = false;
    rubricToggle.setAttribute("aria-pressed", "false");
    rubricStatus.setAttribute("aria-live", "polite");
    var rubricBtnText = rubricToggle.querySelector("text");
    var toggleRubric = function () {
      rubricInspected = !rubricInspected;
      rubricToggle.setAttribute("aria-pressed", rubricInspected ? "true" : "false");
      rubricStatus.textContent = rubricInspected
        ? "Status: Verified tender safeguards highlighted"
        : "Status: Comparing demo claims vs. tender rules";
      rubricLeftPanel.setAttribute("opacity", rubricInspected ? "0.35" : "1.0");
      if (rubricBtnText) rubricBtnText.textContent = rubricInspected ? "Show All" : "Highlight Tender";
    };
    rubricToggle.addEventListener("click", toggleRubric);
    rubricToggle.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        toggleRubric();
      }
    });
  }

  // Progressive enhancement: Quests not feeds interactive completion (#ex-quests-not-feeds)
  var questsToggle = document.getElementById("ex-quests-toggle");
  var questsStatus = document.getElementById("ex-quests-status");
  var questsLeftPanel = document.getElementById("ex-quests-left-panel");
  var questsRightPanel = document.getElementById("ex-quests-right-panel");
  if (questsToggle && questsStatus && questsLeftPanel && questsRightPanel) {
    var questsCompleted = false;
    questsToggle.setAttribute("aria-pressed", "false");
    questsStatus.setAttribute("aria-live", "polite");
    var questsBtnText = questsToggle.querySelector("text");
    var mark1 = document.getElementById("ex-quest-mark-1");
    var mark2 = document.getElementById("ex-quest-mark-2");
    var mark3 = document.getElementById("ex-quest-mark-3");
    var text1 = document.getElementById("ex-quest-text-1");
    var text2 = document.getElementById("ex-quest-text-2");
    var text3 = document.getElementById("ex-quest-text-3");
    var bannerBox = document.getElementById("ex-quest-banner-box");
    var bannerTitle = document.getElementById("ex-quest-banner-title");
    var bannerSub = document.getElementById("ex-quest-banner-sub");
    var bottomBadge = document.getElementById("ex-quest-bottom-badge");

    var toggleQuests = function () {
      questsCompleted = !questsCompleted;
      questsToggle.setAttribute("aria-pressed", questsCompleted ? "true" : "false");
      questsStatus.textContent = questsCompleted
        ? "Status: All daily quests completed (quiet finish line reached)"
        : "Status: Active daily quests (3 priorities)";
      questsLeftPanel.setAttribute("opacity", questsCompleted ? "0.3" : "1.0");

      if (questsBtnText) questsBtnText.textContent = questsCompleted ? "Reset Quests" : "Complete Quests";

      if (mark1) mark1.textContent = questsCompleted ? "\u2713" : "\u25CB";
      if (mark2) mark2.textContent = questsCompleted ? "\u2713" : "\u25CB";
      if (mark3) mark3.textContent = questsCompleted ? "\u2713" : "\u25CB";

      if (text1) text1.setAttribute("opacity", questsCompleted ? "0.5" : "1.0");
      if (text2) text2.setAttribute("opacity", questsCompleted ? "0.5" : "1.0");
      if (text3) text3.setAttribute("opacity", questsCompleted ? "0.5" : "1.0");

      if (bannerBox) bannerBox.setAttribute("fill", questsCompleted ? "#0B3F30" : "#F3E8D8");
      if (bannerTitle) {
        bannerTitle.textContent = questsCompleted
          ? "Finish line reached: 3 of 3 tasks completed"
          : "Finish line: 3 of 3 tasks remaining";
        bannerTitle.setAttribute("fill", questsCompleted ? "#FAF3EA" : "#5E564B");
      }
      if (bannerSub) {
        bannerSub.textContent = questsCompleted
          ? "Tool closed. Time to step outside and back to your life."
          : "Tool will close when all items are marked";
        bannerSub.setAttribute("fill", questsCompleted ? "#FAF3EA" : "#5E564B");
      }
      if (bottomBadge) {
        bottomBadge.textContent = questsCompleted
          ? "Human outcome: Daily task done; quiet until tomorrow"
          : "Human outcome: Clear agency & calm focus";
      }
    };

    questsToggle.addEventListener("click", toggleQuests);
    questsToggle.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        toggleQuests();
      }
    });
  }

  // Progressive enhancement: Shared Horizon hexagon role focus (#ex-horizon-hexagon)
  // and interactive Sample Moves deck explorer (#sh-deck-preview) with Play/Brief toggle.
  var hexFig = document.getElementById("ex-horizon-hexagon");
  var deckPreview = document.getElementById("sh-deck-preview");
  if (hexFig || deckPreview) {
    var nodes = hexFig ? Array.prototype.slice.call(hexFig.querySelectorAll(".sh-node")) : [];
    var chords = hexFig ? Array.prototype.slice.call(hexFig.querySelectorAll(".sh-chord")) : [];
    var spokes = hexFig ? Array.prototype.slice.call(hexFig.querySelectorAll(".sh-spoke")) : [];
    var hexCaption = hexFig ? hexFig.querySelector("figcaption") : null;
    if (hexCaption) hexCaption.setAttribute("aria-live", "polite");
    nodes.forEach(function (n) { n.setAttribute("aria-pressed", "false"); });
    var defaultCap = hexCaption ? hexCaption.textContent : "";

    var sampleCards = deckPreview
      ? Array.prototype.slice.call(deckPreview.querySelectorAll(".sh-sample-card"))
      : [];
    var activeRole = null;
    var activeMode = "play";
    var rolePills = [];
    var modeButtons = [];
    var deckStatusEl = null;

    var roleLabels = {
      "citizen": "Citizen",
      "official": "Public Official",
      "researcher": "Safety Researcher",
      "lab": "Frontier Lab",
      "builder": "Independent Builder",
      "civil-society": "Civil Society / Organiser"
    };

    var updateStatusText = function () {
      if (!deckStatusEl) return;
      var modeLabel = activeMode === "brief" ? "Table / memo view (Brief)" : "Card view (Play)";
      if (!activeRole) {
        deckStatusEl.textContent = "Showing all 6 paths in " + modeLabel + ".";
      } else {
        var rName = roleLabels[activeRole] || activeRole;
        deckStatusEl.textContent = "Focused on " + rName + " in " + modeLabel + ".";
      }
    };

    var findNodeByRole = function (role) {
      for (var i = 0; i < nodes.length; i++) {
        if (nodes[i].getAttribute("data-role") === role) return nodes[i];
      }
      return null;
    };

    var setRole = function (role, explicitNode) {
      var nextRole = (!role || role === "all" || activeRole === role) ? null : role;
      activeRole = nextRole;

      nodes.forEach(function (n) {
        var r = n.getAttribute("data-role");
        var isMatch = nextRole !== null && r === nextRole;
        n.classList.toggle("is-active", isMatch);
        n.classList.toggle("is-dimmed", nextRole !== null && !isMatch);
        n.setAttribute("aria-pressed", isMatch ? "true" : "false");
      });
      chords.forEach(function (c) {
        var roles = (c.getAttribute("data-roles") || "").split(" ");
        c.classList.toggle("is-active", nextRole !== null && roles.indexOf(nextRole) !== -1);
      });
      spokes.forEach(function (s) {
        s.classList.toggle("is-active", nextRole !== null && s.getAttribute("data-role") === nextRole);
      });

      if (hexCaption) {
        if (!nextRole) {
          hexCaption.textContent = defaultCap;
        } else {
          var targetNode = explicitNode || findNodeByRole(nextRole);
          if (targetNode) {
            var t = targetNode.getAttribute("data-title") || "";
            var s = targetNode.getAttribute("data-summary") || "";
            if (t && s) hexCaption.textContent = t + " \u2014 " + s;
          }
        }
      }

      if (deckPreview) {
        deckPreview.classList.toggle("has-role-focus", nextRole !== null);
        sampleCards.forEach(function (card) {
          var cRole = card.getAttribute("data-role");
          var isMatch = nextRole !== null && cRole === nextRole;
          card.classList.toggle("is-active", isMatch);
          card.classList.toggle("is-dimmed", nextRole !== null && !isMatch);
          if (isMatch) {
            card.setAttribute("aria-current", "true");
          } else {
            card.removeAttribute("aria-current");
          }
        });
      }

      rolePills.forEach(function (pill) {
        var pFilter = pill.getAttribute("data-role-filter");
        var isSelected = (!nextRole && pFilter === "all") || (nextRole !== null && pFilter === nextRole);
        pill.setAttribute("aria-pressed", isSelected ? "true" : "false");
        pill.classList.toggle("is-active", isSelected);
      });

      updateStatusText();
    };

    var setViewMode = function (mode) {
      activeMode = mode === "brief" ? "brief" : "play";
      if (deckPreview) {
        deckPreview.classList.toggle("is-brief-mode", activeMode === "brief");
        deckPreview.setAttribute("data-mode", activeMode);
      }
      modeButtons.forEach(function (btn) {
        var bMode = btn.getAttribute("data-view-mode");
        var isSelected = bMode === activeMode;
        btn.setAttribute("aria-pressed", isSelected ? "true" : "false");
        btn.classList.toggle("is-active", isSelected);
      });
      updateStatusText();
    };

    var bindToolbarKeyNav = function (container, btnList) {
      container.addEventListener("keydown", function (e) {
        var idx = btnList.indexOf(document.activeElement);
        if (idx === -1) return;
        var nextIdx = -1;
        if (e.key === "ArrowRight" || e.key === "ArrowDown") {
          nextIdx = (idx + 1) % btnList.length;
        } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
          nextIdx = (idx - 1 + btnList.length) % btnList.length;
        } else if (e.key === "Home") {
          nextIdx = 0;
        } else if (e.key === "End") {
          nextIdx = btnList.length - 1;
        }
        if (nextIdx !== -1) {
          e.preventDefault();
          btnList[nextIdx].focus();
        }
      });
    };

    if (deckPreview && sampleCards.length) {
      var controlsWrap = document.createElement("div");
      controlsWrap.className = "sh-deck-controls";
      controlsWrap.setAttribute("role", "region");
      controlsWrap.setAttribute("aria-label", "Sample moves explorer controls");

      var roleToolbar = document.createElement("div");
      roleToolbar.className = "sh-role-pills";
      roleToolbar.setAttribute("role", "toolbar");
      roleToolbar.setAttribute("aria-label", "Filter sample moves by path");

      var makeRolePill = function (label, roleKey, isPressed) {
        var btn = document.createElement("button");
        btn.setAttribute("type", "button");
        btn.className = isPressed ? "filter-pill sh-role-pill is-active" : "filter-pill sh-role-pill";
        btn.setAttribute("data-role-filter", roleKey);
        btn.setAttribute("aria-pressed", isPressed ? "true" : "false");
        btn.textContent = label;
        btn.addEventListener("click", function () {
          if (roleKey === "all") {
            activeRole = null;
            setRole(null, null);
          } else {
            setRole(roleKey, findNodeByRole(roleKey));
          }
        });
        return btn;
      };

      var showAllBtn = makeRolePill("Show all six paths", "all", true);
      roleToolbar.appendChild(showAllBtn);
      rolePills.push(showAllBtn);

      sampleCards.forEach(function (card) {
        var rKey = card.getAttribute("data-role") || "";
        if (!rKey) return;
        var rLabel = card.getAttribute("data-role-label") || roleLabels[rKey] || rKey;
        var pill = makeRolePill(rLabel, rKey, false);
        roleToolbar.appendChild(pill);
        rolePills.push(pill);
      });

      bindToolbarKeyNav(roleToolbar, rolePills);
      controlsWrap.appendChild(roleToolbar);

      var viewBar = document.createElement("div");
      viewBar.className = "sh-view-bar";

      var modeGroup = document.createElement("div");
      modeGroup.className = "sh-mode-switch";
      modeGroup.setAttribute("role", "group");
      modeGroup.setAttribute("aria-label", "Switch between Play card view and Brief memo view");

      var makeModeBtn = function (label, modeVal, isPressed) {
        var btn = document.createElement("button");
        btn.setAttribute("type", "button");
        btn.className = isPressed ? "filter-pill sh-mode-btn is-active" : "filter-pill sh-mode-btn";
        btn.setAttribute("data-view-mode", modeVal);
        btn.setAttribute("aria-pressed", isPressed ? "true" : "false");
        btn.textContent = label;
        btn.addEventListener("click", function () {
          setViewMode(modeVal);
        });
        return btn;
      };

      var playBtn = makeModeBtn("Card view (Play)", "play", true);
      var briefBtn = makeModeBtn("Table / memo view (Brief)", "brief", false);
      modeGroup.appendChild(playBtn);
      modeGroup.appendChild(briefBtn);
      modeButtons.push(playBtn, briefBtn);
      bindToolbarKeyNav(modeGroup, modeButtons);

      deckStatusEl = document.createElement("p");
      deckStatusEl.className = "sh-deck-status";
      deckStatusEl.setAttribute("role", "status");
      deckStatusEl.setAttribute("aria-live", "polite");
      deckStatusEl.textContent = "Showing all 6 paths in Card view (Play).";

      viewBar.appendChild(modeGroup);
      viewBar.appendChild(deckStatusEl);
      controlsWrap.appendChild(viewBar);

      if (deckPreview.parentNode) {
        deckPreview.parentNode.insertBefore(controlsWrap, deckPreview);
      }
    }

    nodes.forEach(function (node) {
      var role = node.getAttribute("data-role");
      node.addEventListener("click", function () { setRole(role, node); });
      node.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          setRole(role, node);
        }
      });
    });
  }

  // Progressive enhancement: Epistemic confidence calibration explainer (#ex-confidence-calibration)
  var calibToggle = document.getElementById("ex-calibration-toggle");
  var calibStatus = document.getElementById("ex-calibration-status");
  var calibLeft = document.getElementById("ex-calib-left-panel");
  var calibRight = document.getElementById("ex-calib-right-panel");
  var calibBtnText = document.getElementById("ex-calibration-btn-text");

  if (calibToggle && calibStatus && calibLeft && calibRight) {
    var calibActive = false;
    var toggleCalib = function () {
      calibActive = !calibActive;
      calibToggle.setAttribute("aria-pressed", calibActive ? "true" : "false");
      calibStatus.textContent = calibActive
        ? "Audit: Calibrated assistant highlights provenance and inference boundaries"
        : "Status: Comparing overconfident chatbot vs. calibrated assistant";
      calibLeft.setAttribute("opacity", calibActive ? "0.35" : "1.0");
      calibRight.setAttribute("opacity", "1.0");
      if (calibBtnText) {
        calibBtnText.textContent = calibActive ? "Reset Comparison" : "Highlight Calibrated";
      }
    };
    calibToggle.addEventListener("click", toggleCalib);
    calibToggle.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        toggleCalib();
      }
    });
  }

  // Progressive enhancement: Deliberation diversity toggle (#ex-deliberation-diversity)
  var delibToggle = document.getElementById("ex-panel-toggle");
  var delibStatus = document.getElementById("ex-panel-status");
  var delibArch = document.getElementById("ex-panel-arch");
  var delibSpread = document.getElementById("ex-panel-spread");
  var delibCoherence = document.getElementById("ex-panel-coherence");
  var delibOutcome = document.getElementById("ex-panel-outcome");
  var delibBtnText = document.getElementById("ex-panel-btn-text");

  if (delibToggle && delibStatus && delibArch && delibSpread && delibCoherence && delibOutcome) {
    var inspected = false;
    delibToggle.setAttribute("aria-pressed", "false");
    delibStatus.setAttribute("aria-live", "polite");
    var toggleDelib = function () {
      inspected = !inspected;
      delibToggle.setAttribute("aria-pressed", inspected ? "true" : "false");
      delibStatus.textContent = inspected ? "Audit: Dissent verified" : "Panel: Multi-model";
      delibArch.textContent = inspected ? "Audit: 4 independent models tested" : "Four distinct model families · Independent training";
      delibSpread.textContent = inspected ? "Audit: First-choice concentration down 42%" : "Balanced spread · Real trade-offs emerge";
      delibCoherence.textContent = inspected ? "Audit: Transit and clinic objections validated" : "Auditor verifies choices match assigned values";
      delibOutcome.textContent = inspected ? "Audit: Minority dissent saved into public record" : "Minority concerns surfaced before adoption";
      if (delibBtnText) {
        delibBtnText.textContent = inspected ? "Reset" : "Inspect";
      }
    };
    delibToggle.addEventListener("click", toggleDelib);
    delibToggle.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        toggleDelib();
      }
    });
  }

  // Progressive enhancement: Question waypoint inspector (#ex-ask-dont-equip)
  var askToggle = document.getElementById("ex-toggle-mode");
  var askStatus = document.getElementById("ex-waypoint-status");
  if (askToggle && askStatus) {
    var askInspected = false;
    askToggle.setAttribute("aria-pressed", "false");
    askStatus.setAttribute("aria-live", "polite");
    var askBtnText = askToggle.querySelector("text");
    var toggleAsk = function () {
      askInspected = !askInspected;
      askToggle.setAttribute("aria-pressed", askInspected ? "true" : "false");
      askStatus.textContent = askInspected ? "Status: Question clarified" : "Status: Guided execution";
      if (askBtnText) askBtnText.textContent = askInspected ? "Reset" : "Inspect";
    };
    askToggle.addEventListener("click", toggleAsk);
    askToggle.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        toggleAsk();
      }
    });
  }

  // Progressive enhancement: Cognitive Tours waypoint inspector (#ex-cognitive-tours)
  var tourBtn = document.getElementById("ex-tour-inspect-btn");
  var tourStatus = document.getElementById("ex-tour-status");
  var tourBtnText = document.getElementById("ex-tour-btn-text");
  var tourRow1 = document.getElementById("ex-tour-row-1");
  var tourRow2 = document.getElementById("ex-tour-row-2");
  var tourRow3 = document.getElementById("ex-tour-row-3");
  if (tourBtn && tourStatus) {
    var tourInspected = false;
    tourBtn.setAttribute("aria-pressed", "false");
    tourStatus.setAttribute("aria-live", "polite");
    var toggleTour = function () {
      tourInspected = !tourInspected;
      tourBtn.setAttribute("aria-pressed", tourInspected ? "true" : "false");
      if (tourBtnText) {
        tourBtnText.textContent = tourInspected ? "Reset" : "Inspect";
      }
      tourStatus.textContent = tourInspected ? "Status: Rationale Verified" : "Status: 3 Waypoints Linked";
      var activeFill = tourInspected ? "#E4EFEA" : "#F3E8D8";
      var activeStroke = tourInspected ? "#0B3F30" : "#1F6B4E";
      var r1 = tourRow1 ? tourRow1.querySelector("rect") : null;
      var r2 = tourRow2 ? tourRow2.querySelector("rect") : null;
      var r3 = tourRow3 ? tourRow3.querySelector("rect") : null;
      if (r1) { r1.setAttribute("fill", activeFill); r1.setAttribute("stroke", activeStroke); }
      if (r2) { r2.setAttribute("fill", activeFill); r2.setAttribute("stroke", activeStroke); }
      if (r3) { r3.setAttribute("fill", activeFill); r3.setAttribute("stroke", activeStroke); }
    };
    tourBtn.addEventListener("click", toggleTour);
    tourBtn.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        toggleTour();
      }
    });
  }

  // Progressive enhancement: Action Journey vs Word Highlights inspector (#ex-journey-vs-score)
  var journeyToggle = document.getElementById("ex-journey-toggle");
  var journeyStatus = document.getElementById("ex-journey-status");
  var journeyBtnText = document.getElementById("ex-journey-btn-text");
  var step3Box = document.getElementById("ex-journey-step-3-box");
  var step3Title = document.getElementById("ex-journey-step-3-title");
  var step3Desc = document.getElementById("ex-journey-step-3-desc");
  if (journeyToggle && journeyStatus) {
    var journeyInspected = false;
    journeyToggle.setAttribute("aria-pressed", "false");
    journeyStatus.setAttribute("aria-live", "polite");
    var toggleJourney = function () {
      journeyInspected = !journeyInspected;
      journeyToggle.setAttribute("aria-pressed", journeyInspected ? "true" : "false");
      if (journeyBtnText) {
        journeyBtnText.textContent = journeyInspected ? "Reset" : "Inspect";
      }
      journeyStatus.textContent = journeyInspected ? "Status: Step 3 Divergence" : "Status: 4 steps logged";
      if (step3Box) {
        step3Box.setAttribute("fill", journeyInspected ? "#FAF3EA" : "#F3E8D8");
        step3Box.setAttribute("stroke", journeyInspected ? "#B85C38" : "#1F6B4E");
        step3Box.setAttribute("stroke-width", journeyInspected ? "2" : "1");
      }
      if (step3Title) {
        step3Title.setAttribute("fill", journeyInspected ? "#B85C38" : "#1F6B4E");
      }
      if (step3Desc) {
        step3Desc.textContent = journeyInspected ? "Timezone drift detected (+8h offset)" : "Checked departure slot (14:00 UTC)";
      }
    };
    journeyToggle.addEventListener("click", toggleJourney);
    journeyToggle.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        toggleJourney();
      }
    });
  }

  // Progressive enhancement: Out-of-band authorization explainer (#ex-out-of-band-approval)
  var oobToggle = document.getElementById("ex-oob-toggle");
  var oobLeftStatus = document.getElementById("ex-oob-left-status");
  var oobRightStatus = document.getElementById("ex-oob-right-status");
  if (oobToggle && oobLeftStatus && oobRightStatus) {
    var oobActive = false;
    oobToggle.setAttribute("aria-pressed", "false");
    oobRightStatus.setAttribute("aria-live", "polite");
    var oobBtnText = oobToggle.querySelector("text");
    var toggleOob = function () {
      oobActive = !oobActive;
      oobToggle.setAttribute("aria-pressed", oobActive ? "true" : "false");
      if (oobBtnText) {
        oobBtnText.textContent = oobActive ? "RESET SIMULATION" : "SIMULATE APPROVAL CHECK";
      }
      oobLeftStatus.textContent = oobActive ? "Status: Assistant self-approved" : "Status: In-band gate subverted";
      oobRightStatus.textContent = oobActive ? "Status: Human verified on phone" : "Status: Separate key required";
    };
    oobToggle.addEventListener("click", toggleOob);
    oobToggle.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        toggleOob();
      }
    });
  }
  // Progressive enhancement: Observatory oversight gap interactive stage explorer (#ex-oversight-gap)
  var gapFig = document.getElementById("ex-oversight-gap");
  if (gapFig) {
    var stageCards = Array.prototype.slice.call(gapFig.querySelectorAll(".og-stage-card"));
    var stageSpotlights = Array.prototype.slice.call(gapFig.querySelectorAll(".og-spotlight"));
    var stageTickGroups = Array.prototype.slice.call(gapFig.querySelectorAll(".og-stage-tick-group"));
    var statusBadge = gapFig.querySelector(".og-status-badge");
    var statusText = gapFig.querySelector(".og-status-text");
    var resetBtn = document.getElementById("og-reset-btn");

    var stageDescriptions = {
      "1": {
        badge: "Stage 1 (Minutes):",
        text: "At Stage 1, tasks last a few minutes. People can read the whole answer directly before acting, and source receipts confirm links to real evidence."
      },
      "2": {
        badge: "Stage 2 (Hours):",
        text: "At Stage 2, autonomous work stretches into a morning or workday. Watching every screen step stops working; sandboxes and signed action receipts make each change visible afterwards."
      },
      "3": {
        badge: "Stage 3 (Days):",
        text: "At Stage 3, multi-day workflows cross multiple tools and systems. Expiring leases and power on loan replace permanent standing permissions so access ends when the job does."
      },
      "4": {
        badge: "Stage 4 (Weeks):",
        text: "At Stage 4, agent networks coordinate at machine speed over long horizons. A separate network for agents keeps machine traffic off human channels, where it can be watched and audited."
      }
    };

    var defaultBadge = "Overview:";
    var defaultText = "Select any stage to inspect how task duration grows and what oversight tool keeps people in charge.";
    var activeStage = null;

    var setStage = function (stageNum) {
      if (!stageNum || activeStage === stageNum) {
        activeStage = null;
        stageCards.forEach(function (card) {
          card.classList.remove("is-active", "is-dimmed");
          card.setAttribute("aria-pressed", "false");
        });
        stageSpotlights.forEach(function (spot) {
          spot.classList.remove("is-active");
        });
        stageTickGroups.forEach(function (tg) {
          tg.classList.remove("is-active");
          tg.setAttribute("aria-pressed", "false");
        });
        if (statusBadge) statusBadge.textContent = defaultBadge;
        if (statusText) statusText.textContent = defaultText;
        if (resetBtn) resetBtn.hidden = true;
        return;
      }

      activeStage = stageNum;
      stageCards.forEach(function (card) {
        var s = card.getAttribute("data-stage");
        var isMatch = s === stageNum;
        card.classList.toggle("is-active", isMatch);
        card.classList.toggle("is-dimmed", !isMatch);
        card.setAttribute("aria-pressed", isMatch ? "true" : "false");
      });
      stageSpotlights.forEach(function (spot) {
        var s = spot.getAttribute("data-stage");
        spot.classList.toggle("is-active", s === stageNum);
      });
      stageTickGroups.forEach(function (tg) {
        var s = tg.getAttribute("data-stage");
        var isMatch = s === stageNum;
        tg.classList.toggle("is-active", isMatch);
        tg.setAttribute("aria-pressed", isMatch ? "true" : "false");
      });

      var info = stageDescriptions[stageNum];
      if (info) {
        if (statusBadge) statusBadge.textContent = info.badge;
        if (statusText) statusText.textContent = info.text;
      }
      if (resetBtn) resetBtn.hidden = false;
    };

    var bindStageCard = function (el, sNum) {
      el.addEventListener("click", function () {
        setStage(sNum);
      });
      el.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          setStage(sNum);
        } else if (e.key === "ArrowRight" || e.key === "ArrowDown") {
          e.preventDefault();
          var nextNum = String(parseInt(sNum, 10) % 4 + 1);
          var nextCard = null;
          for (var i = 0; i < stageCards.length; i++) {
            if (stageCards[i].getAttribute("data-stage") === nextNum) {
              nextCard = stageCards[i];
              break;
            }
          }
          if (nextCard) nextCard.focus();
        } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
          e.preventDefault();
          var prevNum = String((parseInt(sNum, 10) + 2) % 4 + 1);
          var prevCard = null;
          for (var j = 0; j < stageCards.length; j++) {
            if (stageCards[j].getAttribute("data-stage") === prevNum) {
              prevCard = stageCards[j];
              break;
            }
          }
          if (prevCard) prevCard.focus();
        } else if (e.key === "Escape") {
          e.preventDefault();
          setStage(null);
        }
      });
    };

    stageCards.forEach(function (card) {
      var sNum = card.getAttribute("data-stage");
      if (sNum) bindStageCard(card, sNum);
    });

    stageTickGroups.forEach(function (tg) {
      var sNum = tg.getAttribute("data-stage");
      if (sNum) {
        tg.addEventListener("click", function () { setStage(sNum); });
        tg.addEventListener("keydown", function (e) {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            setStage(sNum);
          }
        });
      }
    });

    if (resetBtn) {
      resetBtn.addEventListener("click", function () {
        setStage(null);
      });
    }
  }
})();
