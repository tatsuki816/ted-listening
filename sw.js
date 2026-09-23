// 1回開けば圏外でも動くようにする Service Worker。
// キャッシュ名はページ側（index.html）と揃える。中身を変えたら v を上げる
const キャッシュ名 = "ted-tim-urban-v2";
const 殻 = ["./", "index.html", "manifest.webmanifest", "icon-180.png", "icon-512.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(キャッシュ名).then(c => c.addAll(殻)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) if (k !== キャッシュ名) await caches.delete(k);
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.pathname.endsWith(".mp3")) { e.respondWith(音声(req)); return; }
  if (url.hostname.endsWith("fonts.googleapis.com") || url.hostname.endsWith("fonts.gstatic.com")) {
    e.respondWith(先にキャッシュ(req)); return;
  }
  if (url.origin === location.origin) { e.respondWith(先にネット(req)); return; }
});

// ページ本体は、つながるなら新しい方を取る（直した版がすぐ届くように）。圏外ならキャッシュ
async function 先にネット(req) {
  const c = await caches.open(キャッシュ名);
  try {
    const res = await fetch(req);
    if (res.ok) c.put(req, res.clone());
    return res;
  } catch (err) {
    return (await c.match(req, {ignoreSearch: true}))
        || (req.mode === "navigate" ? (await c.match("./")) || (await c.match("index.html")) : undefined)
        || Response.error();
  }
}

async function 先にキャッシュ(req) {
  const c = await caches.open(キャッシュ名);
  const hit = await c.match(req);
  if (hit) return hit;
  try {
    const res = await fetch(req);
    if (res.ok || res.type === "opaque") c.put(req, res.clone());
    return res;
  } catch (err) { return Response.error(); }
}

// Safari の <audio> は Range 付きで要求してくる。丸ごと 200 で返すと再生できないので、
// 要求された範囲だけ切り出して 206 で返す
async function 音声(req) {
  const c = await caches.open(キャッシュ名);
  const 鍵 = req.url.split("#")[0];
  let res = await c.match(鍵, {ignoreSearch: true});
  if (!res) {
    try {
      res = await fetch(鍵);   // Range を付けずに丸ごと取り、それを貯める
      if (!res.ok) return res;
      await c.put(鍵, res.clone());
    } catch (err) { return Response.error(); }
  }
  const range = req.headers.get("range");
  if (!range) return res;
  const buf = await res.arrayBuffer();
  const 全 = buf.byteLength;
  const m = /bytes=(\d*)-(\d*)/.exec(range);
  let 頭 = m && m[1] !== "" ? parseInt(m[1], 10) : 0;
  let 尻 = m && m[2] !== "" ? parseInt(m[2], 10) : 全 - 1;
  if (m && m[1] === "" && m[2] !== "") { 頭 = Math.max(0, 全 - parseInt(m[2], 10)); 尻 = 全 - 1; }  // bytes=-500
  尻 = Math.min(尻, 全 - 1);
  if (頭 > 尻) return new Response(null, {status: 416, headers: {"Content-Range": `bytes */${全}`}});
  return new Response(buf.slice(頭, 尻 + 1), {
    status: 206,
    headers: {
      "Content-Type": "audio/mpeg",
      "Content-Range": `bytes ${頭}-${尻}/${全}`,
      "Content-Length": String(尻 - 頭 + 1),
      "Accept-Ranges": "bytes",
    },
  });
}
