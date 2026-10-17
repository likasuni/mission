// 카카오 로그인 직후 받은 카카오 토큰을 보관 (요청 자료가 준비되면 카톡으로 자동 발송하기 위해)
// 서버 전용 테이블 kakao_tokens 에 저장 — 관리자 화면에서도 보이지 않음
import { createClient } from 'npm:@supabase/supabase-js@2';

const ORIGINS = ['https://data.likasuni.com', 'http://localhost:8765'];
const cors = (req: Request) => {
  const o = req.headers.get('origin') || '';
  return {
    'Access-Control-Allow-Origin': ORIGINS.includes(o) ? o : ORIGINS[0],
    'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Vary': 'Origin',
  };
};
const reply = (req: Request, status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { ...cors(req), 'Content-Type': 'application/json' } });

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: cors(req) });
  if (req.method !== 'POST') return reply(req, 405, { error: 'POST only' });
  const db = createClient(Deno.env.get('SUPABASE_URL')!, Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!);
  const jwt = (req.headers.get('Authorization') || '').replace('Bearer ', '');
  const { data: { user } } = await db.auth.getUser(jwt);
  if (!user) return reply(req, 401, { error: 'login' });
  const providers: string[] = user.app_metadata?.providers || [user.app_metadata?.provider];
  if (!providers.includes('kakao')) return reply(req, 200, { ok: false });

  let b: any = {};
  try { b = await req.json(); } catch { /* empty */ }
  const refresh = String(b.refresh_token || ''), access = String(b.access_token || '');
  if (refresh.length < 20) return reply(req, 400, { error: 'token' });

  // 이 토큰이 실제로 이 카카오 계정 것인지 확인 (카카오에 토큰 정보 조회)
  if (access) {
    const k = await fetch('https://kapi.kakao.com/v1/user/access_token_info', { headers: { Authorization: `Bearer ${access}` } });
    if (!k.ok) return reply(req, 400, { error: 'invalid' });
    const info = await k.json();
    const kakaoId = String(user.user_metadata?.provider_id || user.user_metadata?.sub || '');
    if (kakaoId && String(info.id) !== kakaoId) return reply(req, 403, { error: 'mismatch' });
  }
  await db.from('kakao_tokens').upsert({
    user_id: user.id, refresh_token: refresh,
    access_token: access || null, access_expires: access ? new Date(Date.now() + 5 * 3600e3).toISOString() : null,
    updated_at: new Date().toISOString(),
  });
  return reply(req, 200, { ok: true });
});
