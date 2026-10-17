// 준비된 요청 자료 자동 발송 (pg_cron 이 매일 08~22시 매시 5분에 호출)
// 그때 없던 자료를 기다리는 회원 중, 드라이브에 자료가 올라온 회원에게 가장 먼저 요청한 1개만 카톡으로 보냄
// 하루 1개 규칙: 오늘 이미 받은 회원은 건너뜀. 나머지는 메시지에서 "자료실에서 받아 가세요"로 안내 (재방문 유도)
// 공통 함수(listTree·hasNum·moeKey·makeSpec·findFiles)는 note-request 와 같게 유지
import { createClient } from 'npm:@supabase/supabase-js@2';

const LINK_HOURS = 24;
// 부교재 목록 → 단위(강/회). 이름의 각 단어가 드라이브 폴더 이름에 들어가야 함 (lib.js NOTE_BOOK_CFG 와 같게)
const BOOKS: Record<string, string> = { '수능특강 라이트': '강', '리딩파워 기본': '강', '리딩파워 완성': '강', '올림포스 영어독해 기본1': '강', '하루 6개 1등급 모의고사 고1': '회', '하루 6개 1등급 모의고사 고2': '회', '올림포스 전국연합학력평가 기출문제집 고1': '회', '올림포스 전국연합학력평가 기출문제집 고2': '회' };

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

Deno.serve(async (req) => {
  const db = createClient(Deno.env.get('SUPABASE_URL')!, Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!);
  const { data: keyRow } = await db.from('private_config').select('v').eq('k', 'cron_key').maybeSingle();
  if (!keyRow?.v || req.headers.get('x-cron-key') !== keyRow.v) return new Response('forbidden', { status: 403 });
  const REST = Deno.env.get('KAKAO_REST_KEY') || '', SECRET = Deno.env.get('KAKAO_CLIENT_SECRET') || '';
  if (!REST) return Response.json({ ok: false, reason: 'KAKAO_REST_KEY 미설정' });

  const { data: waits } = await db.from('note_orders').select('user_id,author_name,kind,label,query,created_at')
    .in('status', ['missing', 'resolved']).order('created_at', { ascending: true }).limit(500);
  if (!waits?.length) return Response.json({ ok: true, sent: 0 });

  const kst = new Date(Date.now() + 9 * 3600e3);
  const dayStart = new Date(Date.UTC(kst.getUTCFullYear(), kst.getUTCMonth(), kst.getUTCDate()) - 9 * 3600e3).toISOString();
  const { data: cfg } = await db.from('private_config').select('v').eq('k', 'notes_root').maybeSingle();
  if (!cfg?.v) return Response.json({ ok: false, reason: 'notes_root' });
  const all = await listTree(cfg.v);

  // 회원별로 묶기 (요청 순서 유지, 같은 자료는 하나로)
  const byUser = new Map<string, any[]>();
  for (const w of waits) {
    const l = byUser.get(w.user_id) || [];
    if (!l.some((x) => x.label === w.label)) l.push(w);
    byUser.set(w.user_id, l);
  }

  const log: string[] = [];
  for (const [uid, list] of byUser) {
    // 준비된 자료만
    const ready = list.map((w) => ({ w, spec: makeSpec({ kind: w.kind, ...(w.query || {}) }) }))
      .filter((x) => !('error' in x.spec) && findFiles(all, x.spec as Spec).length);
    if (!ready.length) continue;
    // 오늘 이미 받았으면 건너뜀 (하루 1개)
    const { count } = await db.from('note_orders').select('id', { count: 'exact', head: true })
      .eq('user_id', uid).eq('status', 'sent').gte('created_at', dayStart);
    if ((count || 0) >= 1) continue;
    // 카카오 토큰 (없으면 자료실 로그인 시 '준비됐어요' 알림으로 받음)
    const { data: tk } = await db.from('kakao_tokens').select('*').eq('user_id', uid).maybeSingle();
    if (!tk) { log.push(`${uid}: no token`); continue; }
    let access = tk.access_token as string | null;
    if (!access || !tk.access_expires || new Date(tk.access_expires).getTime() < Date.now() + 10 * 60e3) {
      const p = new URLSearchParams({ grant_type: 'refresh_token', client_id: REST, refresh_token: tk.refresh_token });
      if (SECRET) p.set('client_secret', SECRET);
      const r = await fetch('https://kauth.kakao.com/oauth/token', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8' }, body: p });
      const j = await r.json().catch(() => ({}));
      if (!r.ok || !j.access_token) { log.push(`${uid}: refresh fail ${r.status}`); continue; }
      access = j.access_token;
      await db.from('kakao_tokens').update({
        access_token: access, access_expires: new Date(Date.now() + (j.expires_in || 3600) * 1000).toISOString(),
        ...(j.refresh_token ? { refresh_token: j.refresh_token } : {}), updated_at: new Date().toISOString(),
      }).eq('user_id', uid);
    }

    const { w, spec } = ready[0] as { w: any; spec: Spec };
    const f = findFiles(all, spec)[0];
    const token = Array.from(crypto.getRandomValues(new Uint8Array(16))).map((x) => x.toString(16).padStart(2, '0')).join('');
    const expires = new Date(Date.now() + LINK_HOURS * 3600e3);
    const link = `https://data.likasuni.com/get/?t=${token}`;
    const until = new Date(expires.getTime() + 9 * 3600e3).toISOString().slice(5, 16).replace('-', '/').replace('T', ' ');
    const rest = ready.length - 1;
    const text = `[리카수니 자료실]\n요청하신 ${w.label}가 준비돼서 보내드려요 📘\n\n링크는 ${until}까지(24시간) 열 수 있어요.` +
      (rest > 0 ? `\n\n요청하신 자료 ${rest}개가 더 준비돼 있어요. 자료실(data.likasuni.com)에 로그인하면 하루 1개씩 받을 수 있어요.` : '');
    const k = await fetch('https://kapi.kakao.com/v2/api/talk/memo/default/send', {
      method: 'POST',
      headers: { Authorization: `Bearer ${access}`, 'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8' },
      body: new URLSearchParams({ template_object: JSON.stringify({ object_type: 'text', text, link: { web_url: link, mobile_web_url: link }, button_title: '분석노트 받기' }) }),
    });
    if (!k.ok) { log.push(`${uid}: send fail ${k.status} ${await k.text()}`); continue; }
    await db.from('note_orders').insert({
      user_id: uid, author_name: w.author_name, kind: w.kind, label: w.label, query: w.query, status: 'sent',
      drive_id: f.id, file_name: [...f.path, f.name].join('/'), link_token: token, expires_at: expires.toISOString(), kakao_sent: true,
    });
    await db.from('note_orders').update({ status: 'done' }).eq('user_id', uid).eq('label', w.label).in('status', ['missing', 'resolved']);
    log.push(`${uid}: sent ${w.label}`);
  }
  console.log(log.join(' | '));
  return Response.json({ ok: true, log });
});
