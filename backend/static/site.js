document.addEventListener("DOMContentLoaded", () => {
  const navToggle = document.querySelector(".nav-toggle");
  const navList = document.querySelector("#primary-nav");
  if (navToggle && navList) {
    navToggle.addEventListener("click", () => {
      const isOpen = navList.classList.toggle("open");
      navToggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
    });
  }

  const revealTargets = document.querySelectorAll(".tile, .testimonial-card, .home-feature");
  if ("IntersectionObserver" in window && revealTargets.length) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15 }
    );
    revealTargets.forEach((el) => {
      el.classList.add("reveal");
      observer.observe(el);
    });
  }

  const menuGrid = document.getElementById("menu-grid");
  const menuSearch = document.getElementById("menu-search");
  const menuSort = document.getElementById("menu-sort");
  const menuEmpty = document.getElementById("menu-empty");

  const applyMenuFilter = () => {
    if (!menuGrid) return;
    const cards = Array.from(menuGrid.querySelectorAll(".js-menu-card"));
    const query = (menuSearch?.value || "").trim().toLowerCase();
    const sortValue = menuSort?.value || "default";

    cards.forEach((card) => {
      const name = card.dataset.name || "";
      card.hidden = query ? !name.includes(query) : false;
    });

    const visibleCards = cards.filter((card) => !card.hidden);
    if (menuEmpty) {
      menuEmpty.hidden = visibleCards.length > 0;
    }

    if (sortValue !== "default") {
      visibleCards.sort((a, b) => {
        const pa = parseFloat(a.dataset.price || "0");
        const pb = parseFloat(b.dataset.price || "0");
        return sortValue === "price_asc" ? pa - pb : pb - pa;
      });
      visibleCards.forEach((card) => menuGrid.appendChild(card));
    }
  };

  menuSearch?.addEventListener("input", applyMenuFilter);
  menuSort?.addEventListener("change", applyMenuFilter);
});
