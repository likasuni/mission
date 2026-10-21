// 분석노트 요청: 카카오 로그인 회원, 하루 모의고사 2개 · 부교재 1개 (한국 시간 기준)
// 구글드라이브 분석노트 폴더에서 파일을 찾아 24시간짜리 링크를 만들고 카카오톡 '나에게 보내기'로 전송
// 파일이 없으면 'missing'으로 기록 → 관리자 페이지에 알림
import { createClient } from 'npm:@supabase/supabase-js@2';

const LINK_HOURS = 24;
const LIMIT: Record<string, number> = { moe: 2, book: 1 }; // 하루에 받을 수 있는 개수 (lib.js NOTE_LIMIT 와 같게)
const LIMIT_MSG: Record<string, string> = { moe: '모의고사 분석노트는 하루 2개', book: '부교재 분석노트는 하루 1개' };
const ORIGINS = ['https://data.likasuni.com', 'http://localhost:8765'];
// 부교재 목록 → 단위(강/회). 이름의 각 단어가 드라이브 폴더 이름에 들어가야 함 (lib.js NOTE_BOOK_CFG 와 같게)
const BOOKS: Record<string, string> = { '수능특강 라이트': '강', '리딩파워 기본': '강', '리딩파워 완성': '강', '올림포스 영어독해 기본1': '강', '하루 6개 1등급 모의고사 고1': '회', '하루 6개 1등급 모의고사 고2': '회', '올림포스 전국연합학력평가 기출문제집 고1': '회', '올림포스 전국연합학력평가 기출문제집 고2': '회' };

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
// 분석노트 폴더는 비공개 → 원장님 계정의 Apps Script(gas_url, 비밀키 gas_key)로 목록을 받음. 설정 전이면 공개 폴더 방식
async function listTree(root: string, db?: any): Promise<Entry[]> {
  if (cache && cache.root === root && Date.now() - cache.at < 5 * 60e3) return cache.files;
  if (db) {
    const { data: g } = await db.from('private_config').select('k,v').in('k', ['gas_url', 'gas_key']);
    const url = g?.find((x: any) => x.k === 'gas_url')?.v, key = g?.find((x: any) => x.k === 'gas_key')?.v;
    if (url && key) {
      const j = await (await fetch(`${url}?action=list&key=${encodeURIComponent(key)}`)).json().catch(() => null);
      if (j?.files) { // 맨 앞 폴더 이름(모의고사 분석노트/부교재 분석노트)은 빼서 예전 목록과 같은 모양으로
        const files = j.files.map((f: any) => ({ id: f.id, name: f.name, path: f.path.slice(1) }));
        cache = { at: Date.now(), root, files }; return files;
      }
      console.log('gas list fail');
    }
  }
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

// 요청 → 라벨·검색 조건
type Spec = { kind: string; label: string; query: any; words: RegExp[]; unitRe: RegExp; n: number };
function makeSpec(b: any): Spec | { error: string } {
  const n = Number(b.n);
  if (b.kind === 'moe') {
    const y = Number(b.y), m = Number(b.m), g = Number(b.g);
    if (!(y >= 2015 && y <= 2030 && m >= 1 && m <= 12 && g >= 1 && g <= 3)) return { error: '회차를 확인해 주세요.' };
    return { kind: 'moe', label: `${y}년 ${m}월 고${g} 영어 모의고사 ${n}번 분석노트`, query: { y, m, g, n }, words: [], unitRe: /$^/, n };
  }
  if (b.kind === 'book') {
    const book = String(b.book || ''), unit = Number(b.unit);
    if (!BOOKS[book] || !(unit >= 1 && unit <= 60)) return { error: '교재와 강을 확인해 주세요.' };
    return { kind: 'book', label: `${book} ${unit}${BOOKS[book]} ${n === 0 ? 'Gateway' : n + '번'} 분석노트`, query: { book, unit, n },
      words: book.split(/\s+/).map((w) => new RegExp(esc(w))), unitRe: new RegExp(`(^|\\D)${unit}\\s*${BOOKS[book]}`), n };
  }
  return { error: '요청 종류를 확인해 주세요.' };
}
function findFiles(all: Entry[], sp: Spec) {
  const { n, query } = sp;
  return all.filter((f) => {
    if (!/\.pdf$/i.test(f.name) || /문제|정답|해설|듣기/.test(f.name)) return false;
    if (sp.kind === 'moe') { const k = moeKey(f); return hasNum(f.name, n) && !!k && k[0] === query.y && k[1] === query.m && k[2] === query.g; }
    const full = [...f.path, f.name].join(' ');
    if (!sp.words.every((re) => re.test(full))) return false;
    // 부교재 파일 이름 '강-번호.pdf' (0 = Gateway) 예: 1-0.pdf, 20-3.pdf
    const ku = f.name.match(/^(\d+)\s*-\s*(\d+)\s*\.pdf$/i);
    if (ku) return +ku[1] === query.unit && +ku[2] === n;
    return hasNum(f.name, n) && sp.unitRe.test(full); // 또는 '1강' 폴더 안 '1.pdf', 'gateway.pdf'
  });
}

// 오늘(한국 시간) 받은 개수: 종류별
async function todayCounts(db: any, uid: string) {
  const kst = new Date(Date.now() + 9 * 3600e3);
  const dayStart = new Date(Date.UTC(kst.getUTCFullYear(), kst.getUTCMonth(), kst.getUTCDate()) - 9 * 3600e3).toISOString();
  const { data } = await db.from('note_orders').select('kind').eq('user_id', uid).eq('status', 'sent').gte('created_at', dayStart);
  const c: Record<string, number> = { moe: 0, book: 0 };
  for (const r of data || []) c[r.kind] = (c[r.kind] || 0) + 1;
  return c;
}

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: cors(req) });
  if (req.method !== 'POST') return reply(req, 405, { error: 'POST only' });
  const db = createClient(Deno.env.get('SUPABASE_URL')!, Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!);

  const jwt = (req.headers.get('Authorization') || '').replace('Bearer ', '');
  const { data: { user } } = await db.auth.getUser(jwt);
  if (!user) return reply(req, 401, { error: '로그인이 필요해요.' });
  let b: any = {};
  try { b = await req.json(); } catch { /* empty */ }

  // 관리자 '드라이브 확인': 없는 자료 요청(missing)을 드라이브와 다시 맞춰 봄 (관리자는 구글 로그인이어도 됨)
  // 파일이 있으면 '준비 완료'(resolved)로 바꾸고 요청 댓글 답글도 '준비됐어요'로. 없으면 같은 회차·교재 폴더의 파일 이름을 보여 줌 (이름 오류 찾기)
  if (b.kind === 'admin_scan') {
    const { count: adm } = await db.from('admins').select('user_id', { count: 'exact', head: true }).eq('user_id', user.id);
    if (!adm) return reply(req, 403, { error: '관리자만 쓸 수 있어요.' });
    const { data: cfg } = await db.from('private_config').select('k,v').eq('k', 'notes_root').maybeSingle();
    if (!cfg?.v) return reply(req, 503, { error: 'notes_root 설정이 없어요.' });
    cache = null; // 방금 올린 파일도 보이게
    const all = await listTree(cfg.v, db);
    const { data: waits } = await db.from('note_orders').select('user_id,kind,label,query').eq('status', 'missing').limit(500);
    const out = new Map<string, any>();
    for (const w of waits || []) {
      const spec = makeSpec({ kind: w.kind, ...(w.query || {}) });
      if ('error' in spec) continue;
      const files = findFiles(all, spec);
      const r = out.get(w.label) || { label: w.label, n: 0, file: '', near: [] as string[] };
      r.n++;
      if (files.length) {
        r.file = [...files[0].path, files[0].name].join('/');
        await db.from('note_orders').update({ status: 'resolved' }).eq('user_id', w.user_id).eq('label', w.label).eq('status', 'missing');
        await db.from('comments').update({ reply: `${w.label} 준비됐어요! 자료실에 카카오로 로그인해서 '카톡으로 받기'를 누르면 바로 받을 수 있어요.`, replied_at: new Date().toISOString() })
          .eq('user_id', w.user_id).eq('content', `[자료 요청] ${w.label} 부탁드려요.`).like('reply', '%접수했어요%');
      } else if (!r.near.length) {
        const q = spec.query;
        r.near = all.filter((f) => {
          if (spec.kind === 'moe') { const k = moeKey(f); return !!k && k[0] === q.y && k[1] === q.m && k[2] === q.g; }
          const full = [...f.path, f.name].join(' ');
          return spec.words.every((re) => re.test(full)) && spec.unitRe.test(full);
        }).slice(0, 8).map((f) => [...f.path, f.name].join('/'));
      }
      out.set(w.label, r);
    }
    const list = [...out.values()];
    return reply(req, 200, { ready: list.filter((x) => x.file), missing: list.filter((x) => !x.file) });
  }

  const providers: string[] = user.app_metadata?.providers || [user.app_metadata?.provider];
  if (!providers.includes('kakao')) return reply(req, 403, { error: '카카오로 로그인한 회원만 요청할 수 있어요.' });

  const name = user.user_metadata?.full_name || user.user_metadata?.name || user.user_metadata?.nickname || '회원';

  // 준비된 자료 확인: 이 회원이 요청했지만 그때 없던 자료 중, 지금 드라이브에 올라온 것 (알림용, 횟수 차감 없음)
  if (b.kind === 'check') {
    const { data: waits } = await db.from('note_orders').select('kind,label,query,created_at')
      .eq('user_id', user.id).in('status', ['missing', 'resolved']).order('created_at', { ascending: true }).limit(30);
    const seen = new Set<string>(), ready: unknown[] = [];
    const today = await todayCounts(db, user.id);
    const { data: cfg } = await db.from('private_config').select('k,v').eq('k', 'notes_root').maybeSingle();
    if (!cfg?.v || !waits?.length) return reply(req, 200, { ready, today, limit: LIMIT });
    const all = await listTree(cfg.v, db);
    for (const w of waits) {
      if (seen.has(w.label)) continue; seen.add(w.label);
      const spec = makeSpec({ kind: w.kind, ...(w.query || {}) });
      if (!('error' in spec) && findFiles(all, spec).length) ready.push({ kind: w.kind, label: w.label, query: w.query });
    }
    return reply(req, 200, { ready, today, limit: LIMIT });
  }

  const n = Number(b.n);
  if (!(n >= (b.kind === 'book' ? 0 : 1) && n <= 60)) return reply(req, 400, { error: '문항 번호를 확인해 주세요.' });
  const spec = makeSpec(b);
  if ('error' in spec) return reply(req, 400, { error: spec.error });
  const { label, query } = spec;

  // 하루 개수 제한 (한국 시간 자정 기준, 실제로 받은 것만 계산) — 모의고사 2개 · 부교재 1개
  const today = await todayCounts(db, user.id);
  if (today[b.kind] >= LIMIT[b.kind]) return reply(req, 429, { error: `${LIMIT_MSG[b.kind]}까지 받을 수 있어요. 내일 다시 요청해 주세요.` });

  // 분석노트 폴더에서 찾기
  const { data: cfg } = await db.from('private_config').select('k,v').eq('k', 'notes_root').maybeSingle();
  if (!cfg?.v) return reply(req, 503, { error: '자료 연결 준비 중이에요. 잠시 후 다시 시도해 주세요.' });
  const all = await listTree(cfg.v, db);
  const files = findFiles(all, spec);

  if (!files.length) {
    // 같은 자료를 이미 기다리고 있으면 중복으로 쌓지 않음
    const { count: dup } = await db.from('note_orders').select('id', { count: 'exact', head: true })
      .eq('user_id', user.id).eq('label', label).in('status', ['missing', 'resolved']);
    if (!dup) {
      await db.from('note_orders').insert({ user_id: user.id, author_name: name, kind: b.kind, label, query, status: 'missing' });
      // 요청한 페이지 댓글 창에 접수 댓글 + 원장 답글 (이름은 화면에서 김*윤처럼 가려짐)
      const pk = String(b.page_key || 'notes').slice(0, 200), pt = String(b.page_title || '분석노트 요청').slice(0, 200);
      await db.from('comments').insert({
        user_id: user.id, author_name: name, page_key: pk, page_title: pt, approved: true,
        content: `[자료 요청] ${label} 부탁드려요.`,
        reply: `${label} 요청 접수했어요. 원장님이 1~2일 안에 준비할게요. 완성되면 자료실에 로그인해서 받을 수 있어요. (한 번에 여러 개 요청했다면 처음 1개는 카카오톡으로도 보내 드려요)`, replied_at: new Date().toISOString(),
      });
    }
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
  // 기다리던 같은 자료 요청은 '받음' 처리 (준비 알림·관리자 목록에서 빠짐)
  await db.from('note_orders').update({ status: 'done' }).eq('user_id', user.id).eq('label', label).in('status', ['missing', 'resolved']);
  // 접수(진행 중)·준비 완료 댓글이 있으면 답글을 '전송 완료'로 바꿈
  await db.from('comments').update({ reply: `${label} 완성돼서 카카오톡으로 보내 드렸어요. 공부에 도움이 되면 좋겠어요!`, replied_at: new Date().toISOString() })
    .eq('user_id', user.id).eq('content', `[자료 요청] ${label} 부탁드려요.`).not('reply', 'like', '%보내 드렸어요%');
  const left = { moe: LIMIT.moe - today.moe - (b.kind === 'moe' ? 1 : 0), book: LIMIT.book - today.book - (b.kind === 'book' ? 1 : 0) };
  return reply(req, 200, { ok: true, label, link, left, expires_at: expires.toISOString(), kakao, kakao_scope: kakaoError.includes('insufficient') || kakaoError.includes('-402') });
});
