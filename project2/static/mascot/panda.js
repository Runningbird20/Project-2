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
    };
  
    let bubbleTimer = null;
    let moving = false;
  
    function clamp(n, min, max) { return Math.max(min, Math.min(max, n)); }
  
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
  
    function currentPos() {
      const rect = mascot.getBoundingClientRect();
      return { x: rect.left, y: rect.top };
    }
  
    function moveTo(x, y, opts = {}) {
      const dur = clamp(opts.durationMs ?? config.minMoveMs, config.minMoveMs, config.maxMoveMs);
      moving = true;
      setMode("moving");
  
      mascot.style.transition = `left ${dur}ms ease-in-out, top ${dur}ms ease-in-out, right 0ms, bottom 0ms`;
      mascot.style.left = `${x}px`;
      mascot.style.top = `${y}px`;
      mascot.style.right = "auto";
      mascot.style.bottom = "auto";
  
      window.setTimeout(() => {
        moving = false;
        setMode("idle");
        mascot.style.transition = "";
      }, dur + 10);
    }
  
    function moveToElement(selector, opts = {}) {
      const el = document.querySelector(selector);
      if (!el) return false;
  
      const elRect = el.getBoundingClientRect();
      const mRect = mascot.getBoundingClientRect();
  
      const targetX = clamp(
        elRect.right - (mRect.width / 2),
        config.edgePadding,
        window.innerWidth - mRect.width - config.edgePadding
      );
      const targetY = clamp(
        elRect.bottom - (mRect.height / 2),
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
      setMode("celebrate");
      confetti(34);
      if (message) showBubble(message, 3400);
      window.setTimeout(() => setMode("idle"), 1400);
    }
  
    if (wrap) {
      wrap.addEventListener("click", () => {
        if (moving) return;
        const lines = [
          "Need help? Check Job Search 👀",
          "Tip: keep your profile public for recruiters!",
          "You’ve got this 💪",
          "I’m rooting for you 🐼",
        ];
        showBubble(lines[Math.floor(Math.random() * lines.length)]);
      });
    }
  
    mascot.classList.add("idle", "blink");
  
    function runPageHooks() {
      const body = document.body;
      if (!body) return;
  
      const bubbleText = body.getAttribute("data-panda-bubble");
      if (bubbleText) showBubble(bubbleText);
  
      const moveToSel = body.getAttribute("data-panda-move-to");
      if (moveToSel) {
        window.setTimeout(() => moveToElement(moveToSel), 450);
      }
  
      const celebrateText = body.getAttribute("data-panda-celebrate");
      if (celebrateText) {
        window.setTimeout(() => celebrate(celebrateText), 650);
      }
    }
  
    window.addEventListener("panda:bubble", (e) => showBubble(e?.detail?.text || ""));
    window.addEventListener("panda:moveTo", (e) => {
      const sel = e?.detail?.selector;
      if (sel) moveToElement(sel);
    });
    window.addEventListener("panda:celebrate", (e) => celebrate(e?.detail?.text || "Let’s gooo!"));
  
    function anchorLeftTopOnce() {
      const rect = mascot.getBoundingClientRect();
      mascot.style.left = `${rect.left}px`;
      mascot.style.top = `${rect.top}px`;
      mascot.style.right = "auto";
      mascot.style.bottom = "auto";
    }
  
    window.setTimeout(() => {
      anchorLeftTopOnce();
      runPageHooks();
    }, 80);
  
    window.addEventListener("resize", () => {
      const rect = mascot.getBoundingClientRect();
      const x = clamp(rect.left, config.edgePadding, window.innerWidth - rect.width - config.edgePadding);
      const y = clamp(rect.top, config.edgePadding, window.innerHeight - rect.height - config.edgePadding);
      mascot.style.left = `${x}px`;
      mascot.style.top = `${y}px`;
    });
  })();
  