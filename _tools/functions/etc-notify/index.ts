// 기타 자료 요청 → 원장님이 관리자 페이지에서 '준비 완료 · 카톡 보내기'를 누르면 요청한 학생에게 카톡 '나와의 채팅'으로 보냄
// 요청은 comments 의 '[자료 요청] 기타 · <자료> 부탁드려요.' 글. 링크는 원장님이 넣은 주소(드라이브 등), 없으면 기타 자료 드라이브 폴더(ETC_FOLDER)
// 카카오 토큰은 kakao_tokens (note-deliver 와 같은 방식으로 새로 받음). 관리자만 부를 수 있음
import { createClient } from 'npm:@supabase/supabase-js@2';
// 기타 자료 요청 자료실 (구글 드라이브 공유 폴더, 2026-10-31 원장님). 원장님이 만든 자료를 여기에 올리고 카톡으로 이 폴더를 보내요
const ETC_FOLDER = 'https://drive.google.com/drive/folders/1FryHlXrnXc7gzP8e3xQrM-TBR6L-KkXY?usp=sharing'; // 실제 이동은 /get/etc/ 페이지가 해요
const ETC_GO = 'https://data.likasuni.com/get/etc/';

const ORIGINS = ['https://data.likasuni.com', 'http://localhost:8765'];
const cors = (req: Request) => {
  const o = req.headers.get('origin') || '';
  return { 'Access-Control-Allow-Origin': ORIGINS.includes(o) ? o : ORIGINS[0], 'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type', 'Access-Control-Allow-Methods': 'POST, OPTIONS', 'Vary': 'Origin' };
};
const reply = (req: Request, status: number, body: unknown) => new Response(JSON.stringify(body), { status, headers: { ...cors(req), 'Content-Type': 'application/json' } });

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: cors(req) });
  const db = createClient(Deno.env.get('SUPABASE_URL')!, Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!);
  const { data: { user } } = await db.auth.getUser((req.headers.get('Authorization') || '').replace('Bearer ', ''));
  if (!user) return reply(req, 401, { error: '로그인이 필요해요.' });
  const { count: adm } = await db.from('admins').select('user_id', { count: 'exact', head: true }).eq('user_id', user.id);
  if (!adm) return reply(req, 403, { error: '관리자만 쓸 수 있어요.' });
  let b: any = {};
  try { b = await req.json(); } catch { /* empty */ }

  const { data: c } = await db.from('comments').select('id,user_id,content').eq('id', Number(b.id)).maybeSingle();
  if (!c || !c.content.startsWith('[자료 요청] 기타 ·')) return reply(req, 404, { error: '기타 자료 요청 글이 아니에요.' });
  const label = c.content.replace('[자료 요청] 기타 · ', '').replace(' 부탁드려요.', '');
  // 카톡 버튼은 카카오에 등록한 도메인만 열려서, 드라이브 주소는 자료실 /get/etc/ 를 거쳐 넘겨요 (비우면 기타 자료 폴더)
  const raw = String(b.link || '').trim();
  const link = !/^https?:\/\//.test(raw) ? ETC_GO : raw.startsWith('https://data.likasuni.com/') ? raw : `${ETC_GO}?u=${encodeURIComponent(raw)}`;
  const memo = String(b.memo || '').trim().slice(0, 120);

  // 카카오 토큰 (만료 10분 전이면 새로 받음)
  let sent = false, why = '';
  const { data: tk } = await db.from('kakao_tokens').select('*').eq('user_id', c.user_id).maybeSingle();
  let access: string | null = tk?.access_token || null;
  if (!tk) why = 'no_token';
  else if (!access || !tk.access_expires || new Date(tk.access_expires).getTime() < Date.now() + 10 * 60e3) {
    const REST = Deno.env.get('KAKAO_REST_KEY') || '', SECRET = Deno.env.get('KAKAO_CLIENT_SECRET') || '';
    const p = new URLSearchParams({ grant_type: 'refresh_token', client_id: REST, refresh_token: tk.refresh_token });
    if (SECRET) p.set('client_secret', SECRET);
    const r = await fetch('https://kauth.kakao.com/oauth/token', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8' }, body: p });
    const j = await r.json().catch(() => ({}));
    if (r.ok && j.access_token) {
      access = j.access_token;
      await db.from('kakao_tokens').update({ access_token: access, access_expires: new Date(Date.now() + (j.expires_in || 3600) * 1000).toISOString(),
        ...(j.refresh_token ? { refresh_token: j.refresh_token } : {}), updated_at: new Date().toISOString() }).eq('user_id', c.user_id);
    } else { access = null; why = 'fail'; }
  }
  if (access) {
    const text = `[리카수니 자료실]\n요청하신 ${label} 준비됐어요 📘` + (memo ? `\n\n${memo}` : '');
    const k = await fetch('https://kapi.kakao.com/v2/api/talk/memo/default/send', {
      method: 'POST', headers: { Authorization: `Bearer ${access}`, 'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8' },
      body: new URLSearchParams({ template_object: JSON.stringify({ object_type: 'text', text: text.slice(0, 200), link: { web_url: link, mobile_web_url: link }, button_title: '자료 받기' }) }),
    });
    sent = k.ok;
    if (!k.ok) { const err = await k.text(); why = /-402|insufficient/.test(err) ? 'no_consent' : 'fail'; console.log('kakao fail', err); }
  }
  // 답글: 보냈으면 '보내 드렸어요'(초록), 못 보냈으면 '준비됐어요'(파랑) + 받는 방법
  const r = sent ? `${label} 준비돼서 카카오톡으로 보내 드렸어요. 공부에 도움이 되면 좋겠어요!`
    : `${label} 준비됐어요! 카톡을 보내지 못했어요${why === 'no_consent' ? '(카톡 받기 동의가 꺼져 있어요)' : ''}. 자료실에 카카오로 로그인해서 '소통하기'로 말씀해 주시면 바로 보내 드릴게요.`;
  await db.from('comments').update({ reply: r, replied_at: new Date().toISOString(), approved: true }).eq('id', c.id);
  return reply(req, 200, { ok: true, sent, why });
});
