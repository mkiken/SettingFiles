#!/usr/bin/env python3
"""merged.json から自己完結の report.html を生成する。

使い方: generate_review_report.py <merged.json> <output.html>

- テンプレートは本ファイルに内蔵(単一ファイル配備)。
- データはJSONとしてページに埋め込み、DOM構築はクライアントJSが
  textContent ベースで行う(エスケープ漏れ防止)。
- チェック状態は File System Access API で state.json に保存する
  (Chrome系前提。スキーマ: {"schema_version":1,"items":{"<id>":{"reviewed":bool,"adopt":bool}}})。
"""
import json
import sys

HTML_TEMPLATE = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Review Report</title>
<style>
:root{--bg:#f6f8fa;--card:#fff;--border:#d1d9e0;--text:#1f2328;--muted:#59636e;
--high:#d1242f;--medium:#bf8700;--low:#1a7f37;
--claude:#d97757;--gemini:#4285f4;--codex:#10a37f;}
@media(prefers-color-scheme:dark){:root{--bg:#0d1117;--card:#151b23;
--border:#3d444d;--text:#f0f6fc;--muted:#9198a1;}}
*{box-sizing:border-box}
body{margin:0;padding:16px 16px 90px;background:var(--bg);color:var(--text);
font-family:-apple-system,"Hiragino Sans",sans-serif;font-size:14px;line-height:1.6}
h1{font-size:18px;margin:0 0 4px}
.meta{color:var(--muted);margin-bottom:12px}
.toolbar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:16px}
button{cursor:pointer;border:1px solid var(--border);background:var(--card);
color:var(--text);border-radius:6px;padding:4px 12px;font-size:13px}
.prio-title{margin:20px 0 8px;font-size:15px}
.card{background:var(--card);border:1px solid var(--border);border-radius:8px;margin-bottom:8px}
.card.adopted{border-left:4px solid var(--low)}
.card-header{display:flex;align-items:center;gap:8px;padding:8px 12px;cursor:pointer;flex-wrap:wrap}
.card-header .summary{flex:1;min-width:200px;font-weight:600}
.card.reviewed .summary{opacity:.55}
.badge{display:inline-block;border-radius:10px;padding:0 8px;font-size:11px;
font-weight:700;color:#fff;white-space:nowrap}
.badge.high{background:var(--high)}.badge.medium{background:var(--medium)}
.badge.low{background:var(--low)}
.badge.ai-claude{background:var(--claude)}.badge.ai-gemini{background:var(--gemini)}
.badge.ai-codex{background:var(--codex)}
.badge.carry{background:#8250df}
.file{font-family:ui-monospace,monospace;font-size:12px;color:var(--muted)}
.controls{display:flex;gap:16px;padding:0 12px 8px;font-size:13px;color:var(--muted)}
.controls label{cursor:pointer;user-select:none}
.card-body{display:none;border-top:1px solid var(--border);padding:8px 12px}
.card.open .card-body{display:block}
.source{margin:8px 0;padding:8px;border:1px solid var(--border);border-radius:6px}
.source .src-head{font-size:12px;color:var(--muted);margin-bottom:4px}
.source .text{white-space:pre-wrap}
footer{position:fixed;left:0;right:0;bottom:0;background:var(--card);
border-top:1px solid var(--border);padding:10px 16px;display:flex;gap:16px;
align-items:center;flex-wrap:wrap;font-size:13px}
#params{font-family:ui-monospace,monospace}
#save-status{color:var(--muted)}
</style>
</head>
<body>
<h1>AI Review Report</h1>
<div class="meta" id="meta"></div>
<div class="toolbar">
<button id="expand-all">すべて展開</button>
<button id="collapse-all">すべて折りたたむ</button>
<button id="connect-state">状態ファイルを接続</button>
<span id="save-status">未接続(チェック状態は保存されません)</span>
</div>
<div id="report"></div>
<footer>
<span id="progress"></span>
<span id="params"></span>
<button id="copy-params">番号をコピー</button>
</footer>
<script>
const DATA = __REVIEW_DATA__;
const state = {schema_version: 1, items: {}};
let fileHandle = null, saveTimer = null;

const PRIO = [["high","🔴 High Priority"],["medium","🟡 Medium Priority"],["low","🟢 Low Priority"]];
const CARRY = {skipped_before: "前回スキップ", should_be_fixed: "前回対応済のはず"};

function el(tag, cls, text){
  const e = document.createElement(tag);
  if(cls) e.className = cls;
  if(text !== undefined) e.textContent = text;
  return e;
}

function itemState(id){
  const key = String(id);
  if(!state.items[key]) state.items[key] = {reviewed: false, adopt: false};
  return state.items[key];
}

function build(){
  document.getElementById("meta").textContent =
    `PR #${DATA.pr_number} / sources: ${DATA.sources.join(", ")} / items: ${DATA.items.length}`;
  const root = document.getElementById("report");
  root.textContent = "";
  for(const [prio, title] of PRIO){
    const items = DATA.items.filter(i => i.priority === prio);
    if(!items.length) continue;
    root.appendChild(el("h2", "prio-title", title));
    for(const item of items) root.appendChild(card(item));
  }
  if(!DATA.items.length) root.appendChild(el("p", "", "対応が必要な指摘はありません。"));
  refresh();
}

function card(item){
  const c = el("div", "card");
  c.dataset.id = item.id;
  const h = el("div", "card-header");
  h.appendChild(el("span", "", `${item.id}.`));
  h.appendChild(el("span", "badge " + item.priority, item.priority.toUpperCase()));
  for(const s of item.sources)
    h.appendChild(el("span", "badge ai-" + s.ai, s.ai[0].toUpperCase()));
  if(item.carryover)
    h.appendChild(el("span", "badge carry", CARRY[item.carryover] || item.carryover));
  h.appendChild(el("span", "summary", `${item.area}: ${item.summary}`));
  h.appendChild(el("span", "file", `${item.file}:${item.line_spec}`));
  h.addEventListener("click", () => c.classList.toggle("open"));
  c.appendChild(h);

  const ctl = el("div", "controls");
  ctl.appendChild(checkbox(item.id, "reviewed", "確認した"));
  ctl.appendChild(checkbox(item.id, "adopt", "対応する"));
  c.appendChild(ctl);

  const body = el("div", "card-body");
  for(const s of item.sources){
    const box = el("div", "source");
    box.appendChild(el("div", "src-head",
      `${s.ai} #${s.original_number} (影響度: ${s.impact} / 信頼度: ${s.confidence})`));
    box.appendChild(el("div", "text", s.text));
    body.appendChild(box);
  }
  c.appendChild(body);
  return c;
}

function checkbox(id, key, labelText){
  const label = el("label");
  const box = document.createElement("input");
  box.type = "checkbox";
  box.checked = itemState(id)[key];
  box.addEventListener("click", ev => ev.stopPropagation());
  box.addEventListener("change", () => {
    itemState(id)[key] = box.checked;
    refresh();
    scheduleSave();
  });
  label.appendChild(box);
  label.appendChild(document.createTextNode(" " + labelText));
  label.addEventListener("click", ev => ev.stopPropagation());
  return label;
}

function refresh(){
  let reviewed = 0;
  const adopted = [];
  for(const item of DATA.items){
    const s = itemState(item.id);
    if(s.reviewed) reviewed++;
    if(s.adopt) adopted.push(item.id);
    const c = document.querySelector(`.card[data-id="${item.id}"]`);
    if(c){
      c.classList.toggle("reviewed", s.reviewed);
      c.classList.toggle("adopted", s.adopt);
      const boxes = c.querySelectorAll(".controls input");
      boxes[0].checked = s.reviewed;
      boxes[1].checked = s.adopt;
    }
  }
  document.getElementById("progress").textContent =
    `確認済み ${reviewed}/${DATA.items.length}`;
  document.getElementById("params").textContent =
    adopted.length ? `対応する: ${adopted.join(",")}` : "対応する: (未選択)";
}

async function connectState(){
  try{
    fileHandle = await window.showSaveFilePicker({
      suggestedName: "state.json",
      types: [{description: "JSON", accept: {"application/json": [".json"]}}],
    });
  }catch(e){ return; } // ピッカーのキャンセル
  // 既存stateを選び直したケースは読み込んで復元する
  try{
    const text = await (await fileHandle.getFile()).text();
    if(text.trim()){
      const loaded = JSON.parse(text);
      if(loaded && loaded.items) Object.assign(state.items, loaded.items);
    }
  }catch(e){ /* 新規ファイルや不正JSONは無視して上書き */ }
  refresh();
  await save();
}

function scheduleSave(){
  if(!fileHandle) return;
  clearTimeout(saveTimer);
  saveTimer = setTimeout(save, 300);
}

async function save(){
  if(!fileHandle) return;
  const w = await fileHandle.createWritable();
  await w.write(JSON.stringify(state, null, 1));
  await w.close();
  document.getElementById("save-status").textContent =
    "保存済み " + new Date().toLocaleTimeString();
}

document.getElementById("expand-all").addEventListener("click",
  () => document.querySelectorAll(".card").forEach(c => c.classList.add("open")));
document.getElementById("collapse-all").addEventListener("click",
  () => document.querySelectorAll(".card").forEach(c => c.classList.remove("open")));
document.getElementById("connect-state").addEventListener("click", connectState);
document.getElementById("copy-params").addEventListener("click", () => {
  const ids = DATA.items.filter(i => itemState(i.id).adopt).map(i => i.id).join(",");
  navigator.clipboard.writeText(ids);
});
if(!window.showSaveFilePicker){
  document.getElementById("connect-state").disabled = true;
  document.getElementById("save-status").textContent =
    "このブラウザは状態保存非対応(Chrome系で開いてください)";
}
build();
</script>
</body>
</html>
"""


def render(merged):
    data = json.dumps(merged, ensure_ascii=False).replace("</", "<\\/")
    return HTML_TEMPLATE.replace("__REVIEW_DATA__", data)


def main(argv):
    if len(argv) != 3:
        print("Usage: generate_review_report.py <merged.json> <output.html>",
              file=sys.stderr)
        return 1
    with open(argv[1], encoding="utf-8") as f:
        merged = json.load(f)
    with open(argv[2], "w", encoding="utf-8") as f:
        f.write(render(merged))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
