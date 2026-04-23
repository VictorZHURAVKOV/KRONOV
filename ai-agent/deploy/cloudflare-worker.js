/**
 * КРОНОВЪ — прокси Anthropic API через Cloudflare Worker.
 *
 * Зачем: VPS в Беларуси (hoster.by) заблокирован Anthropic по санкциям.
 * Worker крутится в Cloudflare-сети (Европа/США) — запросы идут с их IP.
 *
 * Деплой через веб-UI:
 *   1. dash.cloudflare.com → Workers & Pages → Create → Hello World
 *   2. Скопировать весь этот файл в редактор, заменив дефолтный код
 *   3. Добавить Variable `PROXY_SECRET` (Settings → Variables) — любая длинная строка
 *   4. Save & Deploy → скопировать URL вида https://kronov-claude.<acct>.workers.dev
 *   5. На VPS в .env прописать:
 *        ANTHROPIC_BASE_URL=https://kronov-claude.<acct>.workers.dev
 *        ANTHROPIC_PROXY_SECRET=<тот_же_что_в_CF>
 *   6. systemctl restart kronov-agent
 *
 * Безопасность: Worker принимает запросы только с заголовком
 *   x-proxy-secret: <PROXY_SECRET>
 * иначе 401. Это защищает прокси от случайных левых запросов,
 * которые тратили бы твой бюджет у Anthropic через утёкший прокси-URL.
 *
 * Free-tier Cloudflare: 100 000 запросов/день — для нашего объёма с
 * огромным запасом.
 */

export default {
  async fetch(request, env) {
    // 1. Только /v1/* пути — остальное 404 (не даём прокси ни на что другое)
    const url = new URL(request.url);
    if (!url.pathname.startsWith("/v1/")) {
      return new Response("Not found", { status: 404 });
    }

    // 2. Проверка секрета — защита прокси
    const expected = env.PROXY_SECRET;
    if (!expected) {
      return new Response(
        JSON.stringify({ error: "PROXY_SECRET не задан в Worker Variables" }),
        { status: 500, headers: { "content-type": "application/json" } }
      );
    }
    const got = request.headers.get("x-proxy-secret");
    if (got !== expected) {
      return new Response(
        JSON.stringify({ error: "invalid proxy secret" }),
        { status: 401, headers: { "content-type": "application/json" } }
      );
    }

    // 3. Переписываем URL на Anthropic и убираем наш secret-заголовок
    const target = new URL(url.pathname + url.search, "https://api.anthropic.com");

    const headers = new Headers(request.headers);
    headers.delete("x-proxy-secret");
    // Host header — CF сам поставит, но на всякий случай чистим
    headers.delete("host");
    headers.delete("cf-connecting-ip");
    headers.delete("cf-ray");
    headers.delete("cf-ipcountry");
    headers.delete("cf-visitor");
    headers.delete("x-forwarded-proto");
    headers.delete("x-real-ip");

    // 4. Форвардим. Стриминг/SSE работает прозрачно — fetch() в CF поддерживает.
    const upstream = await fetch(target.toString(), {
      method: request.method,
      headers,
      body: ["GET", "HEAD"].includes(request.method) ? undefined : request.body,
      redirect: "manual",
    });

    // 5. Пробрасываем ответ как есть (включая stream body)
    return new Response(upstream.body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: upstream.headers,
    });
  },
};
