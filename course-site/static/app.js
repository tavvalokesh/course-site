const input = document.getElementById("q");
const box = document.getElementById("suggest");
let timer;

input?.addEventListener("input", () => {
  clearTimeout(timer);
  timer = setTimeout(async () => {
    const q = input.value.trim();
    if (!q) { box.replaceChildren(); return; }
    const res = await fetch(`/api/autocomplete?q=${encodeURIComponent(q)}`);
    const items = await res.json();
    box.replaceChildren(...items.map(s => {
      const d = document.createElement("div");
      d.className = "sug";
      d.textContent = s;
      return d;
    }));
  }, 200);
});

box?.addEventListener("click", e => {
  if (e.target.classList.contains("sug")) {
    input.value = e.target.textContent;
    input.form.submit();
  }
});
