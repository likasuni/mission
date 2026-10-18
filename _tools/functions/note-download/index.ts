// 분석노트 링크 열기: GET ?t=토큰 → 유효기간(24시간) 확인 → 공개 구글드라이브에서 파일을 가져와 PDF로 전달
import { createClient } from 'npm:@supabase/supabase-js@2';

// 오류는 자료실 안내 페이지로 보냄 (Supabase 함수는 HTML 화면을 그대로 보여주지 못함)
function page(_status: number, code: string) {
  return new Response(null, { status: 302, headers: { Location: `https://data.likasuni.com/get/?e=${code}` } });
}

Deno.serve(async (req) => {
  if (req.method !== 'GET') return page(405, 'bad');
  const t = new URL(req.url).searchParams.get('t') || '';
  if (!/^[a-f0-9]{32}$/.test(t)) return page(400, 'bad');
  const db = createClient(Deno.env.get('SUPABASE_URL')!, Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!);

  const { data: o } = await db.from('note_orders').select('label,drive_id,file_name,expires_at,status').eq('link_token', t).maybeSingle();
  if (!o || o.status !== 'sent' || !o.drive_id) return page(404, 'notfound');
  if (Date.now() > new Date(o.expires_at).getTime()) return page(410, 'expired');

  // 분석노트 폴더는 비공개 → 원장님 계정의 Apps Script로 파일을 받아 옴 (설정 전이면 공개 다운로드)
  const { data: g } = await db.from('private_config').select('k,v').in('k', ['gas_url', 'gas_key']);
  const url = g?.find((x: any) => x.k === 'gas_url')?.v, key = g?.find((x: any) => x.k === 'gas_key')?.v;
  let body: BodyInit | null = null;
  if (url && key) {
    const j = await (await fetch(`${url}?action=get&id=${encodeURIComponent(o.drive_id)}&key=${encodeURIComponent(key)}`)).json().catch(() => null);
    if (j?.b64) body = Uint8Array.from(atob(j.b64), (c) => c.charCodeAt(0));
    else console.log('gas get failed', j?.error);
  }
  if (!body) {
    const r = await fetch(`https://drive.usercontent.google.com/download?id=${encodeURIComponent(o.drive_id)}&export=download&confirm=t`);
    const type = r.headers.get('content-type') || '';
    if (!r.ok || type.includes('text/html')) { console.log('drive fetch failed', r.status, type); return page(502, 'fail'); }
    body = r.body;
  }
  const name = `${o.label}.pdf`;
  return new Response(body, {
    headers: {
      'Content-Type': 'application/pdf',
      'Content-Disposition': `inline; filename="note.pdf"; filename*=UTF-8''${encodeURIComponent(name)}`,
      'Cache-Control': 'no-store',
    },
  });
});
