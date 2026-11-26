const SHELL_CACHE = "torre-shell-v8";
const API_CACHE = "torre-api-v8";
const SHELL = [
  "/",
  "/index.html",
  "/css/styles.css?v=8",
  "/js/app.js?v=8",
  "/manifest.json",
  "/icons/icon-192.svg",
  "/icons/icon-512.svg"
];

function apiCacheKey(request) {
  const dept = request.headers.get("X-User-Id") || "anon";
  const url = new URL(request.url);
  url.searchParams.set("__dept", dept);
  return new Request(url.toString(), { method: "GET" });
}

self.addEventListener("install", function (event) {
  event.waitUntil(
    caches.open(SHELL_CACHE).then(function (cache) {
      return cache.addAll(SHELL);
    }).then(function () {
      return self.skipWaiting();
    })
  );
});

self.addEventListener("activate", function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (key) {
        return key !== SHELL_CACHE && key !== API_CACHE;
      }).map(function (key) {
        return caches.delete(key);
      }));
    }).then(function () {
      return self.clients.claim();
    })
  );
});

self.addEventListener("message", function (event) {
  if (event.data && event.data.type === "CLEAR_API_CACHE") {
    event.waitUntil(caches.delete(API_CACHE));
  }
});

self.addEventListener("fetch", function (event) {
  const request = event.request;
  const url = new URL(request.url);

  if (url.origin !== self.location.origin || request.method !== "GET") return;

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).then(function (response) {
        const copy = response.clone();
        caches.open(SHELL_CACHE).then(function (cache) {
          return cache.put("/index.html", copy);
        });
        return response;
      }).catch(function () {
        return caches.match("/index.html");
      })
    );
    return;
  }

  if (url.pathname.startsWith("/api/")) {
    event.respondWith(
      caches.open(API_CACHE).then(function (cache) {
        const key = apiCacheKey(request);
        return fetch(request).then(function (response) {
          if (response.ok) cache.put(key, response.clone());
          return response;
        }).catch(function () {
          return cache.match(key).then(function (cached) {
            if (cached) return cached;
            return new Response(JSON.stringify({ detail: "Sin conexión" }), {
              status: 503,
              headers: { "Content-Type": "application/json" }
            });
          });
        });
      })
    );
    return;
  }

  event.respondWith(
    caches.match(request).then(function (cached) {
      if (cached) return cached;
      return fetch(request).then(function (response) {
        const copy = response.clone();
        caches.open(SHELL_CACHE).then(function (cache) {
          return cache.put(request, copy);
        });
        return response;
      });
    })
  );
});
