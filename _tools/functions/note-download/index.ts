// 분석노트 링크 열기: GET ?t=토큰 → 유효기간(24시간) 확인 → 구글드라이브(앱스 스크립트)에서 파일을 가져와 PDF로 전달
import { createClient } from 'npm:@supabase/supabase-js@2';

function page(status: number, msg: string) {
  const html = `<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>리카수니 자료실</title>
<body style="font-family:sans-serif;padding:40px 20px;text-align:center;color:#172554"><h2>리카수니 자료실</h2><p>${msg}</p>
<p><a href="https://data.likasuni.com/" style="color:#1e3a8a">자료실로 가기</a></p></body>`;
  return new Response(html, { status, headers: { 'Content-Type': 'text/html; charset=utf-8' } });
}

Deno.serve(async (req) => {
  if (req.method !== 'GET') return page(405, '지원하지 않는 요청이에요.');
  const t = new URL(req.url).searchParams.get('t') || '';
  if (!/^[a-f0-9]{32}$/.test(t)) return page(400, '잘못된 링크예요.');
  const db = createClient(Deno.env.get('SUPABASE_URL')!, Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!);

  const { data: o } = await db.from('note_orders').select('label,drive_id,file_name,expires_at,status').eq('link_token', t).maybeSingle();
  if (!o || o.status !== 'sent' || !o.drive_id) return page(404, '링크를 찾을 수 없어요.');
  if (Date.now() > new Date(o.expires_at).getTime()) return page(410, '링크 사용 기간(24시간)이 지났어요. 자료실에서 다시 요청해 주세요.');

  const { data: cfg } = await db.from('private_config').select('k,v').in('k', ['gas_url', 'gas_key']);
  const c = Object.fromEntries((cfg || []).map((r: any) => [r.k, r.v]));
  const u = new URL(c.gas_url);
  u.searchParams.set('key', c.gas_key); u.searchParams.set('action', 'get'); u.searchParams.set('id', o.drive_id);
  let r: any = {};
  try { r = await (await fetch(u)).json(); } catch (e) { console.log('gas get error', String(e)); }
  if (!r.b64) return page(502, '파일을 가져오지 못했어요. 잠시 후 다시 시도해 주세요.');

  const bytes = Uint8Array.from(atob(r.b64), (ch) => ch.charCodeAt(0));
  const name = `${o.label}.pdf`;
  return new Response(bytes, {
    headers: {
      'Content-Type': 'application/pdf',
      'Content-Disposition': `inline; filename="note.pdf"; filename*=UTF-8''${encodeURIComponent(name)}`,
      'Cache-Control': 'no-store',
    },
  });
});
