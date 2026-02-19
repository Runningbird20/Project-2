// static/pulses/pulses.js
(function () {
    function safePlay(video) {
      if (!video) return;
      // Required for autoplay on most browsers
      video.muted = true;
      video.playsInline = true;
  
      const p = video.play();
      if (p && typeof p.catch === "function") {
        p.catch(() => {
          // Autoplay may be blocked until user interacts.
          // That's okay — user can tap once and it will work afterwards.
        });
      }
    }
  
    function pauseAndOptionallyReset(video, reset = false) {
      if (!video) return;
      video.pause();
      if (reset) {
        try { video.currentTime = 0; } catch (e) {}
      }
    }
  
    document.addEventListener("DOMContentLoaded", () => {
      const videos = Array.from(document.querySelectorAll(".pulse-video"));
      if (!videos.length) return;
  
      // Pause all initially
      videos.forEach(v => pauseAndOptionallyReset(v, false));
  
      // Observe which video is “active”
      const observer = new IntersectionObserver((entries) => {
        // Pick the most visible entry (best for fast scrolling)
        const visible = entries
          .filter(e => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
  
        if (visible.length) {
          const activeVideo = visible[0].target;
  
          // Pause all others
          videos.forEach(v => {
            if (v !== activeVideo) pauseAndOptionallyReset(v, true);
          });
  
          // Play active
          safePlay(activeVideo);
        } else {
          // If nothing is visible enough, pause everything
          videos.forEach(v => pauseAndOptionallyReset(v, false));
        }
      }, {
        root: null,
        threshold: [0.25, 0.5, 0.65, 0.8],
      });
  
      videos.forEach(v => observer.observe(v));
  
      // Bonus: click to toggle play/pause
      videos.forEach(v => {
        v.addEventListener("click", () => {
          if (v.paused) safePlay(v);
          else v.pause();
        });
      });
    });
  })();
  