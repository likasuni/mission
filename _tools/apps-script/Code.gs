/**
 * 리카수니 자료실 ↔ 구글드라이브 연결 (원장님 계정으로 실행)
 * - 파일 이름에 '분석노트'가 들어간 PDF만 찾고 전달합니다.
 * - 드라이브 파일은 공유 설정을 바꿀 필요 없이 비공개 그대로 둡니다.
 * 파일 이름 규칙
 *   모의고사: 2026-09_고1_30번_분석노트.pdf  (41-42번처럼 묶음도 가능)
 *   부교재:   2026 수능특강 라이트 20강 1번 분석노트.pdf
 */
const KEY = '46855bb9b6fdc0b15ee3573f59efb145b691b3ed2ac8b212';

function doGet(e) {
  const p = e.parameter || {};
  if (p.key !== KEY) return out({ error: 'forbidden' });

  if (p.action === 'find') {
    const n = Number(p.n);
    const must = JSON.parse(p.must || '[]').map(function (s) { return new RegExp(s); });
    const q = "trashed = false and mimeType = 'application/pdf' and title contains '분석노트' and title contains '" +
      String(p.search || '').replace(/'/g, "\\'") + "'";
    const it = DriveApp.searchFiles(q), files = [];
    while (it.hasNext() && files.length < 20) {
      const f = it.next(), name = f.getName();
      if (must.every(function (re) { return re.test(name); }) && hasNum(name, n)) files.push({ id: f.getId(), name: name });
    }
    return out({ files: files });
  }

  if (p.action === 'get') {
    const f = DriveApp.getFileById(p.id);
    if (f.getName().indexOf('분석노트') < 0) return out({ error: 'forbidden' });
    return out({ name: f.getName(), b64: Utilities.base64Encode(f.getBlob().getBytes()) });
  }
  return out({ error: 'unknown action' });
}

// '30번', '41-42번', '41~42번' 안에 번호 n이 있는지
function hasNum(name, n) {
  const re = /(\d+)\s*(?:[-~]\s*(\d+))?\s*번/g;
  let m;
  while ((m = re.exec(name))) {
    const a = Number(m[1]), b = m[2] ? Number(m[2]) : a;
    if (n >= a && n <= b) return true;
  }
  return false;
}

function out(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}

// 처음 한 번 실행해서 드라이브 권한을 허용하세요 (실행 → 권한 검토 → 허용)
function test() {
  const r = doGet({ parameter: { key: KEY, action: 'find', search: '2026-09', must: JSON.stringify(['^2026-09_고1_']), n: '37' } });
  Logger.log(r.getContent());
}
