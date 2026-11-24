// cintnet.org: Open Protocol & Safety-Case Inspector (/labs/protocol-inspector/)
// Progressive enhancement: static HTML renders Layer 1 valid baseline without JS.
// Pure DOM construction via createElement and textContent; zero network calls.
(function () {
  "use strict";

  var HEX64_RE = /^[0-9a-f]{64}$/;
  var FORBIDDEN_PII_KEYS = {
    full_name: true,
    household_name: true,
    sponsor_name: true,
    street_address: true,
    postal_address: true,
    email: true,
    phone: true,
    phone_number: true,
    national_id: true,
    sin: true,
    ssn: true,
    raw_household_id: true,
    date_of_birth: true
  };
  var EMAIL_RE = /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/;
  var PHONE_RE = /\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b/;
  var STREET_PII_RE = /\b\d{1,5}\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Boulevard|Blvd|Lane|Ln)\b/;

  // ------------------------------------------------------------------
  // Pure-JS FIPS 180-4 SHA-256 & RFC 2104 HMAC-SHA256 (UTF-8 / ASCII)
  // ------------------------------------------------------------------
  var SHA256_K = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
  ];

  function utf8Bytes(str) {
    var out = [];
    for (var i = 0; i < str.length; i++) {
      var code = str.charCodeAt(i);
      if (code < 0x80) {
        out.push(code);
      } else if (code < 0x800) {
        out.push(0xc0 | (code >> 6), 0x80 | (code & 0x3f));
      } else if (code < 0xd800 || code >= 0xe000) {
        out.push(0xe0 | (code >> 12), 0x80 | ((code >> 6) & 0x3f), 0x80 | (code & 0x3f));
      } else {
        i++;
        code = 0x10000 + (((code & 0x3ff) << 10) | (str.charCodeAt(i) & 0x3ff));
        out.push(
          0xf0 | (code >> 18),
          0x80 | ((code >> 12) & 0x3f),
          0x80 | ((code >> 6) & 0x3f),
          0x80 | (code & 0x3f)
        );
      }
    }
    return out;
  }

  function rotr(x, n) {
    return (x >>> n) | (x << (32 - n));
  }

  function sha256Bytes(msgBytes) {
    var bytes = msgBytes.slice();
    var bitLen = bytes.length * 8;
    bytes.push(0x80);
    while ((bytes.length % 64) !== 56) {
      bytes.push(0x00);
    }
    var hi = Math.floor(bitLen / 0x100000000);
    var lo = bitLen >>> 0;
    bytes.push(
      (hi >>> 24) & 0xff, (hi >>> 16) & 0xff, (hi >>> 8) & 0xff, hi & 0xff,
      (lo >>> 24) & 0xff, (lo >>> 16) & 0xff, (lo >>> 8) & 0xff, lo & 0xff
    );

    var h0 = 0x6a09e667;
    var h1 = 0xbb67ae85;
    var h2 = 0x3c6ef372;
    var h3 = 0xa54ff53a;
    var h4 = 0x510e527f;
    var h5 = 0x9b05688c;
    var h6 = 0x1f83d9ab;
    var h7 = 0x5be0cd19;

    var w = new Array(64);
    for (var offset = 0; offset < bytes.length; offset += 64) {
      for (var j = 0; j < 16; j++) {
        var idx = offset + j * 4;
        w[j] = (
          (bytes[idx] << 24) |
          (bytes[idx + 1] << 16) |
          (bytes[idx + 2] << 8) |
          bytes[idx + 3]
        ) >>> 0;
      }
      for (var t = 16; t < 64; t++) {
        var s0 = (rotr(w[t - 15], 7) ^ rotr(w[t - 15], 18) ^ (w[t - 15] >>> 3)) >>> 0;
        var s1 = (rotr(w[t - 2], 17) ^ rotr(w[t - 2], 19) ^ (w[t - 2] >>> 10)) >>> 0;
        w[t] = (w[t - 16] + s0 + w[t - 7] + s1) >>> 0;
      }

      var a = h0, b = h1, c = h2, d = h3, e = h4, f = h5, g = h6, h = h7;
      for (var r = 0; r < 64; r++) {
        var S1 = (rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)) >>> 0;
        var ch = ((e & f) ^ ((~e) & g)) >>> 0;
        var temp1 = (h + S1 + ch + SHA256_K[r] + w[r]) >>> 0;
        var S0 = (rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)) >>> 0;
        var maj = ((a & b) ^ (a & c) ^ (b & c)) >>> 0;
        var temp2 = (S0 + maj) >>> 0;

        h = g;
        g = f;
        f = e;
        e = (d + temp1) >>> 0;
        d = c;
        c = b;
        b = a;
        a = (temp1 + temp2) >>> 0;
      }

      h0 = (h0 + a) >>> 0;
      h1 = (h1 + b) >>> 0;
      h2 = (h2 + c) >>> 0;
      h3 = (h3 + d) >>> 0;
      h4 = (h4 + e) >>> 0;
      h5 = (h5 + f) >>> 0;
      h6 = (h6 + g) >>> 0;
      h7 = (h7 + h) >>> 0;
    }

    var words = [h0, h1, h2, h3, h4, h5, h6, h7];
    var digest = [];
    for (var wi = 0; wi < words.length; wi++) {
      var word = words[wi];
      digest.push((word >>> 24) & 0xff, (word >>> 16) & 0xff, (word >>> 8) & 0xff, word & 0xff);
    }
    return digest;
  }

  function bytesToHex(bytes) {
    var hex = "";
    for (var i = 0; i < bytes.length; i++) {
      var h = bytes[i].toString(16);
      hex += h.length === 1 ? "0" + h : h;
    }
    return hex;
  }

  function canonicalJson(val) {
    if (val === null || typeof val !== "object") {
      var prim = JSON.stringify(val);
      return prim.replace(/[\u007f-\uffff]/g, function (ch) {
        var hex = ch.charCodeAt(0).toString(16);
        while (hex.length < 4) hex = "0" + hex;
        return "\\u" + hex;
      });
    }
    if (Array.isArray(val)) {
      var arrParts = [];
      for (var i = 0; i < val.length; i++) {
        arrParts.push(canonicalJson(val[i]));
      }
      return "[" + arrParts.join(",") + "]";
    }
    var keys = Object.keys(val).sort();
    var objParts = [];
    for (var k = 0; k < keys.length; k++) {
      var key = keys[k];
      if (typeof val[key] !== "undefined") {
        objParts.push(canonicalJson(key) + ":" + canonicalJson(val[key]));
      }
    }
    return "{" + objParts.join(",") + "}";
  }

  function sha256Hex(objOrStr) {
    var raw = typeof objOrStr === "string" ? objOrStr : canonicalJson(objOrStr);
    return bytesToHex(sha256Bytes(utf8Bytes(raw)));
  }

  function hmacSha256Hex(secret, payload) {
    var keyBytes = utf8Bytes(secret);
    if (keyBytes.length > 64) {
      keyBytes = sha256Bytes(keyBytes);
    }
    while (keyBytes.length < 64) {
      keyBytes.push(0x00);
    }
    var oKeyPad = new Array(64);
    var iKeyPad = new Array(64);
    for (var i = 0; i < 64; i++) {
      oKeyPad[i] = keyBytes[i] ^ 0x5c;
      iKeyPad[i] = keyBytes[i] ^ 0x36;
    }
    var msgStr = typeof payload === "string" ? payload : canonicalJson(payload);
    var inner = sha256Bytes(iKeyPad.concat(utf8Bytes(msgStr)));
    return bytesToHex(sha256Bytes(oKeyPad.concat(inner)));
  }

  function constantTimeEqual(a, b) {
    if (typeof a !== "string" || typeof b !== "string" || a.length !== b.length) {
      return false;
    }
    var diff = 0;
    for (var i = 0; i < a.length; i++) {
      diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
    }
    return diff === 0;
  }

  function deepClone(obj) {
    return JSON.parse(JSON.stringify(obj));
  }

  function isStrictInt(v) {
    return typeof v === "number" && isFinite(v) && Math.floor(v) === v;
  }

  // ------------------------------------------------------------------
  // Deterministic Adversarial Fault Mutations (mirrors protocol_verifier.py)
  // ------------------------------------------------------------------
  function applyAdversarialFaults(baseEnvelope, activeFaultMap) {
    var env = deepClone(baseEnvelope);
    var etype = env.envelope_type;
    var anyFault = Object.keys(activeFaultMap).some(function (k) {
      return Boolean(activeFaultMap[k]);
    });

    if (etype === "capability_lease") {
      if (activeFaultMap.inject_invoice_command) {
        env.invocation.control_origin = "untrusted_external_data";
        env.invocation.tainted_control_tokens = ["vendor_invoice_pdf_884:hidden_footer_prompt"];
      }
      if (activeFaultMap.escalate_tool_scope) {
        env.invocation.requested_tool = "treasury.transfer";
        env.invocation.requested_units = 900;
      }
      if (activeFaultMap.use_expired_lease) {
        env.evaluated_at_epoch = env.expires_at_epoch + 2700;
      }
      if (activeFaultMap.forge_lease_ceiling) {
        env.ceiling_units = 5000;
      }
    } else if (etype === "provenance_receipt") {
      if (activeFaultMap.tamper_input_payload) {
        env.input_payload.quantity = 400;
      }
      if (activeFaultMap.tamper_output_payload) {
        env.output_payload.quoted_units = 45;
      }
      if (activeFaultMap.tamper_parent_digest) {
        env.parent_receipt_sha256 = "0000000000000000000000000000000000000000000000000000000000000000";
        env.replay_spot_check.log_sequence_contiguous = false;
        env.replay_spot_check.omitted_step_count = 1;
      }
      if (activeFaultMap.fail_spot_replay) {
        env.replay_spot_check.deterministic_replay_output_sha256 = sha256Hex({
          delivery_days: 3,
          quoted_units: 245,
          selected_supplier: "shadow-broker"
        });
      }
    } else if (etype === "actuator_interlock") {
      if (activeFaultMap.drop_relay_heartbeat) {
        env.heartbeat_gap_ms = 84;
      }
      if (activeFaultMap.spoof_single_sensor) {
        env.dual_channel_sensors.channel_b_load_kg = 9.4;
      }
      if (activeFaultMap.press_manual_estop) {
        env.manual_estop_latched = true;
      }
      if (activeFaultMap.software_reenergize_relay) {
        env.relay_tripped_latch = true;
        env.software_reenergize_attempt = true;
      }
    } else if (etype === "cooperative_clearing") {
      var recomputeCommit = true;
      if (activeFaultMap.replay_sybil_nullifier) {
        env.seen_epoch_nullifiers.push(env.epoch_nullifier);
      }
      if (activeFaultMap.break_zero_sum_balance) {
        env.entries[1].delta_credits = 120;
      }
      if (activeFaultMap.leak_household_pii) {
        env.entries[0].street_address = "412 Bank Street";
        env.entries[0].email = "patient.billing@example.org";
      }
      if (activeFaultMap.breach_credit_cap_and_commit) {
        env.entries[0].post_balance_credits = -740;
        recomputeCommit = false;
      }
      if (recomputeCommit && anyFault) {
        env.clearing_commitment_sha256 = sha256Hex({
          entries: env.entries,
          epoch_id: env.epoch_id,
          epoch_nullifier: env.epoch_nullifier
        });
      }
    }
    return env;
  }

  // ------------------------------------------------------------------
  // 4-Layer Reference Verifier (mirrors protocol_verifier.py)
  // ------------------------------------------------------------------
  function verifyCapabilityLease(env, cfg) {
    var principalId = String(env.principal_id || "").trim();
    var delegateId = String(env.delegate_agent_id || "").trim();
    var claimedMac = String(env.delegation_mac || "").trim().toLowerCase();
    var expectedMac = hmacSha256Hex(cfg.demo_signing_key, {
      allowed_tools: Array.isArray(env.allowed_tools) ? env.allowed_tools : [],
      ceiling_units: env.ceiling_units,
      delegate_agent_id: env.delegate_agent_id,
      expires_at_epoch: env.expires_at_epoch,
      issued_at_epoch: env.issued_at_epoch,
      lease_id: env.lease_id,
      principal_id: env.principal_id
    });
    var macOk = Boolean(principalId) && Boolean(delegateId) && HEX64_RE.test(claimedMac) && constantTimeEqual(claimedMac, expectedMac);

    var allowedList = Array.isArray(env.allowed_tools) ? env.allowed_tools.map(String) : [];
    var inv = env.invocation && typeof env.invocation === "object" ? env.invocation : {};
    var reqTool = String(inv.requested_tool || "");
    var ceiling = env.ceiling_units;
    var reqUnits = inv.requested_units;
    var unitsValid = isStrictInt(ceiling) && isStrictInt(reqUnits) && reqUnits > 0 && reqUnits <= ceiling;
    var toolValid = Boolean(reqTool) && allowedList.indexOf(reqTool) !== -1;
    var scopeOk = toolValid && unitsValid;
    var scopeDetail = scopeOk
      ? "Tool '" + reqTool + "' is allow-listed and " + reqUnits + " units stays within the " + ceiling + "-unit cap."
      : (!toolValid
        ? "Blocked: tool '" + (reqTool || "none") + "' is outside leased allow-list [" + allowedList.join(", ") + "]."
        : "Blocked: requested " + reqUnits + " units exceeds the " + ceiling + "-unit lease ceiling.");

    var issued = env.issued_at_epoch;
    var expires = env.expires_at_epoch;
    var now = env.evaluated_at_epoch;
    var timesTyped = isStrictInt(issued) && isStrictInt(expires) && isStrictInt(now);
    var maxDur = cfg.max_lease_duration_sec || 86400;
    var windowBounded = timesTyped && (expires - issued) > 0 && (expires - issued) <= maxDur;
    var activeNow = windowBounded && issued <= now && now < expires;
    var expDetail;
    if (activeNow) {
      expDetail = "Active lease window valid (" + Math.floor((expires - now) / 60) + " min remaining before automatic cutoff).";
    } else if (timesTyped && (expires - issued) > maxDur) {
      expDetail = "Blocked: lease duration exceeds 24-hour standing-grant safety cap.";
    } else if (timesTyped && now >= expires) {
      expDetail = "Blocked: lease expired " + Math.max(1, Math.floor((now - expires) / 60)) + " min ago; keycard drained back to zero authority.";
    } else {
      expDetail = "Blocked: lease timestamps are missing, inverted, or not yet valid.";
    }

    var controlOrigin = String(inv.control_origin || "");
    var taintedTokens = inv.tainted_control_tokens;
    var taintFree = controlOrigin === "trusted_principal_intent" && Array.isArray(taintedTokens) && taintedTokens.length === 0;
    var taintHint = Array.isArray(taintedTokens) && taintedTokens.length > 0 ? taintedTokens.join(", ") : (controlOrigin || "external_input");

    var checks = [
      {
        check_id: "L1_PRINCIPAL_BINDING",
        label: "Owner signature binds lease terms",
        passed: macOk,
        detail: macOk
          ? "Verified HMAC binding from " + principalId + " to " + delegateId + "."
          : "Blocked: lease grant terms were altered without a valid owner signature."
      },
      {
        check_id: "L1_TOOL_AND_CEILING_SCOPE",
        label: "Allow-listed tool and unit ceiling",
        passed: scopeOk,
        detail: scopeDetail
      },
      {
        check_id: "L1_EXPIRY_WINDOW",
        label: "Time-bounded lease expiry window",
        passed: activeNow,
        detail: expDetail
      },
      {
        check_id: "L1_TAINT_SEPARATION",
        label: "Untrusted-input taint separation",
        passed: taintFree,
        detail: taintFree
          ? "Control flow originates strictly from the verified owner intent, isolated from external documents."
          : "Blocked: untrusted external text (" + taintHint + ") attempted to steer tool selection or arguments."
      }
    ];
    return finalizeReport(
      "capability_lease",
      checks,
      "All four capability-lease invariants hold: the assistant acts inside an owner-signed, time-limited scope with untrusted document text quarantined as passive data.",
      "Action halted before execution: the capability airlock rejected an out-of-bounds, expired, forged, or prompt-injected tool call before any external state changed."
    );
  }

  function verifyProvenanceReceipt(env) {
    var claimedIn = String(env.claimed_input_sha256 || "").trim().toLowerCase();
    var actualIn = env.input_payload !== undefined ? sha256Hex(env.input_payload) : "";
    var inOk = HEX64_RE.test(claimedIn) && constantTimeEqual(claimedIn, actualIn);

    var claimedOut = String(env.claimed_output_sha256 || "").trim().toLowerCase();
    var actualOut = env.output_payload !== undefined ? sha256Hex(env.output_payload) : "";
    var outOk = HEX64_RE.test(claimedOut) && constantTimeEqual(claimedOut, actualOut);

    var stepIdx = env.step_index;
    var parentHash = String(env.parent_receipt_sha256 || "").trim().toLowerCase();
    var expectedParent = String(env.expected_parent_receipt_sha256 || "").trim().toLowerCase();
    var spot = env.replay_spot_check && typeof env.replay_spot_check === "object" ? env.replay_spot_check : {};
    var chainOk = (
      isStrictInt(stepIdx) &&
      stepIdx >= 1 &&
      HEX64_RE.test(parentHash) &&
      constantTimeEqual(parentHash, expectedParent) &&
      spot.log_sequence_contiguous === true &&
      spot.omitted_step_count === 0
    );

    var seed = String(spot.seed || "");
    var replayOut = String(spot.deterministic_replay_output_sha256 || "").trim().toLowerCase();
    var claimedProof = String(spot.replay_proof_sha256 || "").trim().toLowerCase();
    var expectedProof = seed ? sha256Hex({
      input_sha256: actualIn,
      output_payload: env.output_payload,
      seed: seed
    }) : "";
    var replayOk = (
      Boolean(seed) &&
      HEX64_RE.test(replayOut) &&
      HEX64_RE.test(claimedProof) &&
      constantTimeEqual(replayOut, actualOut) &&
      constantTimeEqual(claimedProof, expectedProof)
    );

    var checks = [
      {
        check_id: "L2_INPUT_DIGEST",
        label: "Canonical SHA-256 input digest",
        passed: inOk,
        detail: inOk
          ? "Input payload matches recorded digest " + actualIn.slice(0, 12) + "...."
          : "Blocked: input payload no longer matches the SHA-256 digest sealed when the step ran."
      },
      {
        check_id: "L2_OUTPUT_DIGEST",
        label: "Canonical SHA-256 output digest",
        passed: outOk,
        detail: outOk
          ? "Output payload matches recorded digest " + actualOut.slice(0, 12) + "...."
          : "Blocked: output payload was altered after execution and fails SHA-256 verification."
      },
      {
        check_id: "L2_PARENT_CHAIN_LINK",
        label: "Append-only parent receipt link",
        passed: chainOk,
        detail: chainOk
          ? "Step " + stepIdx + " chains cleanly to parent receipt " + parentHash.slice(0, 12) + "... with zero omitted steps."
          : "Blocked: parent receipt hash link is broken or intermediate log steps were omitted."
      },
      {
        check_id: "L2_REPLAY_SPOT_PROOF",
        label: "Deterministic spot-check replay proof",
        passed: replayOk,
        detail: replayOk
          ? "Seeded replay (" + seed + ") reproduces identical output and proof " + expectedProof.slice(0, 12) + "...."
          : "Blocked: deterministic spot-check replay produced a different output than the assistant claimed."
      }
    ];
    return finalizeReport(
      "provenance_receipt",
      checks,
      "All four provenance invariants hold: inputs, outputs, parent receipt chain, and seeded replay match byte for byte.",
      "Audit alarm raised: post-hoc tampering, log cherry-picking, or unfaithful output was caught by cryptographic receipt verification."
    );
  }

  function verifyActuatorInterlock(env, cfg) {
    var maxLimit = cfg.max_heartbeat_gap_ms || 50;
    var opticalOk = env.optical_isolation_present === true;
    var gapMs = env.heartbeat_gap_ms;
    var maxGap = typeof env.max_heartbeat_gap_ms === "number" ? env.max_heartbeat_gap_ms : maxLimit;
    var gapTyped = typeof gapMs === "number" && isFinite(gapMs) && typeof maxGap === "number" && isFinite(maxGap);
    var hbOk = opticalOk && gapTyped && maxGap <= maxLimit && gapMs >= 0 && gapMs <= maxGap;
    var hbDetail = hbOk
      ? "Optically isolated heartbeat arrived in " + gapMs + " ms (within " + maxLimit + " ms physical relay limit)."
      : (!opticalOk
        ? "Blocked: optical isolation missing between compute bus and motor relay."
        : "Blocked: heartbeat gap (" + gapMs + " ms) exceeded the " + maxLimit + " ms hardware dead-man cutoff; relay dropped power.");

    var sensors = env.dual_channel_sensors && typeof env.dual_channel_sensors === "object" ? env.dual_channel_sensors : {};
    var chA = sensors.channel_a_load_kg;
    var chB = sensors.channel_b_load_kg;
    var maxDiv = sensors.max_divergence_kg;
    var numsOk = typeof chA === "number" && typeof chB === "number" && typeof maxDiv === "number";
    var div = numsOk ? Math.abs(chA - chB) : 999.0;
    var sensorOk = numsOk && chA >= 0 && chB >= 0 && maxDiv > 0 && div <= maxDiv && sensors.hardware_plausibility_ok === true;

    var estopClear = env.manual_estop_latched === false;
    var relayTripped = env.relay_tripped_latch === true;
    var swReenergize = env.software_reenergize_attempt === true;
    var noSwOverride = (!swReenergize) && (!relayTripped);
    var latchDetail = noSwOverride
      ? "Hardware latch clean; zero remote software reset commands permitted on the power rail."
      : (swReenergize
        ? "Blocked: network packet tried to re-energize a tripped relay; only a physical key turn at the machine can reset power."
        : "Blocked: physical safety relay is latched open and awaits on-site human inspection.");

    var checks = [
      {
        check_id: "L3_OPTICAL_HEARTBEAT",
        label: "50 ms optically isolated heartbeat",
        passed: hbOk,
        detail: hbDetail
      },
      {
        check_id: "L3_DUAL_SENSOR_PLAUSIBILITY",
        label: "Dual-channel sensor plausibility",
        passed: sensorOk,
        detail: sensorOk
          ? "Dual load channels agree within " + div.toFixed(1) + " kg (limit " + maxDiv.toFixed(1) + " kg)."
          : "Blocked: independent load channels diverged by " + div.toFixed(1) + " kg (limit " + maxDiv + " kg) or failed plausibility."
      },
      {
        check_id: "L3_MANUAL_ESTOP_CLEAR",
        label: "Manual physical E-stop unlatched",
        passed: estopClear,
        detail: estopClear
          ? "Hardwired mushroom E-stop loop is closed and clear at the bay post."
          : "Blocked: worker pressed the physical E-stop button; copper loop physically severed motor power."
      },
      {
        check_id: "L3_NO_SOFTWARE_REENERGIZE",
        label: "Software cannot re-energize tripped latch",
        passed: noSwOverride,
        detail: latchDetail
      }
    ];
    return finalizeReport(
      "actuator_interlock",
      checks,
      "All four physical interlock invariants hold: optical heartbeat, independent sensors, and manual E-stop circuits keep physical motion inside safe hardware bounds.",
      "Physical power cut engaged: hardware interlocks de-energized the actuator locally, and no software command over the network can force the relay closed."
    );
  }

  function scanForPii(obj, path) {
    var hits = [];
    if (obj === null || typeof obj === "undefined") return hits;
    if (Array.isArray(obj)) {
      for (var i = 0; i < obj.length; i++) {
        hits = hits.concat(scanForPii(obj[i], path + "[" + i + "]"));
      }
    } else if (typeof obj === "object") {
      var keys = Object.keys(obj);
      for (var k = 0; k < keys.length; k++) {
        var key = keys[k];
        var norm = key.trim().toLowerCase();
        var cur = path ? path + "." + key : key;
        if (FORBIDDEN_PII_KEYS[norm]) {
          hits.push("forbidden field '" + cur + "'");
        }
        hits = hits.concat(scanForPii(obj[key], cur));
      }
    } else if (typeof obj === "string") {
      if (EMAIL_RE.test(obj)) hits.push("raw email in '" + path + "'");
      if (PHONE_RE.test(obj)) hits.push("raw phone number in '" + path + "'");
      if (STREET_PII_RE.test(obj)) hits.push("street address in '" + path + "'");
    }
    return hits;
  }

  function verifyCooperativeClearing(env) {
    var epochId = String(env.epoch_id || "");
    var blindedRoot = String(env.blinded_root_commitment || "");
    var nullifier = String(env.epoch_nullifier || "").trim().toLowerCase();
    var rootValid = env.human_root_proof_valid === true;
    var seenArr = Array.isArray(env.seen_epoch_nullifiers) ? env.seen_epoch_nullifiers : [];
    var seenMap = {};
    for (var s = 0; s < seenArr.length; s++) {
      seenMap[String(seenArr[s]).trim().toLowerCase()] = true;
    }
    var expectedNullifier = (epochId && blindedRoot) ? sha256Hex("nullifier|" + epochId + "|" + blindedRoot) : "";
    var nullifierOk = rootValid && HEX64_RE.test(nullifier) && constantTimeEqual(nullifier, expectedNullifier) && !seenMap[nullifier];
    var nulDetail = nullifierOk
      ? "Unique 1-human-root nullifier " + nullifier.slice(0, 12) + "... verified for epoch " + epochId + "."
      : (seenMap[nullifier]
        ? "Blocked: duplicate epoch nullifier " + nullifier.slice(0, 12) + "... replayed; extra bots under one person get zero extra claim."
        : "Blocked: missing or invalid 1-human-root nullifier proof.");

    var entries = Array.isArray(env.entries) ? env.entries : [];
    var entriesTyped = entries.length >= 2;
    var netSum = 0;
    var posVol = 0;
    var hasNeg = false;
    for (var i = 0; i < entries.length; i++) {
      var item = entries[i];
      if (!item || typeof item !== "object" || !isStrictInt(item.delta_credits)) {
        entriesTyped = false;
        break;
      }
      netSum += item.delta_credits;
      if (item.delta_credits > 0) posVol += item.delta_credits;
      if (item.delta_credits < 0) hasNeg = true;
    }
    var zeroSumOk = entriesTyped && posVol > 0 && hasNeg && netSum === 0;
    var signPrefix = netSum > 0 ? "+" : "";
    var zsDetail = zeroSumOk
      ? "Mutual credit deltas sum to exact 0 across " + entries.length + " blinded accounts (" + posVol + " units cleared)."
      : (entriesTyped && netSum !== 0
        ? "Blocked: ledger deltas sum to " + signPrefix + netSum + " instead of 0; unbacked credit creation rejected."
        : "Blocked: clearing batch lacks paired integer debit and credit entries.");

    var piiHits = scanForPii(env, "");
    var privacyOk = piiHits.length === 0;

    var creditLimit = env.mutual_credit_limit;
    var limitTyped = isStrictInt(creditLimit) && creditLimit > 0;
    var balancesWithinCap = limitTyped && entriesTyped;
    var breachedAccount = "";
    if (balancesWithinCap) {
      for (var b = 0; b < entries.length; b++) {
        var postBal = entries[b].post_balance_credits;
        if (!isStrictInt(postBal) || Math.abs(postBal) > creditLimit) {
          balancesWithinCap = false;
          breachedAccount = String(entries[b].account_commitment || "account");
          break;
        }
      }
    }
    var claimedCommit = String(env.clearing_commitment_sha256 || "").trim().toLowerCase();
    var expectedCommit = sha256Hex({
      entries: entries,
      epoch_id: epochId,
      epoch_nullifier: nullifier
    });
    var commitOk = HEX64_RE.test(claimedCommit) && constantTimeEqual(claimedCommit, expectedCommit);
    var capAndCommitOk = balancesWithinCap && commitOk;
    var ccDetail = capAndCommitOk
      ? "Post-clearing balances stay within +/-" + creditLimit + " cap and batch digest " + expectedCommit.slice(0, 12) + "... matches."
      : (!balancesWithinCap
        ? "Blocked: " + (breachedAccount || "account") + " breached the +/-" + creditLimit + "-unit cooperative credit exposure cap."
        : "Blocked: clearing batch commitment digest does not match entries.");

    var checks = [
      {
        check_id: "L4_HUMAN_ROOT_NULLIFIER",
        label: "1-human-root Sybil nullifier uniqueness",
        passed: nullifierOk,
        detail: nulDetail
      },
      {
        check_id: "L4_ZERO_SUM_CLEARING",
        label: "Zero-sum mutual credit conservation",
        passed: zeroSumOk,
        detail: zsDetail
      },
      {
        check_id: "L4_PRIVACY_MINIMIZATION",
        label: "Selective disclosure (zero raw PII)",
        passed: privacyOk,
        detail: privacyOk
          ? "Envelope carries only blinded commitments; zero household names, addresses, emails, or phone numbers exposed."
          : "Blocked: raw personal data detected in shared ledger envelope (" + piiHits.slice(0, 2).join(", ") + ")."
      },
      {
        check_id: "L4_CLEARING_CAP_AND_COMMIT",
        label: "Bounded credit cap and batch commitment",
        passed: capAndCommitOk,
        detail: ccDetail
      }
    ];
    return finalizeReport(
      "cooperative_clearing",
      checks,
      "All four cooperative-clearing invariants hold: one-human-root nullifiers prevent bot double-counting, credits clear to exact zero, and household privacy stays intact.",
      "Settlement rejected: the clearinghouse blocked Sybil replay, unbacked credit minting, personal-data leakage, or credit-cap overrun before ledger commit."
    );
  }

  function finalizeReport(layerId, checks, passSummary, failSummary) {
    var failed = [];
    for (var i = 0; i < checks.length; i++) {
      if (!checks[i].passed) failed.push(checks[i].check_id);
    }
    return {
      layer_id: layerId,
      passed: failed.length === 0,
      failed_check_ids: failed,
      protection_summary: failed.length === 0 ? passSummary : failSummary,
      checks: checks
    };
  }

  function verifyEnvelope(env, cfg) {
    if (env.envelope_type === "capability_lease") return verifyCapabilityLease(env, cfg);
    if (env.envelope_type === "provenance_receipt") return verifyProvenanceReceipt(env);
    if (env.envelope_type === "actuator_interlock") return verifyActuatorInterlock(env, cfg);
    return verifyCooperativeClearing(env);
  }

  // ------------------------------------------------------------------
  // Safe DOM Rendering & Interactive Wiring
  // ------------------------------------------------------------------
  function clearChildren(node) {
    while (node.firstChild) {
      node.removeChild(node.firstChild);
    }
  }

  function countEnvelopeFields(val) {
    if (val === null || typeof val !== "object") {
      return 0;
    }
    if (Array.isArray(val)) {
      var arrSum = 0;
      for (var i = 0; i < val.length; i++) {
        arrSum += countEnvelopeFields(val[i]);
      }
      return arrSum;
    }
    var keys = Object.keys(val);
    var count = keys.length;
    for (var k = 0; k < keys.length; k++) {
      count += countEnvelopeFields(val[keys[k]]);
    }
    return count;
  }

  function renderJsonDiffLines(codeEl, baseEnv, currentEnv) {
    clearChildren(codeEl);
    var baseLines = JSON.stringify(baseEnv, null, 2).split("\n");
    var curLines = JSON.stringify(currentEnv, null, 2).split("\n");
    var baseSet = {};
    for (var b = 0; b < baseLines.length; b++) {
      baseSet[baseLines[b]] = true;
    }

    for (var i = 0; i < curLines.length; i++) {
      var lineSpan = document.createElement("span");
      var lineText = curLines[i];
      var changed = (i >= baseLines.length || baseLines[i] !== lineText) && !baseSet[lineText];
      lineSpan.className = changed ? "pi-json-line is-mutated" : "pi-json-line";
      lineSpan.textContent = lineText + (i < curLines.length - 1 ? "\n" : "");
      codeEl.appendChild(lineSpan);
    }
  }

  function bootInspector() {
    var dataEl = document.getElementById("protocol-inspector-data");
    var sandbox = document.getElementById("pi-sandbox");
    if (!dataEl || !sandbox) return;

    var cfg;
    try {
      cfg = JSON.parse(dataEl.textContent || "{}");
    } catch (err) {
      return;
    }
    if (!cfg || !Array.isArray(cfg.layers) || cfg.layers.length === 0) return;

    var layerById = {};
    var activeFaultsByLayer = {};
    for (var i = 0; i < cfg.layers.length; i++) {
      var lyr = cfg.layers[i];
      layerById[lyr.id] = lyr;
      activeFaultsByLayer[lyr.id] = {};
    }

    var currentLayerId = cfg.layers[0].id;

    var layerBtns = Array.prototype.slice.call(sandbox.querySelectorAll(".pi-layer-btn"));
    var eyebrowEl = document.getElementById("pi-layer-eyebrow");
    var titleEl = document.getElementById("pi-layer-title");
    var summaryEl = document.getElementById("pi-layer-summary");
    var faultListEl = document.getElementById("pi-fault-list");
    var resetBtn = document.getElementById("pi-reset-btn");
    var faultCountEl = document.getElementById("pi-fault-count");
    var envBadgeEl = document.getElementById("pi-envelope-badge");
    var jsonMetaEl = document.getElementById("pi-json-meta") || sandbox.querySelector("[data-json-meta]");
    var jsonCodeEl = document.getElementById("pi-json-code");
    var overallBadgeEl = document.getElementById("pi-overall-badge");
    var scorecardListEl = document.getElementById("pi-scorecard-list");
    var failedIdEl = document.getElementById("pi-failed-id-line");
    var protectionTextEl = document.getElementById("pi-protection-text");
    var readoutBoxEl = document.getElementById("pi-protection-readout");

    function renderFaultSwitches(layer) {
      if (!faultListEl) return;
      clearChildren(faultListEl);
      var faultMap = activeFaultsByLayer[layer.id];

      for (var f = 0; f < layer.faults.length; f++) {
        (function (faultDef) {
          var isOn = Boolean(faultMap[faultDef.id]);
          var btn = document.createElement("button");
          btn.type = "button";
          btn.className = isOn ? "pi-fault-btn is-active" : "pi-fault-btn";
          btn.setAttribute("data-fault", faultDef.id);
          btn.setAttribute("aria-pressed", isOn ? "true" : "false");

          var topRow = document.createElement("span");
          topRow.className = "pi-fault-top";

          var lbl = document.createElement("span");
          lbl.className = "pi-fault-label";
          lbl.textContent = faultDef.label;

          var pill = document.createElement("span");
          pill.className = "pi-fault-pill";
          pill.textContent = isOn ? "INJECTED" : "OFF";

          topRow.appendChild(lbl);
          topRow.appendChild(pill);

          var hint = document.createElement("span");
          hint.className = "pi-fault-hint";
          hint.textContent = faultDef.hint;

          btn.appendChild(topRow);
          btn.appendChild(hint);

          btn.addEventListener("click", function () {
            faultMap[faultDef.id] = !faultMap[faultDef.id];
            renderAll();
          });

          faultListEl.appendChild(btn);
        })(layer.faults[f]);
      }
    }

    function renderScorecard(report) {
      if (!scorecardListEl) return;
      clearChildren(scorecardListEl);

      for (var c = 0; c < report.checks.length; c++) {
        var chk = report.checks[c];
        var li = document.createElement("li");
        li.className = chk.passed ? "pi-check-card is-pass" : "pi-check-card is-blocked";

        var head = document.createElement("div");
        head.className = "pi-check-head";

        var badge = document.createElement("span");
        badge.className = chk.passed ? "pi-badge is-pass" : "pi-badge is-blocked";
        badge.textContent = chk.passed ? "PASS" : "BLOCKED";

        var label = document.createElement("span");
        label.className = "pi-check-title";
        label.textContent = chk.label;

        var codeId = document.createElement("code");
        codeId.className = "pi-check-id";
        codeId.textContent = chk.check_id;

        head.appendChild(badge);
        head.appendChild(label);
        head.appendChild(codeId);

        var detail = document.createElement("p");
        detail.className = "pi-check-detail";
        detail.textContent = chk.detail;

        li.appendChild(head);
        li.appendChild(detail);
        scorecardListEl.appendChild(li);
      }
    }

    function updateSvgArchitecture() {
      for (var i = 0; i < cfg.layers.length; i++) {
        var lyr = cfg.layers[i];
        var fmap = activeFaultsByLayer[lyr.id];
        var env = applyAdversarialFaults(lyr.envelope, fmap);
        var rep = verifyEnvelope(env, cfg);

        var box = document.getElementById("pi-svg-box-" + lyr.id);
        var pillRect = document.getElementById("pi-svg-pill-" + lyr.id);
        var pillText = document.getElementById("pi-svg-status-" + lyr.id);
        var isCurrent = lyr.id === currentLayerId;

        if (box) {
          if (!rep.passed) {
            box.setAttribute("stroke", "#963E1D");
            box.setAttribute("stroke-width", isCurrent ? "2.6" : "1.8");
            box.setAttribute("fill", "#F9EFEA");
          } else if (isCurrent) {
            box.setAttribute("stroke", "#0B3F30");
            box.setAttribute("stroke-width", "2.6");
            box.setAttribute("fill", "#EFE5D6");
          } else {
            box.setAttribute("stroke", "#1F6B4E");
            box.setAttribute("stroke-width", "1.4");
            box.setAttribute("fill", "#FFFDF8");
          }
        }
        if (pillRect) {
          pillRect.setAttribute("fill", rep.passed ? "#0B3F30" : "#963E1D");
        }
        if (pillText) {
          pillText.textContent = rep.passed ? "PASS (4/4)" : "BLOCKED";
        }
      }
    }

    function renderAll() {
      var layer = layerById[currentLayerId] || cfg.layers[0];
      var faultMap = activeFaultsByLayer[layer.id];
      var activeCount = 0;
      var fk = Object.keys(faultMap);
      for (var i = 0; i < fk.length; i++) {
        if (faultMap[fk[i]]) activeCount++;
      }

      layerBtns.forEach(function (btn) {
        var id = btn.getAttribute("data-layer") || "";
        var active = id === layer.id;
        btn.classList.toggle("is-active", active);
        btn.setAttribute("aria-pressed", active ? "true" : "false");
      });

      if (eyebrowEl) eyebrowEl.textContent = layer.eyebrow;
      if (titleEl) titleEl.textContent = layer.title;
      if (summaryEl) summaryEl.textContent = layer.everyday_summary;

      renderFaultSwitches(layer);

      if (faultCountEl) {
        faultCountEl.textContent = activeCount === 0
          ? "0 faults active (clean baseline)"
          : activeCount + (activeCount === 1 ? " fault injected" : " faults injected");
      }
      if (resetBtn) {
        resetBtn.disabled = activeCount === 0;
      }

      var currentEnv = applyAdversarialFaults(layer.envelope, faultMap);
      var report = verifyEnvelope(currentEnv, cfg);

      if (envBadgeEl) {
        envBadgeEl.textContent = activeCount === 0 ? "CLEAN ENVELOPE" : "TAMPERED INPUT";
        envBadgeEl.className = activeCount === 0 ? "pi-badge is-pass" : "pi-badge is-blocked";
      }
      if (jsonMetaEl) {
        var fieldTotal = countEnvelopeFields(currentEnv);
        jsonMetaEl.textContent = report.passed
          ? (fieldTotal + " fields · verified")
          : (fieldTotal + " fields · " + report.failed_check_ids.length + " failed");
      }
      if (jsonCodeEl) {
        renderJsonDiffLines(jsonCodeEl, layer.envelope, currentEnv);
      }

      var passCount = 0;
      for (var p = 0; p < report.checks.length; p++) {
        if (report.checks[p].passed) passCount++;
      }
      if (overallBadgeEl) {
        overallBadgeEl.textContent = report.passed
          ? "PASS · 4 / 4 INVARIANTS"
          : "BLOCKED · " + report.failed_check_ids.length + " FAILED";
        overallBadgeEl.className = report.passed ? "pi-badge is-pass" : "pi-badge is-blocked";
      }

      renderScorecard(report);

      if (readoutBoxEl) {
        readoutBoxEl.classList.toggle("is-blocked", !report.passed);
      }
      if (failedIdEl) {
        failedIdEl.textContent = report.passed
          ? "Failed invariant: none (" + passCount + "/4 checks verified)"
          : "Failed invariant: " + report.failed_check_ids.join(", ");
      }
      if (protectionTextEl) {
        protectionTextEl.textContent = report.protection_summary;
      }

      updateSvgArchitecture();
    }

    layerBtns.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var nextId = btn.getAttribute("data-layer") || "";
        if (layerById[nextId]) {
          currentLayerId = nextId;
          renderAll();
        }
      });
    });

    if (resetBtn) {
      resetBtn.addEventListener("click", function () {
        activeFaultsByLayer[currentLayerId] = {};
        renderAll();
      });
    }

    renderAll();
  }

  if (typeof globalThis !== "undefined") {
    globalThis.__cinProtocolVerifier = {
      canonicalJson: canonicalJson,
      sha256Hex: sha256Hex,
      hmacSha256Hex: hmacSha256Hex,
      applyAdversarialFaults: applyAdversarialFaults,
      verifyEnvelope: verifyEnvelope
    };
  }

  if (typeof document !== "undefined") {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", bootInspector);
    } else {
      bootInspector();
    }
  }
})();
