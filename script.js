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

const detailButtons = document.querySelectorAll(".detail-trigger");
const detailModal = document.getElementById("detailModal");
const detailTitle = document.getElementById("detailTitle");
const detailBody = document.getElementById("detailBody");
const closeModalButtons = document.querySelectorAll("[data-close-modal]");

if (detailButtons.length && detailModal && detailTitle && detailBody) {
  detailButtons.forEach((button) => {
    button.addEventListener("click", () => {
      detailTitle.textContent = button.dataset.title || "Details";
      detailBody.textContent = button.dataset.detail || "";
      detailModal.hidden = false;
      document.body.style.overflow = "hidden";
    });
  });

  closeModalButtons.forEach((button) => {
    button.addEventListener("click", () => {
      detailModal.hidden = true;
      document.body.style.overflow = "";
    });
  });

  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !detailModal.hidden) {
      detailModal.hidden = true;
      document.body.style.overflow = "";
    }
  });
}

const revealTargets = document.querySelectorAll(".section, .card, .mini-card, .skills-explorer, .detail-trigger");
revealTargets.forEach((target) => target.classList.add("reveal"));

if ("IntersectionObserver" in window) {
  const revealObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("visible");
          revealObserver.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.14 }
  );
  revealTargets.forEach((target) => revealObserver.observe(target));
} else {
  // Fallback for browsers without IntersectionObserver.
  revealTargets.forEach((target) => target.classList.add("visible"));
}

const tiltTargets = document.querySelectorAll(".card, .mini-card");
tiltTargets.forEach((card) => {
  card.addEventListener("mousemove", (event) => {
    const rect = card.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    const rotY = ((x / rect.width) - 0.5) * 8;
    const rotX = ((y / rect.height) - 0.5) * -8;
    card.style.transform = `perspective(900px) rotateX(${rotX}deg) rotateY(${rotY}deg) translateY(-2px)`;
  });
  card.addEventListener("mouseleave", () => {
    card.style.transform = "";
  });
});

const canvas = document.getElementById("starfield");
if (canvas) {
  const ctx = canvas.getContext("2d");
  let stars = [];
  let animationId = null;
  let pointerX = window.innerWidth / 2;
  let pointerY = window.innerHeight / 2;

  const resizeCanvas = () => {
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.floor(window.innerWidth * dpr);
    canvas.height = Math.floor(window.innerHeight * dpr);
    canvas.style.width = `${window.innerWidth}px`;
    canvas.style.height = `${window.innerHeight}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    stars = Array.from({ length: Math.min(180, Math.floor(window.innerWidth / 7)) }, () => ({
      x: Math.random() * window.innerWidth,
      y: Math.random() * window.innerHeight,
      r: Math.random() * 1.6 + 0.35,
      s: Math.random() * 0.28 + 0.06
    }));
  };

  const draw = () => {
    ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);
    const pullX = (pointerX - window.innerWidth / 2) * 0.0007;
    const pullY = (pointerY - window.innerHeight / 2) * 0.0007;
    stars.forEach((star) => {
      star.x += star.s + pullX;
      star.y += star.s * 0.22 + pullY;
      if (star.x > window.innerWidth + 4) star.x = -4;
      if (star.y > window.innerHeight + 4) star.y = -4;
      if (star.y < -4) star.y = window.innerHeight + 4;
      ctx.beginPath();
      ctx.fillStyle = "rgba(185, 245, 255, 0.9)";
      ctx.arc(star.x, star.y, star.r, 0, Math.PI * 2);
      ctx.fill();
    });
    animationId = window.requestAnimationFrame(draw);
  };

  window.addEventListener("mousemove", (event) => {
    pointerX = event.clientX;
    pointerY = event.clientY;
  });
  window.addEventListener("resize", resizeCanvas);
  resizeCanvas();
  draw();
  window.addEventListener("beforeunload", () => {
    if (animationId) {
      window.cancelAnimationFrame(animationId);
    }
  });
}
