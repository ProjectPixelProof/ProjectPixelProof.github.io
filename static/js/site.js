/* Publication metadata is intentionally separate from the paper's prose. */
(() => {
  "use strict";
  // Preserve links to sections moved off the homepage.
  if (document.body.classList.contains("homepage")) {
    const moved = new Set(["#verification", "#source-analysis"]);
    const routeMovedSection = () => {
      if (moved.has(location.hash)) location.replace("programs.html" + location.hash);
    };
    routeMovedSection();
    window.addEventListener("hashchange", routeMovedSection);
  }
  function publicURL(value) {
    try {
      const url = new URL(value);
      return ["https:", "http:"].includes(url.protocol) ? url.href : null;
    } catch {
      return null;
    }
  }
  function link(label, href, className = "") {
    const a = document.createElement("a");
    const iconFiles = {"huggingface.co": "huggingface.svg", "github.com": "github.svg"};
    const iconFile = iconFiles[new URL(href).hostname];
    if (className.includes("button") && iconFile) {
      const icon = document.createElement("img");
      icon.src = `static/images/${iconFile}`;
      icon.alt = "";
      icon.setAttribute("aria-hidden", "true");
      icon.className = "resource-icon";
      icon.width = 20;
      icon.height = 20;
      a.append(icon);
    }
    const text = document.createElement("span");
    text.textContent = label;
    a.append(text);
    a.href = href;
    a.className = className;
    return a;
  }
  fetch("data/site.json")
    .then((response) => {
      if (!response.ok)
        throw new Error("Publication configuration unavailable");
      return response.json();
    })
    .then((config) => {
      // This submission site intentionally has no author or affiliation rendering.
      const labels = {
        paper: "Paper",
        code: "GitHub",
        data: "Models and Datasets",
        arxiv: "arXiv",
      };
      let configured = 0;
      Object.entries(labels).forEach(([key, label]) => {
        const url = publicURL(config.links?.[key]);
        if (!url) return;
        configured++;
        document
          .querySelector("#publication-links")
          .append(link(label, url, "button resource-link"));
        document
          .querySelector("#resource-links")
          .prepend(link(`${label} ↗`, url));
      });
      if (configured)
        document.querySelector("#release-message").textContent =
          "Explore the project resources and the recorded examples used in this website.";
      if (config.bibtex) {
        document.querySelector("#bibtex").textContent = config.bibtex;
        document.querySelector("#citation-block").hidden = false;
      }
    })
    .catch(() => {
      // The static scientific content and question explorer remain usable.
    });
})();
