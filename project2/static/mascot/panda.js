// static/mascot/panda.js
(function () {
  const mascot = document.getElementById("panda-mascot");
  if (!mascot) return;

  const wrap = mascot.querySelector(".panda-wrap");
  const bubble = mascot.querySelector(".panda-bubble");
  const confettiLayer = document.getElementById("panda-confetti");

  const config = {
    bubbleMs: 2800,
    moveDurationPerPx: 1.15,
    minMoveMs: 380,
    maxMoveMs: 1600,
    edgePadding: 18,
    storageKey: "panda:pos:v1",
  };

  let bubbleTimer = null;
  let moving = false;
  let dragging = false;
  let dragPointerId = null;
  let dragOffset = { x: 0, y: 0 };

  function clamp(n, min, max) {
    return Math.max(min, Math.min(max, n));
  }

  function setMode(mode) {
    mascot.classList.remove("idle", "moving", "celebrate");
    if (mode) mascot.classList.add(mode);
  }

  function showBubble(text, ms = config.bubbleMs) {
    if (!bubble) return;
    bubble.textContent = text || "";
    bubble.classList.add("show");
    clearTimeout(bubbleTimer);
    bubbleTimer = setTimeout(() => bubble.classList.remove("show"), ms);
  }

  function getRect() {
    return mascot.getBoundingClientRect();
  }

  function setPos(x, y) {
    const rect = getRect();
    const clampedX = clamp(x, config.edgePadding, window.innerWidth - rect.width - config.edgePadding);
    const clampedY = clamp(y, config.edgePadding, window.innerHeight - rect.height - config.edgePadding);
    mascot.style.left = `${clampedX}px`;
    mascot.style.top = `${clampedY}px`;
    mascot.style.right = "auto";
    mascot.style.bottom = "auto";
  }

  function currentPos() {
    const rect = getRect();
    return { x: rect.left, y: rect.top };
  }

  function savePos() {
    const rect = getRect();
    try {
      localStorage.setItem(config.storageKey, JSON.stringify({ x: rect.left, y: rect.top }));
    } catch (e) {}
  }

  function loadPos() {
    try {
      const raw = localStorage.getItem(config.storageKey);
      if (!raw) return false;
      const p = JSON.parse(raw);
      if (typeof p?.x !== "number" || typeof p?.y !== "number") return false;
      setPos(p.x, p.y);
      return true;
    } catch (e) {
      return false;
    }
  }

  function moveTo(x, y, opts = {}) {
    if (dragging) return;
    const dur = clamp(opts.durationMs ?? 0, config.minMoveMs, config.maxMoveMs);
    moving = true;
    setMode("moving");
    mascot.style.transition = `left ${dur}ms ease-in-out, top ${dur}ms ease-in-out, right 0ms, bottom 0ms`;
    setPos(x, y);
    window.setTimeout(() => {
      moving = false;
      setMode("idle");
      mascot.style.transition = "";
      savePos();
    }, dur + 10);
  }

  function moveToElement(selector, opts = {}) {
    if (dragging) return false;
    const el = document.querySelector(selector);
    if (!el) return false;
    const elRect = el.getBoundingClientRect();
    const mRect = getRect();
    const targetX = clamp(
      elRect.right - mRect.width / 2,
      config.edgePadding,
      window.innerWidth - mRect.width - config.edgePadding
    );
    const targetY = clamp(
      elRect.bottom - mRect.height / 2,
      config.edgePadding,
      window.innerHeight - mRect.height - config.edgePadding
    );
    const cur = currentPos();
    const dx = targetX - cur.x;
    const dy = targetY - cur.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    const durationMs = clamp(dist * config.moveDurationPerPx, config.minMoveMs, config.maxMoveMs);
    moveTo(targetX, targetY, { durationMs, ...opts });
    return true;
  }

  function confetti(count = 26) {
    if (!confettiLayer) return;
    const colors = ["#0d6efd", "#198754", "#ffc107", "#dc3545", "#6f42c1", "#20c997"];
    for (let i = 0; i < count; i++) {
      const piece = document.createElement("div");
      piece.className = "panda-confetti-piece";
      piece.style.left = `${Math.random() * 100}vw`;
      piece.style.background = colors[Math.floor(Math.random() * colors.length)];
      piece.style.transform = `rotate(${Math.random() * 360}deg)`;
      const dur = 900 + Math.random() * 1100;
      piece.style.animationDuration = `${dur}ms`;
      piece.style.animationDelay = `${Math.random() * 200}ms`;
      piece.style.width = `${8 + Math.random() * 8}px`;
      piece.style.height = `${10 + Math.random() * 12}px`;
      confettiLayer.appendChild(piece);
      window.setTimeout(() => piece.remove(), dur + 500);
    }
  }

  function celebrate(message) {
    if (dragging) return;
    setMode("celebrate");
    confetti(34);
    if (message) showBubble(message, 3400);
    window.setTimeout(() => setMode("idle"), 1400);
  }

  function activateAssistant() {
    const event = new CustomEvent("panda:activate", { cancelable: true });
    const handled = !window.dispatchEvent(event);
    return handled;
  }

  if (wrap) {
    wrap.addEventListener("click", () => {
      if (moving || dragging) return;
      if (activateAssistant()) return;
      const lines = [
        "Need help? Check job search.",
        "Tip: keep your profile public for recruiters.",
        "You have got this.",
        "I am rooting for you.",
      ];
      showBubble(lines[Math.floor(Math.random() * lines.length)]);
    });
  }

  if (bubble) {
    bubble.addEventListener("click", () => {
      if (moving || dragging) return;
      activateAssistant();
    });
  }

  mascot.classList.add("idle", "blink");

  function runPageHooks() {
    const body = document.body;
    if (!body) return;
    const bubbleText = body.getAttribute("data-panda-bubble");
    if (bubbleText) showBubble(bubbleText);
    const moveToSel = body.getAttribute("data-panda-move-to");
    if (moveToSel) window.setTimeout(() => moveToElement(moveToSel), 450);
    const celebrateText = body.getAttribute("data-panda-celebrate");
    if (celebrateText) window.setTimeout(() => celebrate(celebrateText), 650);
  }

  window.addEventListener("panda:bubble", (e) => showBubble(e?.detail?.text || ""));
  window.addEventListener("panda:moveTo", (e) => {
    const sel = e?.detail?.selector;
    if (sel) moveToElement(sel);
  });
  window.addEventListener("panda:celebrate", (e) => celebrate(e?.detail?.text || "Lets go."));

  function anchorLeftTopOnce() {
    const rect = getRect();
    mascot.style.left = `${rect.left}px`;
    mascot.style.top = `${rect.top}px`;
    mascot.style.right = "auto";
    mascot.style.bottom = "auto";
  }

  function onPointerDown(e) {
    if (!wrap || moving) return;
    dragging = true;
    dragPointerId = e.pointerId;
    try {
      wrap.setPointerCapture(dragPointerId);
    } catch {}
    mascot.classList.add("dragging");
    setMode(null);
    const rect = getRect();
    dragOffset.x = e.clientX - rect.left;
    dragOffset.y = e.clientY - rect.top;
    mascot.style.transition = "none";
    if (bubble) bubble.classList.remove("show");
  }

  function onPointerMove(e) {
    if (!dragging) return;
    if (dragPointerId !== null && e.pointerId !== dragPointerId) return;
    setPos(e.clientX - dragOffset.x, e.clientY - dragOffset.y);
  }

  function endDrag(e) {
    if (!dragging) return;
    if (dragPointerId !== null && e.pointerId !== dragPointerId) return;
    dragging = false;
    mascot.classList.remove("dragging");
    dragPointerId = null;
    setMode("idle");
    mascot.style.transition = "";
    savePos();
  }

  if (wrap) {
    wrap.addEventListener("pointerdown", onPointerDown);
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", endDrag);
    window.addEventListener("pointercancel", endDrag);
  }

  window.setTimeout(() => {
    anchorLeftTopOnce();
    loadPos();
    runPageHooks();
  }, 80);

  window.addEventListener("resize", () => {
    const rect = getRect();
    mascot.style.left = `${clamp(rect.left, config.edgePadding, window.innerWidth - rect.width - config.edgePadding)}px`;
    mascot.style.top = `${clamp(rect.top, config.edgePadding, window.innerHeight - rect.height - config.edgePadding)}px`;
    savePos();
  });
})();
