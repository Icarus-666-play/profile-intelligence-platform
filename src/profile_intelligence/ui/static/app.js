(() => {
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduce) return;

  document.documentElement.classList.add("motion-ready");

  const main = document.querySelector(".main");
  if (main) {
    main.style.animationDelay = "40ms";
  }

  const metrics = document.querySelectorAll(".metric-value[data-count]");
  metrics.forEach((node) => {
    const target = Number(node.getAttribute("data-count"));
    if (!Number.isFinite(target)) return;
    const isFloat = String(node.getAttribute("data-count")).includes(".");
    const duration = 650;
    const start = performance.now();
    const tick = (now) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - (1 - t) ** 3;
      const value = target * eased;
      node.textContent = isFloat ? value.toFixed(1) : String(Math.round(value));
      if (t < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });
})();
