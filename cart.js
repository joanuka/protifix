/* Shared basket for every page. Stores only ids and quantities; the server works out names and prices. */
(function () {
  var KEY = "mtk_cart_v1", mem = [];
  function read() {
    try {
      var v = JSON.parse(localStorage.getItem(KEY) || "[]");
      if (!Array.isArray(v)) return mem;
      return v.filter(function (x) { return x && typeof x.id === "string" && x.qty > 0; });
    } catch (e) { return mem; }  // private windows can block storage: keep working in memory
  }
  function write(list) {
    mem = list;
    try { localStorage.setItem(KEY, JSON.stringify(list)); } catch (e) {}
    badge();
  }
  function badge() {
    var n = Cart.count();
    document.querySelectorAll("[data-cart-count]").forEach(function (el) { el.textContent = n; el.hidden = !n; });
  }
  var Cart = {
    get: read,
    count: function () { return read().reduce(function (a, x) { return a + x.qty; }, 0); },
    qty: function (id) { var x = read().find(function (l) { return l.id === id; }); return x ? x.qty : 0; },
    add: function (id, n) {
      var list = read(), x = list.find(function (l) { return l.id === id; });
      if (x) x.qty = Math.min(20, x.qty + (n || 1)); else list.push({ id: id, qty: n || 1 });
      write(list);
    },
    set: function (id, qty) {
      var list = read(), i = list.findIndex(function (l) { return l.id === id; });
      if (qty <= 0) { if (i > -1) list.splice(i, 1); }
      else if (i > -1) list[i].qty = Math.min(20, qty);  // keep the line where it is
      else list.push({ id: id, qty: Math.min(20, qty) });
      write(list);
    },
    remove: function (id) { Cart.set(id, 0); },
    clear: function () { write([]); }
  };
  window.Cart = Cart;
  document.addEventListener("DOMContentLoaded", badge);
  window.addEventListener("storage", badge);
})();