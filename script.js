// ── Mobile menu ────────────────────────────────────────────────
const menuButton = document.querySelector(".menu-toggle");
const nav = document.querySelector(".site-nav");

if (menuButton && nav) {
  menuButton.addEventListener("click", () => {
    const isOpen = nav.classList.toggle("open");
    menuButton.setAttribute("aria-expanded", String(isOpen));
  });

  nav.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      nav.classList.remove("open");
      menuButton.setAttribute("aria-expanded", "false");
    });
  });
}

// ── Skills tabs ─────────────────────────────────────────────────
const skillTabs = document.querySelectorAll(".skill-tab");
const skillPanels = document.querySelectorAll(".skill-panel");

if (skillTabs.length && skillPanels.length) {
  skillTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const target = tab.dataset.skillTab;
      skillTabs.forEach((item) => {
        const isActive = item === tab;
        item.classList.toggle("active", isActive);
        item.setAttribute("aria-selected", String(isActive));
      });
      skillPanels.forEach((panel) => {
        const isActive = panel.dataset.skillPanel === target;
        panel.classList.toggle("active", isActive);
        panel.hidden = !isActive;
      });
    });
  });
}

// ── Modal system ────────────────────────────────────────────────
const detailModal  = document.getElementById("detailModal");
const detailTitle  = document.getElementById("detailTitle");
const detailBody   = document.getElementById("detailBody");
const closeButtons = document.querySelectorAll("[data-close-modal]");

function openModal(title, bodyHTML) {
  if (!detailModal || !detailTitle || !detailBody) return;
  detailTitle.textContent = title;
  detailBody.innerHTML    = bodyHTML;
  detailModal.hidden = false;
  document.body.style.overflow = "hidden";
}

function closeModal() {
  if (!detailModal) return;
  detailModal.hidden = true;
  document.body.style.overflow = "";
}

// Case study triggers (data-case-id)
document.querySelectorAll(".case-trigger").forEach((btn) => {
  btn.addEventListener("click", () => {
    const caseId  = btn.dataset.caseId;
    const caseEl  = caseId ? document.getElementById(caseId) : null;
    const title   = caseEl ? (caseEl.dataset.title || "Case Study") : "Case Study";
    const content = caseEl ? caseEl.innerHTML : "<p>Content not found.</p>";
    openModal(title, content);
  });
});

// Generic detail triggers (data-title + data-detail)
document.querySelectorAll(".detail-trigger:not(.case-trigger)").forEach((btn) => {
  btn.addEventListener("click", () => {
    const title   = btn.dataset.title  || "Details";
    const detail  = btn.dataset.detail || "";
    openModal(title, `<p>${detail}</p>`);
  });
});

// Close
closeButtons.forEach((btn) => btn.addEventListener("click", closeModal));

window.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && detailModal && !detailModal.hidden) closeModal();
});

// ── Scroll reveal ───────────────────────────────────────────────
const revealTargets = document.querySelectorAll(
  ".section, .card, .mini-card, .skills-explorer, .system-card, .focus-card, .pub-item"
);
revealTargets.forEach((t) => t.classList.add("reveal"));

if ("IntersectionObserver" in window) {
  const obs = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("visible");
          obs.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.1 }
  );
  revealTargets.forEach((t) => obs.observe(t));
} else {
  revealTargets.forEach((t) => t.classList.add("visible"));
}

// ── Card tilt effect ─────────────────────────────────────────────
document.querySelectorAll(".card, .mini-card, .focus-card").forEach((card) => {
  card.addEventListener("mousemove", (e) => {
    const rect = card.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const rotY = ((x / rect.width)  - 0.5) *  6;
    const rotX = ((y / rect.height) - 0.5) * -6;
    card.style.transform = `perspective(900px) rotateX(${rotX}deg) rotateY(${rotY}deg) translateY(-2px)`;
  });
  card.addEventListener("mouseleave", () => {
    card.style.transform = "";
  });
});

// ── Starfield ────────────────────────────────────────────────────
const canvas = document.getElementById("starfield");
if (canvas) {
  const ctx = canvas.getContext("2d");
  let stars = [];
  let animationId = null;
  let pointerX = window.innerWidth  / 2;
  let pointerY = window.innerHeight / 2;

  const resizeCanvas = () => {
    const dpr = window.devicePixelRatio || 1;
    canvas.width  = Math.floor(window.innerWidth  * dpr);
    canvas.height = Math.floor(window.innerHeight * dpr);
    canvas.style.width  = `${window.innerWidth}px`;
    canvas.style.height = `${window.innerHeight}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    stars = Array.from(
      { length: Math.min(180, Math.floor(window.innerWidth / 7)) },
      () => ({
        x: Math.random() * window.innerWidth,
        y: Math.random() * window.innerHeight,
        r: Math.random() * 1.6 + 0.35,
        s: Math.random() * 0.28 + 0.06,
      })
    );
  };

  const draw = () => {
    ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);
    const pullX = (pointerX - window.innerWidth  / 2) * 0.0007;
    const pullY = (pointerY - window.innerHeight / 2) * 0.0007;
    stars.forEach((star) => {
      star.x += star.s + pullX;
      star.y += star.s * 0.22 + pullY;
      if (star.x > window.innerWidth  + 4) star.x = -4;
      if (star.y > window.innerHeight + 4) star.y = -4;
      if (star.y < -4) star.y = window.innerHeight + 4;
      ctx.beginPath();
      ctx.fillStyle = "rgba(185, 245, 255, 0.9)";
      ctx.arc(star.x, star.y, star.r, 0, Math.PI * 2);
      ctx.fill();
    });
    animationId = window.requestAnimationFrame(draw);
  };

  window.addEventListener("mousemove", (e) => { pointerX = e.clientX; pointerY = e.clientY; });
  window.addEventListener("resize", resizeCanvas);
  resizeCanvas();
  draw();
  window.addEventListener("beforeunload", () => {
    if (animationId) window.cancelAnimationFrame(animationId);
  });
}
