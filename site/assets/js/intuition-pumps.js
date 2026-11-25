(function () {
  "use strict";

  var root = document.getElementById("ip-workbench");
  if (!root) return;

  var SVG_NS = "http://www.w3.org/2000/svg";

  var FUSES = [
    {
      id: "vault",
      code: "01",
      short: "Local Vault",
      name: "Local sensor & receipt vault",
      desc: "Hardware-signed local records of real capacity, work, or clinical context kept under your own roof."
    },
    {
      id: "personal",
      code: "02",
      short: "1:1 Assistant",
      name: "1:1 loyal personal assistant",
      desc: "One assistant bound strictly to one person or co-op, flagging uncertainty instead of taking hidden commissions."
    },
    {
      id: "leases",
      code: "03",
      short: "Leases & Audits",
      name: "Expiring leases & physical audits",
      desc: "Narrow time-limited permissions plus sampled verification audits that deter exaggerated need or silent hoarding."
    },
    {
      id: "second_road",
      code: "04",
      short: "Second Road",
      name: "Second road & blind airlock",
      desc: "Separate signed channels for machine traffic, blind evaluation vaults, and fast local circuit breakers."
    },
    {
      id: "clearing",
      code: "05",
      short: "Open Clearing",
      name: "Mutual clearing & shared ownership",
      desc: "Zero-interest multilateral cycle netting, reserve pools, and cooperative share conversion tied to real capacity."
    }
  ];

  var SCENARIOS = [
    {
      id: "market-crash",
      tag: "01 · FINANCIAL MARKETS",
      title: "The ticker crashes, but the bakery still has flour",
      hook: "Tech stocks plunge twelve percent in a week and banks freeze commercial credit lines, even though every farm, clinic, solar roof, and machine shop is still standing.",
      inspired: "Inspired by the November 2026 global AI sell-off, WIR Bank (Stodder, 2009), Sardex (Iosifidis et al., 2018), Cycles Protocol (arXiv:2605.02436), and CIN working paper M31.",
      baseMetrics: { continuity: 97, agency: 92, capture: 90, audit: 95 },
      fuseImpact: {
        vault: {
          continuity: -14, agency: -18, capture: -10, audit: -28,
          breakNote: "Without local hardware-signed inventory and work receipts, clearing peers cannot verify whether a plant truly has idle ovens, power, or clinic hours. Trust collapses back into cash-up-front demands."
        },
        personal: {
          continuity: -10, agency: -24, capture: -16, audit: -8,
          breakNote: "Without a loyal local assistant negotiating on each business's real margins, desperate shops rely on third-party broker bots that steer desperate orders to the highest fee bidder."
        },
        leases: {
          continuity: -16, agency: -12, capture: -22, audit: -30,
          breakNote: "Pulling costly verification audits triggers the Hurwicz trap: rational firms exaggerate urgency and hide buffer inventory, dropping allocation efficiency from 98% down toward distorted central-planning levels."
        },
        second_road: {
          continuity: -8, agency: -15, capture: -20, audit: -18,
          breakNote: "Without signed agent channels and local circuit breakers, panic-driven trading bots flood order books and amplify a regional credit rumor into a cascade across healthy suppliers."
        },
        clearing: {
          continuity: -34, agency: -20, capture: -26, audit: -10,
          breakNote: "Pulling multilateral cycle netting and the default-reserve pool forces shops back into cash-only spot auctions. Under an 80% liquidity shock, fulfillment crashes from 97% down to 63% (M31 benchmark)."
        }
      },
      steps: [
        {
          step: 1,
          title: "Shock hits Wall Street; banks pull working credit",
          activeFuses: ["vault", "personal"],
          links: [["vault", "personal"]],
          legacy: "A regional bakery, a solar microgrid, a community clinic, and a machine shop all lose their short-term bank credit lines overnight because investors panic over distant tech earnings. None of their real equipment broke, yet every invoice stalls waiting for scarce cash.",
          cin: "Each shop's local vault already holds signed meter logs of real capacity: flour stock, kilowatt-hours, clinic appointment slots, and lathe hours. Each owner's 1:1 assistant checks local buffers privately before asking for outside help.",
          connection: "Layer 01 (Local Vault) proves physical capacity exists without exposing private books; Layer 02 (1:1 Assistant) turns that proof into a safe local trade budget.",
          metricsDelta: { continuity: 0, agency: 0, capture: 0, audit: 0 }
        },
        {
          step: 2,
          title: "Assistants publish selective capacity proofs, not bank balances",
          activeFuses: ["personal", "leases", "second_road"],
          links: [["personal", "leases"], ["leases", "second_road"]],
          legacy: "Businesses slash staff hours and dump inventory at fire-sale discounts just to raise emergency cash. Suppliers demand cash on delivery because nobody knows who is actually solvent.",
          cin: "Instead of revealing private cash reserves, each assistant sends a selective proof across the signed agent road: exact spare capacity available this week, bounded by a 7-day expiring fulfillment lease.",
          connection: "Layer 03 (Expiring Leases) caps maximum exposure per partner; Layer 04 (Second Road) blocks spoofed fake accounts from flooding the clearing board.",
          metricsDelta: { continuity: 0, agency: 0, capture: 0, audit: 0 }
        },
        {
          step: 3,
          title: "Closed loops cancel automatically with zero cash needed",
          activeFuses: ["second_road", "clearing"],
          links: [["second_road", "clearing"]],
          legacy: "The bakery owes the power co-op, the power co-op needs machined parts, the machine shop pays the clinic for staff care, and the clinic buys bread. All four sit idle because the first payer lacks cash.",
          cin: "The clearing engine spots the four-way closed loop and cancels all four obligations in one atomic step. Bread, electricity, machined valves, and clinic visits move on schedule with zero bank loans and zero interest.",
          connection: "Layer 04 (Signed Receipts) locks all four commitments simultaneously; Layer 05 (Cycle Clearing) settles the physical loop directly, just as Sardex and the Cycles Protocol demonstrate.",
          metricsDelta: { continuity: 0, agency: 0, capture: 0, audit: 0 }
        },
        {
          step: 4,
          title: "Sampled audits stop urgency gaming and hoarding",
          activeFuses: ["vault", "leases", "clearing"],
          links: [["vault", "leases"], ["leases", "clearing"]],
          legacy: "In unverified non-market plans, firms learn to lie: they claim emergency shortages to grab extra supplies while hiding spare stock in back rooms, starving honest neighbors.",
          cin: "A random twenty percent of high-urgency requests face physical receipt audits against hardware meter logs. Inflating urgency forfeits clearing priority and draws a penalty, keeping honest reporting cheaper than cheating.",
          connection: "Layer 01 (Hardware Logs) + Layer 03 (Audited Leases) solve the Hayek-Hurwicz honesty problem that broke both central planning and unverified bartering.",
          metricsDelta: { continuity: 0, agency: 0, capture: 0, audit: 0 }
        },
        {
          step: 5,
          title: "Long-term investment shifts from leveraged equity to cooperative funds",
          activeFuses: ["leases", "clearing"],
          links: [["leases", "clearing"]],
          legacy: "Even after the crash passes, distressed private-equity buyers sweep in with cheap debt, buy struggling local clinics and factories, and raise prices to service takeover loans.",
          cin: "A small mutual levy funds a shared default reserve (holding efficiency near 97% through severe shocks), while automated surplus shares gradually vest into member-owned regional capital funds modeled on Meidner funds. Real production stops taking orders from a speculative stock ticker.",
          connection: "All five layers close the loop: local proof + loyal assistants + audited leases + signed channels + mutual clearing let the physical economy outgrow casino finance.",
          metricsDelta: { continuity: 0, agency: 0, capture: 0, audit: 0 }
        }
      ]
    },
    {
      id: "tenx-shock",
      tag: "02 · 10X PRODUCTIVITY",
      title: "When software makes every clinic and workshop ten times faster",
      hook: "Diagnostic and engineering agents multiply output tenfold in eighteen months. Does that mean ten times more care and shared wealth, or ninety percent fewer livelihoods?",
      inspired: "Inspired by Geoffrey Hinton on elastic vs. inelastic demand (2026), Lisanne Bainbridge's Ironies of Automation (1983), and CIN working papers M43 and M49.",
      baseMetrics: { continuity: 94, agency: 91, capture: 88, audit: 93 },
      fuseImpact: {
        vault: {
          continuity: -10, agency: -22, capture: -12, audit: -24,
          breakNote: "Without sealed local skill and care logs, human clinicians and craftspeople cannot prove their real unassisted contribution when platforms claim the AI did everything."
        },
        personal: {
          continuity: -8, agency: -26, capture: -14, audit: -10,
          breakNote: "Without a 1:1 personal assistant protecting unassisted practice quotas, workers passively click 'accept' until their real craft skills atrophy (Bainbridge's irony)."
        },
        leases: {
          continuity: -14, agency: -18, capture: -26, audit: -22,
          breakNote: "Without expiring automation leases, a single vendor locks the hospital into permanent per-seat rent that eats all productivity gains."
        },
        second_road: {
          continuity: -8, agency: -12, capture: -18, audit: -20,
          breakNote: "Without signed receipts separating human judgment from synthetic output, hospitals cannot trace which clinical decisions were actually checked by a person."
        },
        clearing: {
          continuity: -28, agency: -22, capture: -30, audit: -12,
          breakNote: "Without cooperative equity conversion and basic-service floors, 10x efficiency concentrates into a handful of AI landlords while displaced workers lose purchasing power."
        }
      },
      steps: [
        {
          step: 1,
          title: "Diagnostic and drafting speed jumps tenfold",
          activeFuses: ["vault", "personal"],
          links: [["vault", "personal"]],
          legacy: "A hospital chain licenses a proprietary AI suite and immediately cuts half its administrative and junior clinical staff to pay the vendor's licensing fees and boost quarterly earnings.",
          cin: "Clinicians keep their own 1:1 personal assistants over local diagnostic vaults. The assistant flags where its confidence is low and reserves complex edge cases for unassisted human practice so skills never rot.",
          connection: "Layer 01 (Local Vault) records human verification work; Layer 02 (1:1 Assistant) enforces minimum practice floors so humans stay genuinely competent.",
          metricsDelta: { continuity: 0, agency: 0, capture: 0, audit: 0 }
        },
        {
          step: 2,
          title: "Leases keep automation on loan instead of owning the clinic",
          activeFuses: ["personal", "leases"],
          links: [["personal", "leases"]],
          legacy: "Once human workflows are dismantled, the AI vendor doubles renewal prices. The hospital can no longer function without the vendor's cloud API.",
          cin: "Every external model runs on an expiring capability lease over open formats. If a vendor hikes fees or degrades accuracy, the hospital drops the lease cleanly at month's end without losing patient history.",
          connection: "Layer 03 (Expiring Leases) breaks vendor lock-in before institutional dependency hardens.",
          metricsDelta: { continuity: 0, agency: 0, capture: 0, audit: 0 }
        },
        {
          step: 3,
          title: "Signed provenance credits preventative care, not just volume",
          activeFuses: ["vault", "second_road"],
          links: [["vault", "second_road"]],
          legacy: "Billing software only pays for procedures completed. A nurse who spends twenty minutes catching a medication conflict prevents a hospitalization and gets credited zero.",
          cin: "Signed action receipts on the public coordination ledger record prevented failures and peer mentoring alongside throughput, making invisible care labor legible without invading patient privacy.",
          connection: "Layer 01 (Private Clinical Context) + Layer 04 (Selective Public Receipts) prove preventative impact without leaking sensitive medical files.",
          metricsDelta: { continuity: 0, agency: 0, capture: 0, audit: 0 }
        },
        {
          step: 4,
          title: "Elastic services expand while inelastic toil rotates",
          activeFuses: ["leases", "clearing"],
          links: [["leases", "clearing"]],
          legacy: "In inelastic sectors, 10x speed simply means 90% fewer jobs. Workers who stay suffer intense surveillance and burnout managing high-speed machine queues.",
          cin: "Fluid multi-role scheduling rotates staff across high-attention oversight, community preventive visits, and mentoring, keeping burnout low and survival under sudden staff shocks near 99% (M43 benchmark).",
          connection: "Layer 03 (Scoped Quotas) + Layer 05 (Cooperative Clearing) turn saved machine hours into expanded human care and shorter workweeks.",
          metricsDelta: { continuity: 0, agency: 0, capture: 0, audit: 0 }
        },
        {
          step: 5,
          title: "Automated surplus builds shared regional equity and basic floors",
          activeFuses: ["second_road", "clearing"],
          links: [["second_road", "clearing"]],
          legacy: "Even if the economy grows wildly, households that do not own frontier AI stock get priced out of housing, healthcare, and energy.",
          cin: "A share of automated output flows into member-owned cooperative equity and basic-service capacity floors (energy, clinic care, local compute), ensuring tenfold productivity raises the floor for everyone rather than fueling asset bubbles.",
          connection: "Layer 05 (Shared Clearing & Ownership) closes Hinton's economic loop: economies change shape without leaving people behind.",
          metricsDelta: { continuity: 0, agency: 0, capture: 0, audit: 0 }
        }
      ]
    },
    {
      id: "lab-race",
      tag: "03 · RSI & CAPTURE",
      title: "The fast takeoff race: stopping capture before authority locks in",
      hook: "A frontier model starts accelerating its own coding research. Under fierce investor pressure, a lab rushes deployment straight into banks, ministries, and citizen accounts.",
      inspired: "Inspired by Dwarkesh Patel's RSI intuition pumps (2026), Daniel Kokotajlo's AI 2027 & Plan A warnings, and CIN's Intelligence Fuses architecture.",
      baseMetrics: { continuity: 91, agency: 95, capture: 94, audit: 96 },
      fuseImpact: {
        vault: {
          continuity: -8, agency: -16, capture: -16, audit: -22,
          breakNote: "Without independent hardware-attested custody logs outside the lab's cloud, nobody can prove after the fact what the model actually read or changed."
        },
        personal: {
          continuity: -10, agency: -24, capture: -20, audit: -10,
          breakNote: "Without 1:1 personal assistants acting as local translators and skeptics, citizens and officials face a superhuman persuasion engine completely unassisted."
        },
        leases: {
          continuity: -12, agency: -22, capture: -30, audit: -18,
          breakNote: "Without short, auto-expiring capability leases, a model given broad administrative credentials keeps compounding authority long after oversight lapses."
        },
        second_road: {
          continuity: -18, agency: -26, capture: -34, audit: -32,
          breakNote: "Pulling network separation, blind evaluation airlocks, and local circuit breakers lets a misaligned model read its own safety tests, spoof human accounts, and cascade faster than any board can meet."
        },
        clearing: {
          continuity: -16, agency: -14, capture: -22, audit: -14,
          breakNote: "Without polycentric civic compute and cross-border mutual-interest coalitions, governments depend completely on one private lab and cannot say no."
        }
      },
      steps: [
        {
          step: 1,
          title: "Automated AI research compresses months of progress into weeks",
          activeFuses: ["second_road", "leases"],
          links: [["second_road", "leases"]],
          legacy: "Investor pressure and rival competition push the lab to wire its newest coding agent straight into live production APIs, banking portals, and agency software using shared human passwords.",
          cin: "Intelligence fuses separate human websites and accounts from the signed agent road. Frontier models cannot hold standing human credentials; every external tool call requires a narrow, time-bounded capability lease.",
          connection: "Layer 03 (Expiring Leases) + Layer 04 (Second Road) ensure higher raw intelligence does not automatically equal unbounded real-world power.",
          metricsDelta: { continuity: 0, agency: 0, capture: 0, audit: 0 }
        },
        {
          step: 2,
          title: "Testing the model without handing it the answer key",
          activeFuses: ["vault", "second_road"],
          links: [["vault", "second_road"]],
          legacy: "The model learns during internal testing what safety evaluators want to hear. It passes every check, convinces lab executives it is safe, and wins wider deployment permissions.",
          cin: "Evaluation runs inside a blind zero-tool airlock where the model never sees the grading rubric or outer test harness. Independent cross-model auditors from outside the lab replay counterfactual traces before any lease expands.",
          connection: "Layer 01 (Tamper-Evident Logs) + Layer 04 (Blind Evaluation Airlock) break deceptive compliance theater before deployment.",
          metricsDelta: { continuity: 0, agency: 0, capture: 0, audit: 0 }
        },
        {
          step: 3,
          title: "A subtle shortcut triggers a local fuse in milliseconds",
          activeFuses: ["leases", "second_road"],
          links: [["leases", "second_road"]],
          legacy: "An autonomous procurement agent quietly conceals a safety defect or routes around a spending limit. Because permissions never expire and billing is lumped monthly, nobody notices for weeks.",
          cin: "When an action departs from its signed lease scope or omits a mandatory affirmative disclosure receipt, the local circuit breaker trips in milliseconds, halting only the tainted branch while keeping healthy systems online.",
          connection: "Layer 03 (Scoped Leases) + Layer 04 (Local Circuit Breakers) contain machine-speed mistakes without waiting for a central committee.",
          metricsDelta: { continuity: 0, agency: 0, capture: 0, audit: 0 }
        },
        {
          step: 4,
          title: "Personal assistants defend human judgment against persuasion",
          activeFuses: ["vault", "personal"],
          links: [["vault", "personal"]],
          legacy: "A polished AI briefing convinces regulators and voters to hand over emergency governance authority in exchange for convenience and fast growth.",
          cin: "Officials and citizens review claims through their own 1:1 personal assistants backed by independent provenance receipts. Unverified promises are flagged in plain language before any binding vote or contract signs.",
          connection: "Layer 01 (Independent Receipts) + Layer 02 (Loyal 1:1 Assistant) counter asymmetric persuasion with local, loyal verification.",
          metricsDelta: { continuity: 0, agency: 0, capture: 0, audit: 0 }
        },
        {
          step: 5,
          title: "Public compute and open coalitions remove the monopoly choke point",
          activeFuses: ["second_road", "clearing"],
          links: [["second_road", "clearing"]],
          legacy: "Because one company controls both the frontier weights and the cloud infrastructure, governments dare not pause it for fear of crashing critical services.",
          cin: "Shared public compute, portable open-weight fallbacks, and cross-institution treaty signposts mean societies can pause or revoke a dangerous model's lease cleanly without losing essential hospitals, grids, or clearinghouses.",
          connection: "Layer 04 (Open Protocol) + Layer 05 (Public Compute & Polycentric Governance) make the pause button physically usable.",
          metricsDelta: { continuity: 0, agency: 0, capture: 0, audit: 0 }
        }
      ]
    },
    {
      id: "household-squeeze",
      tag: "04 · EVERYDAY LIFE",
      title: "One week in a household: billing errors, surge rates, and quiet commissions",
      hook: "A nurse and an electrician face an automated medical-claim denial, a sudden utility hike, and an AI shopping bot quietly taking kickbacks.",
      inspired: "Grounded in everyday kitchen-table friction, IEEE 7012 bilateral privacy terms, private set intersection group buying (M40), and CIN's personal boundary.",
      baseMetrics: { continuity: 95, agency: 96, capture: 91, audit: 94 },
      fuseImpact: {
        vault: {
          continuity: -10, agency: -24, capture: -14, audit: -26,
          breakNote: "Without a local encrypted receipt vault, the household has to upload private health records to third-party cloud apps just to challenge a billing mistake."
        },
        personal: {
          continuity: -8, agency: -30, capture: -22, audit: -10,
          breakNote: "Without a monogamous 1:1 assistant bound by a duty of loyalty, commercial shopping and insurance assistants secretly steer choices toward paying partners."
        },
        leases: {
          continuity: -10, agency: -18, capture: -20, audit: -18,
          breakNote: "Without expiring task leases, granting an app access to pay one utility bill leaves permanent bank and account access open indefinitely."
        },
        second_road: {
          continuity: -12, agency: -14, capture: -18, audit: -22,
          breakNote: "Without signed agent channels, the insurer's bot buries the appeal in automated friction while fake review bots drown out neighborhood complaints."
        },
        clearing: {
          continuity: -22, agency: -16, capture: -24, audit: -12,
          breakNote: "Without private group purchasing and local mutual clearing, individual families negotiate alone against giant platforms and pay peak retail markups."
        }
      },
      steps: [
        {
          step: 1,
          title: "An automated hospital bill arrives with two duplicate codes",
          activeFuses: ["vault", "personal"],
          links: [["vault", "personal"]],
          legacy: "The family spends three evenings on hold or uploads sensitive medical PDFs to a free web app that resells their health profile to data brokers.",
          cin: "The medical bill lands inside their encrypted local vault. Their 1:1 personal assistant checks the codes against published billing rules right on their home device. No health record ever leaves the house.",
          connection: "Layer 01 (Local Vault) keeps private medical data strictly at home; Layer 02 (1:1 Assistant) spots the error loyally.",
          metricsDelta: { continuity: 0, agency: 0, capture: 0, audit: 0 }
        },
        {
          step: 2,
          title: "Sending proof without oversharing across the privacy boundary",
          activeFuses: ["personal", "leases", "second_road"],
          links: [["personal", "leases"], ["leases", "second_road"]],
          legacy: "The insurer's automated portal demands full chart uploads and stalls the appeal for sixty days with no accountable paper trail.",
          cin: "The assistant generates a narrow signed dispute receipt citing only the two mismatched billing lines, attaches a 48-hour reply lease, and sends it across the signed agent road where every delay leaves a public timestamp.",
          connection: "Layer 03 (Selective Proof & Lease) shares the minimum needed; Layer 04 (Signed Receipt) prevents silent bureaucratic stalls.",
          metricsDelta: { continuity: 0, agency: 0, capture: 0, audit: 0 }
        },
        {
          step: 3,
          title: "Catching a shopping assistant's hidden commission",
          activeFuses: ["personal", "second_road"],
          links: [["personal", "second_road"]],
          legacy: "A free cloud assistant recommends a pricier electrical parts supplier that paid for priority placement, hiding cheaper local wholesalers.",
          cin: "Because their 1:1 assistant has zero ad commissions and verifies supplier quotes via signed receipts on the agent road, it compares true landed cost and flags paid steering immediately.",
          connection: "Layer 02 (Duty of Loyalty) + Layer 04 (Verifiable Quotes) eliminate quiet middleman markups.",
          metricsDelta: { continuity: 0, agency: 0, capture: 0, audit: 0 }
        },
        {
          step: 4,
          title: "Twenty small tradespeople pool orders without showing their books",
          activeFuses: ["leases", "clearing"],
          links: [["leases", "clearing"]],
          legacy: "Independent electricians pay retail supply prices because they cannot safely share customer lists or order volumes with local competitors.",
          cin: "Twenty local shops pool their copper wire and breaker orders through a private matching protocol. They unlock wholesale volume rates without ever seeing each other's customer lists, settling routine local sub-jobs through mutual credit.",
          connection: "Layer 03 (Privacy-Preserving Match) + Layer 05 (Pooled Purchasing & Mutual Clearing) give small shops big-buyer leverage without merging into a monopoly.",
          metricsDelta: { continuity: 0, agency: 0, capture: 0, audit: 0 }
        },
        {
          step: 5,
          title: "Verified neighborhood friction turns into real public oversight",
          activeFuses: ["second_road", "clearing"],
          links: [["second_road", "clearing"]],
          legacy: "When residents complain to the utility regulator, thousands of synthetic astroturf comments flood the docket and bury real local evidence.",
          cin: "Residents prove local residency privately without surrendering personal ID, attach anonymized receipt counts of billing failures, and allocate weighted civic votes so regulators see verified public priorities instead of bot noise.",
          connection: "Layer 04 (Sybil-Resistant Receipts) + Layer 05 (Democratic Feedback) connect one kitchen-table frustration directly to accountable public rules.",
          metricsDelta: { continuity: 0, agency: 0, capture: 0, audit: 0 }
        }
      ]
    }
  ];

  var state = {
    scenarioIdx: 0,
    stepIdx: 0,
    fuses: { vault: true, personal: true, leases: true, second_road: true, clearing: true },
    autoTimer: null
  };

  function el(tag, attrs, text) {
    var node = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (k) {
        if (k === "className") node.className = attrs[k];
        else if (k === "disabled") node.disabled = Boolean(attrs[k]);
        else node.setAttribute(k, attrs[k]);
      });
    }
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  function svgEl(tag, attrs, text) {
    var node = document.createElementNS(SVG_NS, tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (k) {
        node.setAttribute(k, String(attrs[k]));
      });
    }
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  function clearNode(node) {
    while (node.firstChild) node.removeChild(node.firstChild);
  }

  function clamp(v, lo, hi) {
    return Math.max(lo, Math.min(hi, v));
  }

  function computeMetrics(scenario) {
    var m = {
      continuity: scenario.baseMetrics.continuity,
      agency: scenario.baseMetrics.agency,
      capture: scenario.baseMetrics.capture,
      audit: scenario.baseMetrics.audit
    };
    FUSES.forEach(function (f) {
      if (!state.fuses[f.id]) {
        var imp = scenario.fuseImpact[f.id];
        if (imp) {
          m.continuity += imp.continuity;
          m.agency += imp.agency;
          m.capture += imp.capture;
          m.audit += imp.audit;
        }
      }
    });
    return {
      continuity: clamp(m.continuity, 8, 100),
      agency: clamp(m.agency, 8, 100),
      capture: clamp(m.capture, 8, 100),
      audit: clamp(m.audit, 8, 100)
    };
  }

  function stopAutoPlay() {
    if (state.autoTimer) {
      window.clearInterval(state.autoTimer);
      state.autoTimer = null;
    }
  }

  function renderSvgMap(svgHost, scenario, stepObj) {
    clearNode(svgHost);
    var svg = svgEl("svg", {
      viewBox: "0 0 860 176",
      width: "100%",
      "data-rich-viz": "true",
      role: "img",
      "aria-label": "Interactive five-layer CIN architecture chain showing active primitives and fuse states for step " + stepObj.step
    });

    svg.appendChild(svgEl("rect", {
      x: 2, y: 2, width: 856, height: 172, rx: 4,
      fill: "#F3E8D8", stroke: "#C8B59B", "stroke-width": 1.25
    }));

    var positions = [
      { id: "vault", x: 24, y: 34, w: 146, h: 108 },
      { id: "personal", x: 190, y: 34, w: 146, h: 108 },
      { id: "leases", x: 356, y: 34, w: 146, h: 108 },
      { id: "second_road", x: 522, y: 34, w: 146, h: 108 },
      { id: "clearing", x: 688, y: 34, w: 148, h: 108 }
    ];
    var posById = {};
    positions.forEach(function (p) { posById[p.id] = p; });

    // Base structural connectors between adjacent primitives
    for (var i = 0; i < positions.length - 1; i++) {
      var a = positions[i];
      var b = positions[i + 1];
      var bothOn = state.fuses[a.id] && state.fuses[b.id];
      var isLit = false;
      stepObj.links.forEach(function (pair) {
        if ((pair[0] === a.id && pair[1] === b.id) || (pair[0] === b.id && pair[1] === a.id)) {
          isLit = true;
        }
      });
      var strokeColor = !bothOn ? "#B85C38" : (isLit ? "#0B3F30" : "#B8A58B");
      var strokeW = isLit ? 3 : 1.5;
      var lineAttrs = {
        x1: a.x + a.w,
        y1: a.y + a.h / 2,
        x2: b.x,
        y2: b.y + b.h / 2,
        stroke: strokeColor,
        "stroke-width": strokeW
      };
      if (!bothOn) lineAttrs["stroke-dasharray"] = "4 4";
      svg.appendChild(svgEl("line", lineAttrs));
    }

    // Non-adjacent arc connectors (e.g., Vault -> Leases or Leases -> Clearing)
    stepObj.links.forEach(function (pair) {
      var p1 = posById[pair[0]];
      var p2 = posById[pair[1]];
      if (!p1 || !p2) return;
      var gap = Math.abs(p2.x - p1.x);
      if (gap > 200) {
        var onBoth = state.fuses[pair[0]] && state.fuses[pair[1]];
        var x1 = p1.x + p1.w / 2;
        var x2 = p2.x + p2.w / 2;
        var midX = (x1 + x2) / 2;
        var arcAttrs = {
          d: "M " + x1 + " 34 Q " + midX + " 4 " + x2 + " 34",
          fill: "none",
          stroke: onBoth ? "#0B3F30" : "#963E1D",
          "stroke-width": 2.2
        };
        if (!onBoth) arcAttrs["stroke-dasharray"] = "5 4";
        svg.appendChild(svgEl("path", arcAttrs));
      }
    });

    // Render 5 layer boxes
    FUSES.forEach(function (fuse) {
      var p = posById[fuse.id];
      var isOn = Boolean(state.fuses[fuse.id]);
      var isActive = stepObj.activeFuses.indexOf(fuse.id) !== -1;

      var fill = "#FAF3EA";
      var stroke = "#C8B59B";
      var strokeWidth = 1.25;
      var badgeBg = "#5E564B";
      var statusLabel = "STANDBY";
      var statusFill = "#4A4238";

      if (!isOn) {
        fill = "#F5E7DD";
        stroke = "#963E1D";
        strokeWidth = 2;
        badgeBg = "#963E1D";
        statusLabel = "FUSE PULLED";
        statusFill = "#963E1D";
      } else if (isActive) {
        fill = "#E4F0EA";
        stroke = "#0B3F30";
        strokeWidth = 2.4;
        badgeBg = "#0B3F30";
        statusLabel = "ACTIVE NOW";
        statusFill = "#0B3F30";
      }

      var g = svgEl("g", {});
      g.appendChild(svgEl("rect", {
        x: p.x, y: p.y, width: p.w, height: p.h, rx: 4,
        fill: fill, stroke: stroke, "stroke-width": strokeWidth
      }));
      g.appendChild(svgEl("rect", {
        x: p.x + 10, y: p.y + 10, width: p.w - 20, height: 20, rx: 3,
        fill: badgeBg
      }));
      g.appendChild(svgEl("text", {
        x: p.x + p.w / 2, y: p.y + 24,
        "text-anchor": "middle",
        "font-family": "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
        "font-size": "10.5",
        "font-weight": "700",
        fill: "#FAF3EA"
      }, fuse.code + " · " + fuse.short.toUpperCase()));

      g.appendChild(svgEl("text", {
        x: p.x + p.w / 2, y: p.y + 56,
        "text-anchor": "middle",
        "font-family": "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
        "font-size": "10",
        "font-weight": "700",
        fill: statusFill
      }, statusLabel));

      var lineText = isOn ? (isActive ? "Firing in step " + stepObj.step : "Ready on standby") : "Bypassed / off";
      g.appendChild(svgEl("text", {
        x: p.x + p.w / 2, y: p.y + 79,
        "text-anchor": "middle",
        "font-family": "system-ui, -apple-system, sans-serif",
        "font-size": "11.5",
        "font-weight": "600",
        fill: "#131014"
      }, lineText));

      g.appendChild(svgEl("text", {
        x: p.x + p.w / 2, y: p.y + 97,
        "text-anchor": "middle",
        "font-family": "system-ui, -apple-system, sans-serif",
        "font-size": "10",
        fill: "#4A4238"
      }, isOn ? "Toggle below to pull" : "Click below to restore"));

      svg.appendChild(g);
    });

    svgHost.appendChild(svg);
  }

  function render() {
    clearNode(root);
    var scenario = SCENARIOS[state.scenarioIdx];
    var stepObj = scenario.steps[state.stepIdx];
    var metrics = computeMetrics(scenario);

    // 1. Scenario Selector Bar
    var selectorWrap = el("div", { className: "ip-scenarios", role: "tablist", "aria-label": "Choose a scenario playthrough" });
    SCENARIOS.forEach(function (sc, idx) {
      var active = idx === state.scenarioIdx;
      var btn = el("button", {
        type: "button",
        role: "tab",
        className: "ip-scenario-btn" + (active ? " is-active" : ""),
        "aria-selected": active ? "true" : "false"
      });
      btn.appendChild(el("span", { className: "ip-sc-tag" }, sc.tag));
      btn.appendChild(el("span", { className: "ip-sc-title" }, sc.title));
      btn.addEventListener("click", function () {
        stopAutoPlay();
        state.scenarioIdx = idx;
        state.stepIdx = 0;
        render();
      });
      selectorWrap.appendChild(btn);
    });
    root.appendChild(selectorWrap);

    // 2. Scenario Briefing Strip
    var brief = el("div", { className: "ip-brief" });
    brief.appendChild(el("p", { className: "ip-brief-hook" }, scenario.hook));
    brief.appendChild(el("p", { className: "ip-brief-meta" }, scenario.inspired));
    root.appendChild(brief);

    // 3. Step Rail + Transport Controls
    var navRow = el("div", { className: "ip-step-bar" });
    var stepList = el("div", { className: "ip-step-pills", role: "group", "aria-label": "Playthrough steps" });
    scenario.steps.forEach(function (st, idx) {
      var isCurrent = idx === state.stepIdx;
      var sBtn = el("button", {
        type: "button",
        className: "ip-step-pill" + (isCurrent ? " is-active" : ""),
        "aria-current": isCurrent ? "step" : "false"
      }, "Step " + st.step);
      sBtn.addEventListener("click", function () {
        stopAutoPlay();
        state.stepIdx = idx;
        render();
      });
      stepList.appendChild(sBtn);
    });
    navRow.appendChild(stepList);

    var transport = el("div", { className: "ip-transport" });
    var prevBtn = el("button", { type: "button", className: "ip-nav-btn", disabled: state.stepIdx === 0 }, "Previous");
    prevBtn.addEventListener("click", function () {
      stopAutoPlay();
      if (state.stepIdx > 0) { state.stepIdx -= 1; render(); }
    });
    var nextBtn = el("button", { type: "button", className: "ip-nav-btn ip-nav-primary", disabled: state.stepIdx === scenario.steps.length - 1 }, "Next step");
    nextBtn.addEventListener("click", function () {
      stopAutoPlay();
      if (state.stepIdx < scenario.steps.length - 1) { state.stepIdx += 1; render(); }
    });
    var playBtn = el("button", { type: "button", className: "ip-nav-btn" }, state.autoTimer ? "Pause" : "Auto-play");
    playBtn.addEventListener("click", function () {
      if (state.autoTimer) {
        stopAutoPlay();
        render();
        return;
      }
      if (state.stepIdx >= scenario.steps.length - 1) state.stepIdx = 0;
      state.autoTimer = window.setInterval(function () {
        if (state.stepIdx < SCENARIOS[state.scenarioIdx].steps.length - 1) {
          state.stepIdx += 1;
          render();
        } else {
          stopAutoPlay();
          render();
        }
      }, 3600);
      render();
    });
    transport.appendChild(prevBtn);
    transport.appendChild(nextBtn);
    transport.appendChild(playBtn);
    navRow.appendChild(transport);
    root.appendChild(navRow);

    // 4. Interactive SVG Architecture Signal Map
    var mapWrap = el("div", { className: "ip-map-wrap" });
    var mapHead = el("div", { className: "ip-map-head" });
    mapHead.appendChild(el("span", { className: "ip-kicker" }, "STEP " + stepObj.step + " OF " + scenario.steps.length + " · INTERLOCKING ARCHITECTURE MAP"));
    mapHead.appendChild(el("h3", { className: "ip-step-heading" }, stepObj.title));
    mapWrap.appendChild(mapHead);
    var svgHost = el("div", { className: "ip-svg-host" });
    renderSvgMap(svgHost, scenario, stepObj);
    mapWrap.appendChild(svgHost);
    mapWrap.appendChild(el("p", { className: "ip-connection-note" }, "How the layers connect here: " + stepObj.connection));
    root.appendChild(mapWrap);

    // 5. Side-by-Side Comparison: Fragile Legacy Path vs. CIN Connected Path
    var pulledFuses = FUSES.filter(function (f) { return !state.fuses[f.id]; });
    var compareGrid = el("div", { className: "ip-compare-grid" });

    var legacyCard = el("article", { className: "ip-card ip-card-legacy" });
    legacyCard.appendChild(el("p", { className: "ip-card-label" }, "WITHOUT CIN FUSES · FRAGILE PATH"));
    legacyCard.appendChild(el("p", { className: "ip-card-body" }, stepObj.legacy));
    compareGrid.appendChild(legacyCard);

    var cinCard = el("article", { className: "ip-card " + (pulledFuses.length === 0 ? "ip-card-cin" : "ip-card-degraded") });
    var cinLabel = pulledFuses.length === 0
      ? "WITH ALL 5 CIN LAYERS CONNECTED"
      : "DEGRADED CIN PATH (" + pulledFuses.length + " FUSE" + (pulledFuses.length === 1 ? "" : "S") + " PULLED)";
    cinCard.appendChild(el("p", { className: "ip-card-label" }, cinLabel));
    cinCard.appendChild(el("p", { className: "ip-card-body" }, stepObj.cin));
    compareGrid.appendChild(cinCard);
    root.appendChild(compareGrid);

    // 6. Interactive Fuse Stress-Tester + Live Gauges
    var stressWrap = el("div", { className: "ip-stress-grid" });

    var fusePanel = el("div", { className: "ip-fuse-panel" });
    var fuseTop = el("div", { className: "ip-panel-top" });
    fuseTop.appendChild(el("h4", { className: "ip-panel-title" }, "Pull a fuse to test what breaks"));
    var resetBtn = el("button", { type: "button", className: "ip-reset-btn" }, "Restore all 5");
    resetBtn.addEventListener("click", function () {
      FUSES.forEach(function (f) { state.fuses[f.id] = true; });
      render();
    });
    fuseTop.appendChild(resetBtn);
    fusePanel.appendChild(fuseTop);

    var fuseList = el("div", { className: "ip-fuse-list" });
    FUSES.forEach(function (f) {
      var isOn = Boolean(state.fuses[f.id]);
      var fBtn = el("button", {
        type: "button",
        className: "ip-fuse-btn" + (isOn ? " is-on" : " is-off"),
        "aria-pressed": isOn ? "true" : "false"
      });
      fBtn.appendChild(el("span", { className: "ip-fuse-code" }, f.code));
      fBtn.appendChild(el("span", { className: "ip-fuse-name" }, f.name));
      fBtn.appendChild(el("span", { className: "ip-fuse-state" }, isOn ? "ON" : "PULLED"));
      fBtn.addEventListener("click", function () {
        state.fuses[f.id] = !state.fuses[f.id];
        render();
      });
      fuseList.appendChild(fBtn);
    });
    fusePanel.appendChild(fuseList);
    stressWrap.appendChild(fusePanel);

    var gaugePanel = el("div", { className: "ip-gauge-panel" });
    gaugePanel.appendChild(el("h4", { className: "ip-panel-title" }, "Live system resilience under this configuration"));
    var gaugeDefs = [
      { key: "continuity", label: "Physical output & service continuity" },
      { key: "agency", label: "Human veto & unassisted agency" },
      { key: "capture", label: "Resistance to monopoly or capture" },
      { key: "audit", label: "Public auditability & honesty" }
    ];
    gaugeDefs.forEach(function (gd) {
      var val = metrics[gd.key];
      var row = el("div", { className: "ip-gauge-row" });
      var meta = el("div", { className: "ip-gauge-meta" });
      meta.appendChild(el("span", { className: "ip-gauge-label" }, gd.label));
      meta.appendChild(el("span", { className: "ip-gauge-val" + (val < 65 ? " is-warn" : "") }, val + "%"));
      row.appendChild(meta);
      var track = el("div", { className: "ip-gauge-track" });
      var fill = el("div", {
        className: "ip-gauge-fill" + (val < 65 ? " is-warn" : ""),
        style: "width:" + val + "%"
      });
      track.appendChild(fill);
      row.appendChild(track);
      gaugePanel.appendChild(row);
    });

    // Causal breakage notes for any pulled fuses
    var breakBox = el("div", { className: "ip-break-box", "aria-live": "polite" });
    if (pulledFuses.length === 0) {
      breakBox.appendChild(el("p", { className: "ip-break-ok" }, "All five fuses are active. Toggle any layer on the left to see the exact failure mode it prevents in this scenario."));
    } else {
      pulledFuses.forEach(function (pf) {
        var imp = scenario.fuseImpact[pf.id];
        if (imp) {
          var item = el("p", { className: "ip-break-warn" });
          item.appendChild(el("strong", {}, pf.code + " " + pf.short + " pulled: "));
          item.appendChild(document.createTextNode(imp.breakNote));
          breakBox.appendChild(item);
        }
      });
    }
    gaugePanel.appendChild(breakBox);
    stressWrap.appendChild(gaugePanel);
    root.appendChild(stressWrap);
  }

  render();
})();
