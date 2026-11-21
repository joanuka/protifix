/* Adds "Sign in" / "Hi, Name" to the top menu of every page. */
(function () {
  fetch("/api/me").then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; }).then(function (u) {
    var host = document.querySelector("nav ul") || document.querySelector("nav .r") || document.querySelector("nav .wrap > div:last-child") || document.querySelector("nav");
    if (!host) return;
    var a = document.createElement("a");
    a.href = "/account";
    a.textContent = u ? "Hi, " + u.name.split(" ")[0] : "Sign in";
    a.style.cssText = "text-decoration:none;font-weight:600;font-size:.82rem;color:inherit;margin-left:14px;white-space:nowrap";
    if (host.tagName === "UL") {
      var li = document.createElement("li");
      li.style.setProperty("display", "list-item", "important");  // stay visible on phones
      li.appendChild(a);
      host.insertBefore(li, host.lastElementChild);
    } else host.insertBefore(a, host.firstChild);
  });
})();