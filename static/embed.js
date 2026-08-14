(() => {
  const script = document.currentScript;

  const API = script.dataset.api;
  const SITE = script.dataset.site;
  const PAGE = script.dataset.page || location.pathname;
  const SORT = script.dataset.sort || "newest";
  const KEY = "comments-token";

  const TEXT = {
    empty: "No comments yet.",
    loading: "Loading…",
    placeholder: "Write a comment…",
    replyPlaceholder: "Write a reply…",
    submit: "Post",
    reply: "Reply",
    delete: "Delete",
    confirmDelete: "Delete this comment?",
    deleted: "[deleted]",
    signIn: "Sign in with",
    signOut: "Sign out",
    providers: { github: "GitHub" },
    expired: "Your session expired. Please sign in again.",
    failed: "Something went wrong.",
    poweredBy: "Powered by Hilo",
  };

  const host = document.createElement("div");

  host.className = "comments-widget";

  if (script.dataset.scheme) host.dataset.scheme = script.dataset.scheme;
  if (script.parentNode === document.head) {
    addEventListener("DOMContentLoaded", () => document.body.append(host));
  } else {
    script.after(host);
  }

  const root = host.attachShadow({ mode: "open" });

  root.innerHTML = `<div class="widget" part="widget">
    <footer class="powered" part="powered"></footer>
    <div class="bar" part="bar"></div>
    <div class="thread" part="thread"></div>
  </div>`;

  const el = (tag, cls, text) => {
    const n = document.createElement(tag);

    if (cls) {
      n.className = cls;
      n.setAttribute("part", cls);
    }

    if (text != null) n.textContent = text;

    return n;
  };

  const $ = (s) => root.querySelector(s);
  const thread = $(".thread");
  const bar = $(".bar");
  const powered = el("a", "powered", TEXT.poweredBy);
  powered.href = "https://byandrev.github.io/hilo/";
  powered.target = "_blank";
  powered.rel = "noopener noreferrer";
  $(".powered").append(powered);

  // --- time ------------------------------------------------------------

  const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
  const UNITS = [
    ["year", 31536000],
    ["month", 2592000],
    ["week", 604800],
    ["day", 86400],
    ["hour", 3600],
    ["minute", 60],
  ];
  // The API sends a real ISO 8601 timestamp with an offset, so Date parses it as-is.
  const parseUTC = (s) => new Date(s);

  const ago = (date) => {
    const secs = (date - Date.now()) / 1000;
    for (const [unit, size] of UNITS) {
      if (Math.abs(secs) >= size)
        return rtf.format(Math.round(secs / size), unit);
    }
    return rtf.format(Math.round(secs), "second");
  };

  // --- state -----------------------------------------------------------

  let token = localStorage.getItem(KEY);
  // UI only; the signature on the token is what the server actually trusts
  let user = JSON.parse(localStorage.getItem(KEY + "-user") || "null");

  const api = async (path, opts = {}) => {
    const res = await fetch(API + path, {
      ...opts,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
    if (res.status === 401) {
      logout();
      throw new Error(TEXT.expired);
    }
    if (!res.ok)
      throw new Error(
        (await res.json().catch(() => ({}))).detail || TEXT.failed,
      );
    return res.status === 204 ? null : res.json();
  };

  const logout = () => {
    localStorage.removeItem(KEY);
    localStorage.removeItem(KEY + "-user");
    token = user = null;
    render();
  };

  const login = (provider) => {
    const url = `${API}/auth/${provider}/login?origin=${encodeURIComponent(location.origin)}`;
    window.open(url, "comments-login", "width=520,height=650");
    addEventListener("message", function onMsg(e) {
      if (e.origin !== API || e.data?.type !== "comments-auth") return;
      removeEventListener("message", onMsg);
      localStorage.setItem(KEY, e.data.token);
      localStorage.setItem(KEY + "-user", JSON.stringify(e.data.user));
      token = e.data.token;
      user = e.data.user;
      render();
    });
  };

  // --- rendering -------------------------------------------------------

  const composer = (parentId, after) => {
    const f = el("form", "form");
    const ta = el("textarea", "textarea");
    ta.placeholder = parentId ? TEXT.replyPlaceholder : TEXT.placeholder;
    const btn = el("button", "primary", TEXT.submit);
    const err = el("div", "error");
    f.append(ta, btn, err);

    f.onsubmit = async (e) => {
      e.preventDefault();
      btn.disabled = true;
      err.textContent = "";
      try {
        await api("/api/comments", {
          method: "POST",
          body: JSON.stringify({
            site: SITE,
            page: PAGE,
            body: ta.value,
            parent_id: parentId,
          }),
        });
        await render();
      } catch (ex) {
        err.textContent = ex.message;
        btn.disabled = false;
      }
    };
    after.after(f);
  };

  const node = (c, depth) => {
    const box = el("div", depth ? "comment nested" : "comment");
    const level = Math.min(depth, 5); // unlimited nesting, capped indent
    box.style.setProperty("--depth", level);
    if (level) {
      box.style.setProperty("--depth-rule", "1px");
      box.style.setProperty("--depth-pad", "var(--_indent)");
    }

    if (c.deleted) {
      box.append(el("p", "body tombstone", TEXT.deleted));
      return box;
    }

    const meta = el("div", "meta");
    if (c.author_avatar) {
      const img = el("img", "avatar");
      img.src = c.author_avatar;
      img.alt = "";
      img.loading = "lazy";
      meta.append(img);
    }
    const when = parseUTC(c.created_at);
    const time = el("time", "time", ago(when));
    time.dateTime = when.toISOString();
    time.title = when.toLocaleString();
    meta.append(el("span", "author", c.author_name), time);

    box.append(meta, el("p", "body", c.body));

    const actions = el("div", "actions");
    if (token) {
      const reply = el("button", "action", TEXT.reply);
      reply.type = "button";
      reply.onclick = () => {
        reply.disabled = true;
        composer(c.id, actions);
      };
      actions.append(reply);
    }
    if (user && c.author_id === user.sub) {
      const del = el("button", "action danger", TEXT.delete);
      del.type = "button";
      del.onclick = async () => {
        if (!confirm(TEXT.confirmDelete)) return;
        await api(`/api/comments/${c.id}`, { method: "DELETE" });
        render();
      };
      actions.append(del);
    }
    if (actions.children.length) box.append(actions);
    return box;
  };

  const render = async () => {
    thread.replaceChildren(el("p", "loading", TEXT.loading));
    let rows;
    try {
      rows = await api(
        `/api/comments?site=${encodeURIComponent(SITE)}&page=${encodeURIComponent(PAGE)}&sort=${SORT}`,
      );
    } catch (e) {
      thread.replaceChildren(el("p", "error", e.message));
      return;
    }

    // tree without recursive SQL: group by parent, then walk depth-first
    const byParent = new Map();
    for (const c of rows) {
      if (!byParent.has(c.parent_id)) byParent.set(c.parent_id, []);
      byParent.get(c.parent_id).push(c);
    }
    thread.replaceChildren();
    (function walk(parent, depth) {
      for (const c of byParent.get(parent) || []) {
        thread.append(node(c, depth));
        walk(c.id, depth + 1);
      }
    })(null, 0);
    if (!rows.length) thread.append(el("p", "empty", TEXT.empty));

    bar.replaceChildren();
    root.querySelectorAll(".widget > .form").forEach((f) => f.remove());
    if (token) {
      bar.append(el("span", "session", user?.name || ""));
      const out = el("button", "action", TEXT.signOut);
      out.type = "button";
      out.onclick = logout;
      bar.append(out);
      composer(null, bar);
    } else {
      for (const p of ["github"]) {
        const b = el(
          "button",
          "primary",
          `${TEXT.signIn} ${TEXT.providers[p]}`,
        );
        b.type = "button";
        b.onclick = () => login(p);
        bar.append(b);
      }
    }
  };

  render();
})();
