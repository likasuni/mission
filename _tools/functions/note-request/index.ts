// 분석노트 요청: 카카오 로그인 회원, 1인 하루 1개(한국 시간 기준)
// 공개 구글드라이브 분석노트 폴더에서 파일을 찾아 24시간짜리 링크를 만들고 카카오톡 '나에게 보내기'로 전송
// 파일이 없으면 'missing'으로 기록 → 관리자 페이지에 알림
import { createClient } from 'npm:@supabase/supabase-js@2';

const LINK_HOURS = 24;
const ORIGINS = ['https://data.likasuni.com', 'http://localhost:8765'];
const BOOKS = ['수능특강 라이트']; // 부교재 목록 (이름의 각 단어가 폴더·파일 이름에 들어가야 함)

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

// 공개 폴더 목록 읽기 (하위 폴더 포함, 5분 캐시)
type Entry = { id: string; name: string; path: string[] };
let cache: { at: number; root: string; files: Entry[] } | null = null;
const unescape = (t: string) => t.replace(/&amp;/g, '&').replace(/&#39;/g, "'").replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>');
async function listFolder(id: string) {
  const html = await (await fetch(`https://drive.google.com/embeddedfolderview?id=${id}`)).text();
  const out: { id: string; name: string; folder: boolean }[] = [];
  const re = /<div class="flip-entry" id="entry-([\w-]+)"[\s\S]*?<a href="([^"]+)"[\s\S]*?<div class="flip-entry-title">([^<]*)<\/div>/g;
  let m;
  while ((m = re.exec(html))) out.push({ id: m[1], name: unescape(m[3]).trim(), folder: m[2].includes('/folders/') });
  return out;
}
async function listTree(root: string): Promise<Entry[]> {
  if (cache && cache.root === root && Date.now() - cache.at < 5 * 60e3) return cache.files;
  const files: Entry[] = [];
  const queue = root.split(',').map((x) => x.trim()).filter(Boolean).map((id) => ({ id, path: [] as string[] }));
  let seen = 0;
  while (queue.length && seen < 200) {
    const batch = queue.splice(0, 10); seen += batch.length;
    const lists = await Promise.all(batch.map((f) => listFolder(f.id).catch(() => [])));
    lists.forEach((l, i) => {
      for (const e of l) e.folder ? queue.push({ id: e.id, path: [...batch[i].path, e.name] }) : files.push({ id: e.id, name: e.name, path: batch[i].path });
    });
  }
  cache = { at: Date.now(), root, files };
  return files;
}
// 파일 이름에 번호가 있는지: '30번', '41-42번', 또는 이름 자체가 '30.pdf', '41-42.pdf'
function hasNum(name: string, n: number) {
  if (n === 0) return /gateway|게이트웨이/i.test(name); // 부교재 Gateway
  const re = /(\d+)\s*(?:[-~]\s*(\d+))?\s*번/g;
  let m;
  while ((m = re.exec(name))) { const a = +m[1], b = m[2] ? +m[2] : a; if (n >= a && n <= b) return true; }
  const bare = name.match(/^(\d+)\s*(?:[-~]\s*(\d+))?\s*\.pdf$/i);
  if (bare) { const a = +bare[1], b = bare[2] ? +bare[2] : a; return n >= a && n <= b; }
  return false;
}
// 모의고사 회차: 파일 이름(2026-09_고1_…) 또는 폴더 이름(2026년 9월 고1)에서 읽음
function moeKey(f: Entry): number[] | null {
  let m = f.name.match(/^(\d{4})-(\d{2})_고(\d)/);
  if (m) return [+m[1], +m[2], +m[3]];
  for (const p of [...f.path].reverse()) {
    m = p.match(/(\d{4})\s*년\s*(\d{1,2})\s*월\s*고\s*(\d)/);
    if (m) return [+m[1], +m[2], +m[3]];
  }
  return null;
}

const esc = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: cors(req) });
  if (req.method !== 'POST') return reply(req, 405, { error: 'POST only' });
  const db = createClient(Deno.env.get('SUPABASE_URL')!, Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!);

  const jwt = (req.headers.get('Authorization') || '').replace('Bearer ', '');
  const { data: { user } } = await db.auth.getUser(jwt);
  if (!user) return reply(req, 401, { error: '로그인이 필요해요.' });
  const providers: string[] = user.app_metadata?.providers || [user.app_metadata?.provider];
  if (!providers.includes('kakao')) return reply(req, 403, { error: '카카오로 로그인한 회원만 요청할 수 있어요.' });

  let b: any = {};
  try { b = await req.json(); } catch { /* empty */ }
  const n = Number(b.n);
  if (!(n >= (b.kind === 'book' ? 0 : 1) && n <= 60)) return reply(req, 400, { error: '문항 번호를 확인해 주세요.' });

  // 요청 → 검색 조건
  let label = '', must: string[] = [], query: any = {};
  if (b.kind === 'moe') {
    const y = Number(b.y), m = Number(b.m), g = Number(b.g);
    if (!(y >= 2015 && y <= 2030 && m >= 1 && m <= 12 && g >= 1 && g <= 3)) return reply(req, 400, { error: '회차를 확인해 주세요.' });
    label = `${y}년 ${m}월 고${g} 영어 모의고사 ${n}번 분석노트`;
    query = { y, m, g, n };
  } else if (b.kind === 'book') {
    const book = String(b.book || ''), unit = Number(b.unit);
    if (!BOOKS.includes(book) || !(unit >= 1 && unit <= 60)) return reply(req, 400, { error: '교재와 강을 확인해 주세요.' });
    label = `${book} ${unit}강 ${n === 0 ? 'Gateway' : n + '번'} 분석노트`;
    const words = book.split(/\s+/);
    must = [...words.map(esc), `(^|\\D)${unit}\\s*강`];
    query = { book, unit, n };
  } else return reply(req, 400, { error: '요청 종류를 확인해 주세요.' });

  // 하루 1개 (한국 시간 자정 기준, 실제로 받은 요청만 계산)
  const kst = new Date(Date.now() + 9 * 3600e3);
  const dayStart = new Date(Date.UTC(kst.getUTCFullYear(), kst.getUTCMonth(), kst.getUTCDate()) - 9 * 3600e3).toISOString();
  const { count } = await db.from('note_orders').select('id', { count: 'exact', head: true })
    .eq('user_id', user.id).eq('status', 'sent').gte('created_at', dayStart);
  if ((count || 0) >= 1) return reply(req, 429, { error: '분석노트는 하루에 1개만 받을 수 있어요. 내일 다시 요청해 주세요.' });

  // 공개 드라이브 폴더(분석노트 폴더)에서 찾기
  const { data: cfg } = await db.from('private_config').select('k,v').eq('k', 'notes_root').maybeSingle();
  if (!cfg?.v) return reply(req, 503, { error: '자료 연결 준비 중이에요. 잠시 후 다시 시도해 주세요.' });
  const all = await listTree(cfg.v);
  const words = must.slice(0, -1).map((x) => new RegExp(x)), unitRe = new RegExp(must[must.length - 1] || '$^');
  const files = all.filter((f) => {
    if (!/\.pdf$/i.test(f.name) || /문제|정답|해설|듣기/.test(f.name)) return false;
    if (b.kind === 'moe') { const k = moeKey(f); return hasNum(f.name, n) && !!k && k[0] === query.y && k[1] === query.m && k[2] === query.g; }
    const full = [...f.path, f.name].join(' ');
    if (!words.every((re) => re.test(full))) return false;
    // 부교재 파일 이름 '강-번호.pdf' (0 = Gateway) 예: 1-0.pdf, 20-3.pdf
    const ku = f.name.match(/^(\d+)\s*-\s*(\d+)\s*\.pdf$/i);
    if (ku) return +ku[1] === query.unit && +ku[2] === n;
    return hasNum(f.name, n) && unitRe.test(full); // 또는 '1강' 폴더 안 '1.pdf', 'gateway.pdf'
  });

  const name = user.user_metadata?.full_name || user.user_metadata?.name || user.user_metadata?.nickname || '회원';
  if (!files.length) {
    await db.from('note_orders').insert({ user_id: user.id, author_name: name, kind: b.kind, label, query, status: 'missing' });
    return reply(req, 200, { missing: true, label });
  }

  const f = files[0];
  const token = Array.from(crypto.getRandomValues(new Uint8Array(16))).map((x) => x.toString(16).padStart(2, '0')).join('');
  const expires = new Date(Date.now() + LINK_HOURS * 3600e3);
  const link = `https://data.likasuni.com/get/?t=${token}`;

  // 카카오톡 나에게 보내기
  let kakao = false, kakaoError = '';
  if (b.kakao_token) {
    const until = new Date(expires.getTime() + 9 * 3600e3).toISOString().slice(5, 16).replace('-', '/').replace('T', ' ');
    const template = {
      object_type: 'text',
      text: `[리카수니 자료실]\n${label}가 도착했어요 📘\n\n링크는 ${until}까지(24시간) 열 수 있어요.`,
      link: { web_url: link, mobile_web_url: link },
      button_title: '분석노트 받기',
    };
    const k = await fetch('https://kapi.kakao.com/v2/api/talk/memo/default/send', {
      method: 'POST',
      headers: { Authorization: `Bearer ${b.kakao_token}`, 'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8' },
      body: new URLSearchParams({ template_object: JSON.stringify(template) }),
    });
    kakao = k.ok;
    if (!k.ok) { kakaoError = await k.text(); console.log('kakao send fail', k.status, kakaoError); }
  }

  await db.from('note_orders').insert({
    user_id: user.id, author_name: name, kind: b.kind, label, query, status: 'sent',
    drive_id: f.id, file_name: [...f.path, f.name].join('/'), link_token: token, expires_at: expires.toISOString(), kakao_sent: kakao,
  });
  return reply(req, 200, { ok: true, label, link, expires_at: expires.toISOString(), kakao, kakao_scope: kakaoError.includes('insufficient') || kakaoError.includes('-402') });
});
