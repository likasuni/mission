// 새 자료 웹 푸시 알림 (외부 서비스 없이 VAPID 직접 발송)
//   key         공개키 돌려줌 (처음 부를 때 키 한 쌍을 만들어 private_config 에 보관, 비밀키는 서버 밖으로 안 나감)
//   subscribe   학생 브라우저의 구독 정보 저장 (서버 전용 테이블 push_subs)
//   unsubscribe 구독 삭제
//   send        모든 구독자에게 발송 (x-cron-key 필요: 원장님 '완료' 때 SQL 로 호출). 끊긴 구독(404·410)은 지움
import { createClient } from 'npm:@supabase/supabase-js@2';
import webpush from 'npm:web-push@3.6.7';

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

// 브라우저 푸시 서버 주소만 받음 (크롬·엣지·파이어폭스·사파리)
const PUSH_HOSTS = [/(^|\.)fcm\.googleapis\.com$/, /(^|\.)push\.services\.mozilla\.com$/, /(^|\.)notify\.windows\.com$/, /(^|\.)push\.apple\.com$/];

async function vapid(db: any) {
  const { data } = await db.from('private_config').select('k,v').in('k', ['vapid_public', 'vapid_private']);
  let pub = data?.find((x: any) => x.k === 'vapid_public')?.v, priv = data?.find((x: any) => x.k === 'vapid_private')?.v;
  if (!pub || !priv) {
    const k = webpush.generateVAPIDKeys();
    await db.from('private_config').upsert([{ k: 'vapid_public', v: k.publicKey }, { k: 'vapid_private', v: k.privateKey }]);
    pub = k.publicKey; priv = k.privateKey;
  }
  return { pub, priv };
}

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: cors(req) });
  if (req.method !== 'POST') return reply(req, 405, { error: 'POST only' });
  const db = createClient(Deno.env.get('SUPABASE_URL')!, Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!);
  let b: any = {};
  try { b = await req.json(); } catch { /* empty */ }

  if (b.action === 'key') return reply(req, 200, { key: (await vapid(db)).pub });

  if (b.action === 'subscribe' || b.action === 'unsubscribe') {
    const s = b.sub || {}, ep = String(s.endpoint || '');
    let host = '';
    try { const u = new URL(ep); if (u.protocol === 'https:') host = u.hostname; } catch { /* bad */ }
    if (!host || !PUSH_HOSTS.some((re) => re.test(host)) || ep.length > 1000) return reply(req, 400, { error: 'endpoint' });
    if (b.action === 'unsubscribe') { await db.from('push_subs').delete().eq('endpoint', ep); return reply(req, 200, { ok: true }); }
    const p256dh = String(s.keys?.p256dh || ''), auth = String(s.keys?.auth || '');
    if (!p256dh || !auth || p256dh.length > 200 || auth.length > 100) return reply(req, 400, { error: 'keys' });
    await db.from('push_subs').upsert({ endpoint: ep, p256dh, auth, ua: String(req.headers.get('user-agent') || '').slice(0, 200), updated_at: new Date().toISOString() });
    return reply(req, 200, { ok: true });
  }

  if (b.action === 'send') {
    const { data: keyRow } = await db.from('private_config').select('v').eq('k', 'cron_key').maybeSingle();
    if (!keyRow?.v || req.headers.get('x-cron-key') !== keyRow.v) return reply(req, 403, { error: 'forbidden' });
    const title = String(b.title || '리카수니 자료실').slice(0, 80), body = String(b.body || '새 자료가 올라왔어요').slice(0, 200);
    const url = String(b.url || '/').startsWith('/') ? 'https://data.likasuni.com' + String(b.url || '/') : 'https://data.likasuni.com/';
    const { pub, priv } = await vapid(db);
    webpush.setVapidDetails('https://data.likasuni.com', pub, priv);
    const { data: subs } = await db.from('push_subs').select('endpoint,p256dh,auth').limit(5000);
    const payload = JSON.stringify({ title, body, url });
    let sent = 0, gone = 0, fail = 0;
    for (let i = 0; i < (subs || []).length; i += 50) {
      await Promise.all(subs!.slice(i, i + 50).map(async (s: any) => {
        try {
          await webpush.sendNotification({ endpoint: s.endpoint, keys: { p256dh: s.p256dh, auth: s.auth } }, payload, { TTL: 86400 });
          sent++;
        } catch (e: any) {
          if (e?.statusCode === 404 || e?.statusCode === 410) { gone++; await db.from('push_subs').delete().eq('endpoint', s.endpoint); }
          else { fail++; console.log('push fail', e?.statusCode, String(e?.body || e).slice(0, 120)); }
        }
      }));
    }
    await db.from('push_log').insert({ title, body, url, sent, gone, fail });
    return reply(req, 200, { ok: true, total: subs?.length || 0, sent, gone, fail });
  }
  return reply(req, 400, { error: 'action' });
});
