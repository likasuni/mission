/**
 * 리카수니 자료실 ↔ 구글드라이브 분석노트 연결 (원장님 계정으로 실행)
 *
 * 하는 일
 *  1) 분석노트 폴더 2개(모의고사·부교재)를 '제한됨'(비공개)으로 바꾸고,
 *     바로 보기 자료(모의고사 18~29번, 41~45번)만 파일별로 '링크가 있는 모든 사용자' 공개로 둡니다.
 *     30~40번과 부교재 분석노트는 비공개 → 카톡 요청으로만 받을 수 있어요.
 *  2) 자료실 서버(Supabase)가 비밀키로 요청하면 파일 목록과 파일 내용을 전달합니다.
 *  3) 자료실 목록 만들기(깃허브)에는 공개 파일 목록만 알려 줍니다 (비공개 파일 주소는 절대 안 내보냄).
 *  4) 매시간 자동으로 새로 올린 파일의 공개/비공개를 맞춥니다.
 *  5) '기타자료' 폴더(기타 자료 요청)도 비공개로 두고, 원장님이 고른 파일 하나만 학생에게 열기 링크로 보냅니다 (2026-10-31).
 *
 * 처음 한 번: 위쪽 함수 선택에서 setup → 실행 → 권한 허용
 */
const KEY = '여기에_비밀키';
const ROOTS = { '모의고사 분석노트': '1jSEPdOdM4RD7GplBWwF3jiRKFWToBOBq', '부교재 분석노트': '1vg17CVTqjIRk-hdoA3PhrJ1RTUn84lSO', '기타자료': '1FryHlXrnXc7gzP8e3xQrM-TBR6L-KkXY' };
const ETC = '기타자료'; // 기타 자료 요청 폴더 — 모두 비공개, 분석노트 목록(list)에는 안 섞음
const KEEP_PUBLIC = ['105f20gSuhZvR44gCK6oW5mxn2-ZFG12J']; // 부교재 샘플(수능특강 라이트) — 공개 유지
const PRIVATE_FROM = 30, PRIVATE_TO = 40; // 모의고사 30~40번은 비공개

/* ---------- 공개/비공개 규칙 ---------- */
function nums(name) {
  name = String(name).normalize('NFC'); // 맥에서 올린 이름(NFD) 보정
  const out = [];
  let m, re = /(\d{1,2})\s*(?:[-~]\s*(\d{1,2}))?\s*번/g;
  while ((m = re.exec(name))) out.push([+m[1], m[2] ? +m[2] : +m[1]]);
  m = name.match(/^(\d{1,2})(?:\s*[-~]\s*(\d{1,2}))?\s*\.pdf$/i);
  if (m) out.push([+m[1], m[2] ? +m[2] : +m[1]]);
  return out;
}
function isPublic(f) {
  if (KEEP_PUBLIC.indexOf(f.id) > -1) return true;
  if (String(f.path[0]).normalize('NFC') === '부교재 분석노트') return false;            // 부교재 분석노트는 모두 비공개
  if (String(f.path[0]).normalize('NFC') === ETC) return false;                         // 기타자료도 모두 비공개
  if (/문제|정답|해설|듣기/.test(String(f.name).normalize('NFC'))) return true;          // 같은 폴더의 시험지 원본은 공개 그대로
  const ns = nums(f.name);
  if (!ns.length) return false;                                   // 번호를 모르면 안전하게 비공개
  return ns.every(function (r) { return r[1] < PRIVATE_FROM || r[0] > PRIVATE_TO; });
}

/* ---------- 폴더 훑기 ---------- */
function walk(withFolders) {
  const files = [], folders = [];
  Object.keys(ROOTS).forEach(function (name) {
    const stack = [{ f: DriveApp.getFolderById(ROOTS[name]), path: [name] }];
    while (stack.length) {
      const cur = stack.pop();
      folders.push(cur.f);
      const fs = cur.f.getFiles();
      while (fs.hasNext()) {
        const x = fs.next(), nm = x.getName().trim(); // 이름 앞뒤 빈칸 제거 (' 18.pdf' 같은 이름)
        if (/\.pdf$/i.test(nm) && !x.isTrashed()) files.push({ id: x.getId(), name: nm, path: cur.path, file: withFolders ? x : null });
      }
      const ds = cur.f.getFolders();
      while (ds.hasNext()) { const d = ds.next(); stack.push({ f: d, path: cur.path.concat([d.getName()]) }); }
    }
  });
  return withFolders ? { files: files, folders: folders } : files;
}

// 목록 캐시 (CacheService 는 한 칸 100KB 라 나눠 저장)
function cachedList(minutes) {
  const c = CacheService.getScriptCache();
  const n = Number(c.get('l2_n') || 0);
  if (n) {
    const parts = c.getAll(Array.apply(null, Array(n)).map(function (_, i) { return 'l2_' + i; }));
    let s = '';
    for (let i = 0; i < n; i++) { if (!parts['l2_' + i]) { s = ''; break; } s += parts['l2_' + i]; }
    if (s) return JSON.parse(s);
  }
  const list = walk(false).map(function (f) {
    const nfc = function (x) { return String(x).normalize('NFC'); }; // 맥에서 올린 이름(NFD) 보정
    return { id: f.id, name: nfc(f.name), path: f.path.map(nfc), pub: isPublic(f) };
  });
  const s = JSON.stringify(list), size = 90000, put = {};
  const cnt = Math.ceil(s.length / size);
  for (let i = 0; i < cnt; i++) put['l2_' + i] = s.slice(i * size, (i + 1) * size);
  put.l2_n = String(cnt);
  c.putAll(put, (minutes || 5) * 60);
  return list;
}

/* ---------- 웹 요청 ---------- */
function doGet(e) {
  const p = (e && e.parameter) || {};
  // 공개 목록 (자료실 페이지 만들 때 사용) — 비밀키 없이, 공개 파일만
  if (p.action === 'catalog') {
    return out({ files: cachedList(60).filter(function (f) { return f.pub; }).map(function (f) { return { id: f.id, title: f.name, path: f.path }; }) });
  }
  if (p.key !== KEY) return out({ error: 'forbidden' });
  // 전체 목록 (요청 처리용). scope=etc 이면 기타자료 폴더만, 아니면 분석노트 폴더만
  if (p.action === 'list') {
    if (p.scope === 'etc') return out({ files: listEtc() });
    return out({ files: cachedList(5).filter(function (f) { return f.path[0] !== ETC; })
      .map(function (f) { return { id: f.id, name: f.name, path: f.path }; }) });
  }
  // 파일 내용 (분석노트 폴더 안 파일만)
  if (p.action === 'get') {
    const has = function (f) { return f.id === p.id; };
    const ok = cachedList(5).some(has) || listEtc().some(has); // 기타자료는 방금 올린 파일도 바로 (캐시 없이)
    if (!ok) return out({ error: 'notfound' });
    const f = DriveApp.getFileById(p.id);
    return out({ name: f.getName(), b64: Utilities.base64Encode(f.getBlob().getBytes()) });
  }
  return out({ error: 'unknown action' });
}
// 기타자료 폴더 파일 목록 (작은 폴더라 캐시 없이 바로 훑음 → 방금 올린 파일도 보임)
function listEtc() {
  const files = [], stack = [{ f: DriveApp.getFolderById(ROOTS[ETC]), path: [ETC] }];
  while (stack.length) {
    const cur = stack.pop(), fs = cur.f.getFiles();
    while (fs.hasNext()) {
      const x = fs.next(), nm = x.getName().trim().normalize('NFC');
      if (/\.pdf$/i.test(nm) && !x.isTrashed()) files.push({ id: x.getId(), name: nm, path: cur.path });
    }
    const ds = cur.f.getFolders();
    while (ds.hasNext()) { const d = ds.next(); stack.push({ f: d, path: cur.path.concat([d.getName().normalize('NFC')]) }); }
  }
  return files;
}
function out(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}

/* ---------- 공개/비공개 맞추기 ---------- */
// 순서: ① 바로 보기 파일에 공개를 직접 걸고 → ② 폴더를 '제한됨'으로 → ③ 남은 파일 중 공개된 것을 비공개로
// (폴더에서 물려받은 공개는 파일에서 직접 못 지워서, 폴더를 먼저 막아야 함)
function applySharing() {
  const t0 = Date.now(), w = walk(true), late = function () { return Date.now() - t0 > 4.5 * 60e3; };
  let toPub = 0, toPriv = 0, folders = 0, fail = [], done = true;
  const first = w.folders.some(function (d) { return d.getSharingAccess() !== DriveApp.Access.PRIVATE; });
  // ① 바로 보기 파일은 공개 (처음 실행 때는 폴더 공개를 물려받았을 수 있어서 모두 직접 걸어 둠)
  for (let i = 0; i < w.files.length; i++) {
    if (late()) { done = false; break; }
    const f = w.files[i];
    if (!isPublic(f)) continue;
    const acc = f.file.getSharingAccess();
    if (first || (acc !== DriveApp.Access.ANYONE_WITH_LINK && acc !== DriveApp.Access.ANYONE)) {
      try { f.file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW); toPub++; } catch (e) { fail.push(f.name + '(공개)'); }
    }
  }
  // ② 폴더를 '제한됨'으로
  if (done) w.folders.forEach(function (d) {
    if (d.getSharingAccess() !== DriveApp.Access.PRIVATE) {
      try { d.setSharing(DriveApp.Access.PRIVATE, DriveApp.Permission.NONE); folders++; } catch (e) { fail.push('폴더 ' + d.getName()); }
    }
  });
  // ③ 비공개여야 하는데 아직 공개인 파일
  if (done) for (let i = 0; i < w.files.length; i++) {
    if (late()) { done = false; break; }
    const f = w.files[i];
    if (isPublic(f) || f.file.getSharingAccess() === DriveApp.Access.PRIVATE) continue;
    try { f.file.setSharing(DriveApp.Access.PRIVATE, DriveApp.Permission.NONE); toPriv++; } catch (e) { fail.push(f.path.slice(1).join('/') + '/' + f.name); }
  }
  CacheService.getScriptCache().remove('l2_n');
  const msg = '파일 ' + w.files.length + '개 확인 · 공개로 ' + toPub + ' · 폴더 제한 ' + folders + ' · 비공개로 ' + toPriv +
    (done ? ' · 완료' : ' · 아직 남았어요 (setup 을 한 번 더 실행하세요)') +
    (fail.length ? '\n바꾸지 못한 것 ' + fail.length + '개: ' + fail.slice(0, 20).join(', ') : '');
  Logger.log(msg);
  return msg;
}

// 처음 한 번 실행: 공개/비공개 맞추기 + 매시간 자동 실행 등록
function setup() {
  const has = ScriptApp.getProjectTriggers().some(function (t) { return t.getHandlerFunction() === 'applySharing'; });
  if (!has) ScriptApp.newTrigger('applySharing').timeBased().everyHours(1).create();
  applySharing();
}
