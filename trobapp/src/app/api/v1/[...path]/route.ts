// Runtime proxy for /api/v1/* → FastAPI backend.
// Done at request time (not as a build-time rewrite) so the backend address can be set via
// BACKEND_API_URL in the host panel, and so we can try Liara's private-network hostname first:
// public *.liara.run names do not resolve from inside Liara containers.
import { NextRequest } from 'next/server';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

const CANDIDATES = [
  process.env.BACKEND_API_URL,
  'http://torobmap-api:8080',
  'https://torobmap-api.liara.run',
  'http://127.0.0.1:8080',
].filter((u, i, a): u is string => !!u && a.indexOf(u) === i);

const FORWARD_HEADERS = ['content-type', 'accept', 'authorization', 'x-user-role', 'x-user-id', 'x-shop-id', 'x-correlation-id'];

let working: string | null = null;

async function proxy(req: NextRequest, { params }: { params: { path: string[] } }) {
  const suffix = `/api/v1/${params.path.map(encodeURIComponent).join('/')}${req.nextUrl.search}`;
  const headers: Record<string, string> = {};
  for (const h of FORWARD_HEADERS) {
    const v = req.headers.get(h);
    if (v) headers[h] = v;
  }
  const body = req.method === 'GET' || req.method === 'HEAD' ? undefined : await req.arrayBuffer();
  const order = working ? [working, ...CANDIDATES.filter((c) => c !== working)] : CANDIDATES;

  for (const base of order) {
    try {
      const res = await fetch(base + suffix, { method: req.method, headers, body, cache: 'no-store', signal: AbortSignal.timeout(60000) });
      working = base;
      return new Response(res.body, {
        status: res.status,
        headers: { 'content-type': res.headers.get('content-type') || 'application/json' },
      });
    } catch (err) {
      console.warn(`[api-proxy] ${base} unreachable:`, (err as Error).message);
      if (working === base) working = null;
    }
  }
  return Response.json({ detail: 'Backend unreachable', tried: order }, { status: 502 });
}

export { proxy as GET, proxy as POST, proxy as PUT, proxy as PATCH, proxy as DELETE };
