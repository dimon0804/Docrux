// Ставит тему до первой отрисовки, чтобы страница не мигала светлым фоном.
(function () {
  try {
    var saved = localStorage.getItem("paragraf:theme");
    var dark =
      saved === "dark" ||
      (saved !== "light" && window.matchMedia("(prefers-color-scheme: dark)").matches);
    document.documentElement.dataset.theme = dark ? "dark" : "light";
  } catch (error) {
    document.documentElement.dataset.theme = "light";
  }
})();
