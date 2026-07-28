#!/usr/bin/env python3
"""merged.json から自己完結の report.html を生成する。"""
import base64
import binascii
import copy
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote


LINE_SPEC = re.compile(r"^~?(?P<start>[1-9][0-9]*)(?:-(?P<end>[1-9][0-9]*))?$")


HTML_TEMPLATE = r"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Review Report</title>
<style>
:root{--bg:#f6f8fa;--card:#fff;--border:#d1d9e0;--text:#1f2328;--muted:#59636e;--link:#0969da;
--high:#d1242f;--medium:#bf8700;--low:#1a7f37;--claude:#d97757;--gemini:#4285f4;--codex:#10a37f;}
:root[data-theme="dark"]{--bg:#0d1117;--card:#151b23;--border:#3d444d;--text:#f0f6fc;--muted:#9198a1;--link:#58a6ff;}
@media(prefers-color-scheme:dark){:root:not([data-theme]){--bg:#0d1117;--card:#151b23;--border:#3d444d;--text:#f0f6fc;--muted:#9198a1;--link:#58a6ff;}}
*{box-sizing:border-box} body{margin:0;padding:16px 16px 90px;background:var(--bg);color:var(--text);font-family:-apple-system,"Hiragino Sans",sans-serif;font-size:14px;line-height:1.6}
a{color:var(--link)} button{cursor:pointer;border:1px solid var(--border);background:var(--card);color:var(--text);border-radius:6px;padding:5px 10px;font-size:13px}button:disabled{cursor:not-allowed;opacity:.55}
button[aria-pressed="true"],button.primary{background:var(--link);border-color:var(--link);color:#fff}.report-header{margin-bottom:14px}.breadcrumbs,.meta,.save-help{color:var(--muted);font-size:13px}.breadcrumbs{display:flex;gap:7px;flex-wrap:wrap;align-items:center}.report-header h1{font-size:20px;margin:3px 0}.author{margin:0}.toolbar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:16px}.theme-picker{display:flex;gap:0}.theme-picker button{border-radius:0}.theme-picker button:first-child{border-radius:6px 0 0 6px}.theme-picker button:last-child{border-radius:0 6px 6px 0}.prio-title{margin:20px 0 8px;font-size:15px}
.priority-group{margin-top:20px}.prio-title{margin:0 0 8px}.card{background:var(--card);border:1px solid var(--border);border-radius:8px;margin-bottom:8px}.card.completed{opacity:.62;border-left:4px solid var(--muted)}.card.completed.adopted{border-left-color:var(--low)}.hide-completed .card.completed{display:none}.hide-completed .priority-group.all-completed{display:none}.card-header{display:flex;align-items:center;gap:8px;padding:8px 12px;flex-wrap:wrap}.card-toggle{display:flex;align-items:center;gap:7px;border:0;padding:0;background:transparent;color:var(--text);text-align:left;flex:1;min-width:220px}.card-toggle:hover{text-decoration:underline}.summary{font-weight:600}.disclosure{width:1.2em;text-align:center;font-weight:700}.badge{display:inline-flex;align-items:center;gap:3px;border-radius:10px;padding:1px 8px;font-size:11px;font-weight:700;color:#fff;white-space:nowrap}.badge.high{background:var(--high)}.badge.medium{background:var(--medium)}.badge.low{background:var(--low)}.badge.ai-claude{background:var(--claude)}.badge.ai-gemini{background:var(--gemini)}.badge.ai-codex{background:var(--codex)}.badge.ai-unknown{background:var(--muted)}.badge.carry{background:#8250df}.badge.done{background:var(--muted)}.badge.adopted{background:var(--low)}.ai-icon{width:12px;height:12px;fill:currentColor;stroke:currentColor;stroke-width:1.6}.confidence{color:var(--muted);font-size:12px;white-space:nowrap}.file-links{display:flex;gap:6px;font-family:ui-monospace,monospace;font-size:12px;flex-wrap:wrap}.controls{display:flex;gap:8px;padding:0 12px 8px}.decision{border:0;margin:0;padding:0;display:flex;gap:8px;flex-wrap:wrap}.decision label{cursor:pointer;border:1px solid var(--border);border-radius:6px;padding:3px 8px}.decision input{accent-color:var(--link)}.decision label:has(input:checked){border-color:var(--link);background:color-mix(in srgb,var(--link) 15%,transparent)}.card-body{display:none;border-top:1px solid var(--border);padding:8px 12px}.card.open .card-body{display:block}.source,.code-context{margin:8px 0;padding:8px;border:1px solid var(--border);border-radius:6px}.src-head,.context-head{font-size:12px;color:var(--muted);margin-bottom:4px}.markdown-line{min-height:1.4em}.markdown-code{background:color-mix(in srgb,var(--border) 45%,transparent);border-radius:3px;padding:1px 4px;font-family:ui-monospace,monospace}.markdown-block{overflow:auto;margin:6px 0;padding:8px;background:color-mix(in srgb,var(--border) 30%,transparent);border-radius:4px}.code-lines{margin:0;overflow:auto;font-family:ui-monospace,monospace;font-size:12px;line-height:1.5}.code-line{display:flex;min-width:max-content}.code-line.target{background:color-mix(in srgb,var(--medium) 25%,transparent)}.line-no{width:4em;flex:none;padding-right:8px;text-align:right;color:var(--muted);user-select:none}.code-text{white-space:pre}.unavailable{color:var(--muted);font-size:13px}footer{position:fixed;left:0;right:0;bottom:0;background:var(--card);border-top:1px solid var(--border);padding:10px 16px;display:flex;gap:16px;align-items:center;flex-wrap:wrap;font-size:13px}#params{font-family:ui-monospace,monospace}#save-status{color:var(--muted)}
</style>
<style>
#expand-all{background:#0969da;border-color:#0969da;color:#fff}#collapse-all{background:#8250df;border-color:#8250df;color:#fff}#toggle-completed{background:#9a6700;border-color:#9a6700;color:#fff}#save-state{background:var(--low);border-color:var(--low);color:#fff}.theme-picker button[data-theme="auto"]{background:#0969da;border-color:#0969da;color:#fff}.theme-picker button[data-theme="light"]{background:#9a6700;border-color:#9a6700;color:#fff}.theme-picker button[data-theme="dark"]{background:#8250df;border-color:#8250df;color:#fff}.theme-picker button[aria-pressed="true"]{outline:2px solid var(--text);outline-offset:2px}.priority-group[data-priority="high"]{border-left:4px solid var(--high);padding-left:10px}.priority-group[data-priority="medium"]{border-left:4px solid var(--medium);padding-left:10px}.priority-group[data-priority="low"]{border-left:4px solid var(--low);padding-left:10px}.priority-group[data-priority="high"] .prio-title{color:var(--high)}.priority-group[data-priority="medium"] .prio-title{color:var(--medium)}.priority-group[data-priority="low"] .prio-title{color:var(--low)}.card.completed.skipped{border-left-color:var(--muted)}.badge.skipped{background:var(--muted)}.decision .decision-adopt{border-color:var(--low);background:color-mix(in srgb,var(--low) 12%,transparent)}.decision .decision-skip{border-color:var(--muted);background:color-mix(in srgb,var(--muted) 12%,transparent)}.decision .decision-adopt input{accent-color:var(--low)}.decision .decision-skip input{accent-color:var(--muted)}.decision .decision-adopt:has(input:checked){border-color:var(--low);background:var(--low);color:#fff}.decision .decision-skip:has(input:checked){border-color:var(--muted);background:var(--muted);color:#fff}
</style>
<style>.card-toggle{color:var(--link)}.card-toggle:hover{color:var(--claude)}</style>
</head>
<body>
<header class="report-header" id="report-header"></header>
<div class="toolbar">
<button id="expand-all">すべて展開</button><button id="collapse-all">すべて折りたたむ</button>
<div class="theme-picker" role="group" aria-label="テーマ"><button data-theme="auto">自動</button><button data-theme="light">ライト</button><button data-theme="dark">ダーク</button></div>
</div>
<div id="report" class="hide-completed"></div>
<footer><span id="progress"></span><button id="toggle-completed">処理済みを表示</button><span id="params"></span><button id="save-state" disabled>状態ファイルを保存…</button><span id="save-status">未保存</span></footer>
<script>
const DATA = __REVIEW_DATA__;
const state = {schema_version: 1, items: {}};
let fileHandle = null, saveTimer = null, showCompleted = false;
const CAN_SAVE_STATE = typeof window.showSaveFilePicker === "function";
const PRIO = [["high","🔴 High Priority"],["medium","🟡 Medium Priority"],["low","🟢 Low Priority"]];
const CARRY = {skipped_before:"前回スキップ",should_be_fixed:"前回対応済のはず"};
const AI = {claude:{name:"Claude",shape:"claude"},codex:{name:"Codex",shape:"codex"},gemini:{name:"Gemini",shape:"gemini"}};
const THEME_KEY = "ai-review-report-theme";

function el(tag, cls, text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;}
function externalLink(text, href, cls){const a=el("a",cls,text);try{const url=new URL(href);if(url.protocol==="https:"||url.protocol==="http:"){a.href=url.href;a.target="_blank";a.rel="noopener noreferrer";return a;}}catch(e){}return el("span",cls,text);}
function itemState(id){const key=String(id);if(!state.items[key])state.items[key]={reviewed:false,adopt:false};return state.items[key];}
function allItemsCompleted(){return DATA.items.every(item=>{const s=itemState(item.id);return s.reviewed||s.adopt;});}
function aiIcon(kind){const svg=document.createElementNS("http://www.w3.org/2000/svg","svg");svg.setAttribute("viewBox","0 0 16 16");svg.setAttribute("aria-hidden","true");svg.classList.add("ai-icon");const path=document.createElementNS(svg.namespaceURI,"path");const paths={claude:"M3 4h10v3H3zM3 9h10v3H3z",codex:"M8 1l2 3 3.5.5-2.5 2.5.6 3.5L8 9l-3.1 1.5.6-3.5L3 4.5 6.5 4z",gemini:"M8 1.2l1.4 5.4 5.4 1.4-5.4 1.4L8 14.8 6.6 9.4 1.2 8l5.4-1.4z"};path.setAttribute("d",paths[kind]||paths.codex);svg.appendChild(path);return svg;}
function aiBadge(ai){const info=AI[ai]||{name:ai||"AI",shape:"unknown"};const b=el("span","badge ai-"+(AI[ai]?ai:"unknown"));b.appendChild(aiIcon(info.shape));b.appendChild(document.createTextNode(info.name));return b;}
function maxConfidence(item){const values=item.sources.map(s=>Number(s.confidence)||0);return values.length?Math.max(...values):0;}
function appendInline(parent,text){const re=/(\*\*[^*\n]+\*\*|`[^`\n]+`)/g;let pos=0;for(const match of text.matchAll(re)){parent.appendChild(document.createTextNode(text.slice(pos,match.index)));const token=match[0];if(token.startsWith("**")){const strong=el("strong","",token.slice(2,-2));parent.appendChild(strong);}else{parent.appendChild(el("code","markdown-code",token.slice(1,-1)));}pos=match.index+token.length;}parent.appendChild(document.createTextNode(text.slice(pos)));}
function markdown(parent,text){let inCode=false,code=[];for(const line of String(text||"").split("\n")){if(line.startsWith("```")){if(inCode){parent.appendChild(el("pre","markdown-block",code.join("\n")));code=[];}inCode=!inCode;continue;}if(inCode){code.push(line);continue;}const p=el("div","markdown-line");appendInline(p,line);parent.appendChild(p);}if(inCode)parent.appendChild(el("pre","markdown-block",code.join("\n")));}
function buildHeader(){const h=document.getElementById("report-header"),repo=DATA.repository||{};const crumbs=el("div","breadcrumbs");if(repo.url)crumbs.appendChild(externalLink(repo.name||"リポジトリ",repo.url));else crumbs.appendChild(el("span","",repo.name||"リポジトリ情報なし"));if(DATA.head_ref_name)crumbs.appendChild(el("span","","/ "+DATA.head_ref_name));if(DATA.pr_url)crumbs.appendChild(externalLink("PR #"+DATA.pr_number,DATA.pr_url));else crumbs.appendChild(el("span","","PR #"+DATA.pr_number));h.appendChild(crumbs);const title=DATA.pr_title||"AI Review Report";h.appendChild(el("h1","",title));if(DATA.pr_author)h.appendChild(el("p","author","作成者: "+DATA.pr_author));document.title=title+" · AI Review Report";}
function build(){buildHeader();const root=document.getElementById("report");root.textContent="";for(const [prio,title] of PRIO){const items=DATA.items.filter(i=>i.priority===prio);if(!items.length)continue;const group=el("section","priority-group");group.dataset.priority=prio;group.appendChild(el("h2","prio-title",title));for(const item of items)group.appendChild(card(item));root.appendChild(group);}if(!DATA.items.length)root.appendChild(el("p","","対応が必要な指摘はありません。"));refresh();}
function card(item){const c=el("article","card");c.dataset.id=item.id;const bodyId="item-body-"+item.id;const h=el("div","card-header");const toggle=el("button","card-toggle");toggle.type="button";toggle.setAttribute("aria-expanded","false");toggle.setAttribute("aria-controls",bodyId);toggle.appendChild(el("span","disclosure","▸"));toggle.appendChild(el("span","",item.id+"."));toggle.appendChild(el("span","badge "+item.priority,item.priority.toUpperCase()));for(const s of item.sources)toggle.appendChild(aiBadge(s.ai));if(item.carryover)toggle.appendChild(el("span","badge carry",CARRY[item.carryover]||item.carryover));toggle.appendChild(el("span","summary",item.area+": "+item.summary));toggle.addEventListener("click",()=>setOpen(c,!c.classList.contains("open")));h.appendChild(toggle);h.appendChild(el("span","decision-status"));h.appendChild(el("span","confidence","最大信頼度 "+maxConfidence(item)+"%"));const links=el("span","file-links");if(item.links&&item.links.pr_diff)links.appendChild(externalLink("PR差分",item.links.pr_diff));if(item.links&&item.links.snapshot)links.appendChild(externalLink(item.file+":"+item.line_spec,item.links.snapshot));else links.appendChild(el("span","",item.file+":"+item.line_spec));h.appendChild(links);c.appendChild(h);const ctl=el("div","controls");ctl.appendChild(decision(item.id));c.appendChild(ctl);const body=el("div","card-body");body.id=bodyId;for(const s of item.sources){const box=el("section","source");box.appendChild(el("div","src-head",(AI[s.ai]?.name||s.ai)+" #"+s.original_number+" (影響度: "+s.impact+" / 信頼度: "+s.confidence+")"));const content=el("div","text");markdown(content,s.text);box.appendChild(content);body.appendChild(box);}appendContext(body,item.code_context);c.appendChild(body);return c;}
function setOpen(card,open){card.classList.toggle("open",open);const button=card.querySelector(".card-toggle");button.setAttribute("aria-expanded",String(open));button.querySelector(".disclosure").textContent=open?"▾":"▸";}
function decision(id){const group=el("fieldset","decision");group.setAttribute("aria-label","指摘の対応方針");for(const [value,style,label] of [["adopt","adopt","🔧 対応する"],["reviewed","skip","🚫 対応しない"]]){const labelEl=el("label","decision-"+style,label);const input=document.createElement("input");input.type="checkbox";input.value=value;input.addEventListener("change",()=>{const s=itemState(id);s.reviewed=input.checked&&value==="reviewed";s.adopt=input.checked&&value==="adopt";setOpen(input.closest(".card"),false);refresh();scheduleSave();});labelEl.prepend(input);group.appendChild(labelEl);}return group;}
function appendContext(parent,context){if(!context)return;const box=el("section","code-context");box.appendChild(el("div","context-head","対象コード（前後3行）"));if(context.error){box.appendChild(el("div","unavailable",context.error));parent.appendChild(box);return;}const pre=el("pre","code-lines");for(const line of context.lines){const row=el("span","code-line"+(line.target?" target":""));row.appendChild(el("span","line-no",String(line.number)));row.appendChild(el("span","code-text",line.text));pre.appendChild(row);}box.appendChild(pre);parent.appendChild(box);}
function refresh(){let reviewed=0;const adopted=[];for(const item of DATA.items){const s=itemState(item.id);if(s.reviewed)reviewed++;if(s.adopt)adopted.push(item.id);const c=document.querySelector(`.card[data-id="${item.id}"]`);if(c){const completed=s.reviewed||s.adopt;c.classList.toggle("completed",completed);c.classList.toggle("adopted",s.adopt);c.classList.toggle("skipped",s.reviewed);const status=c.querySelector(".decision-status");status.textContent=s.adopt?"🔧 対応する":s.reviewed?"🚫 対応しない":"";status.className="decision-status"+(s.adopt?" badge adopted":s.reviewed?" badge skipped":"");for(const input of c.querySelectorAll(".decision input"))input.checked=input.value==="adopt"?s.adopt:s.reviewed;}}for(const group of document.querySelectorAll(".priority-group")){const cards=group.querySelectorAll(".card");group.classList.toggle("all-completed",cards.length>0&&[...cards].every(c=>c.classList.contains("completed")));}const done=reviewed+adopted.length;const root=document.getElementById("report");root.classList.toggle("hide-completed",!showCompleted);document.getElementById("progress").textContent=`未処理 ${DATA.items.length-done}/${DATA.items.length}（対応しない ${reviewed} / 対応する ${adopted.length}）`;document.getElementById("toggle-completed").textContent=showCompleted?`処理済みを隠す (${done})`:`処理済みを表示 (${done})`;document.getElementById("params").textContent=adopted.length?`対応する: ${adopted.join(",")}`:"対応する: (未選択)";document.getElementById("save-state").disabled=!CAN_SAVE_STATE||done!==DATA.items.length;}
async function saveState(){if(!CAN_SAVE_STATE||!allItemsCompleted())return;try{fileHandle=await window.showSaveFilePicker({suggestedName:"state.json",types:[{description:"JSON",accept:{"application/json":[".json"]}}]});}catch(e){return;}await save();}
function scheduleSave(){if(!fileHandle||!allItemsCompleted())return;clearTimeout(saveTimer);saveTimer=setTimeout(save,300);}async function save(){if(!fileHandle||!allItemsCompleted())return;const w=await fileHandle.createWritable();await w.write(JSON.stringify(state,null,1));await w.close();document.getElementById("save-status").textContent="保存済み "+new Date().toLocaleTimeString();}
function setTheme(theme){if(theme==="auto")delete document.documentElement.dataset.theme;else document.documentElement.dataset.theme=theme;for(const b of document.querySelectorAll("[data-theme]")){b.setAttribute("aria-pressed",String(b.dataset.theme===theme));}try{localStorage.setItem(THEME_KEY,theme);}catch(e){}}
document.getElementById("expand-all").addEventListener("click",()=>document.querySelectorAll(".card").forEach(c=>setOpen(c,true)));document.getElementById("collapse-all").addEventListener("click",()=>document.querySelectorAll(".card").forEach(c=>setOpen(c,false)));document.getElementById("save-state").addEventListener("click",saveState);document.getElementById("toggle-completed").addEventListener("click",()=>{showCompleted=!showCompleted;refresh();});document.querySelectorAll(".theme-picker button").forEach(b=>b.addEventListener("click",()=>setTheme(b.dataset.theme)));let savedTheme="auto";try{savedTheme=localStorage.getItem(THEME_KEY)||"auto";}catch(e){}setTheme(savedTheme);if(!CAN_SAVE_STATE)document.getElementById("save-status").textContent="このブラウザは進捗保存に非対応(Chrome系で開いてください)";build();
</script>
</body>
</html>
"""


def parse_line_spec(line_spec):
    match = LINE_SPEC.fullmatch(str(line_spec))
    if not match:
        return None
    start = int(match.group("start"))
    end = int(match.group("end") or start)
    return start, max(start, end)


def extract_context(content, line_spec, padding=3):
    parsed = parse_line_spec(line_spec)
    if not parsed:
        return {"error": "対象行を解決できないため、コード抜粋は表示できません。"}
    start, end = parsed
    lines = content.splitlines()
    if start > len(lines):
        return {"error": "対象行がPR先頭コミットに存在しないため、コード抜粋は表示できません。"}
    first = max(1, start - padding)
    last = min(len(lines), end + padding)
    return {"lines": [
        {"number": number, "text": lines[number - 1], "target": start <= number <= end}
        for number in range(first, last + 1)
    ]}


def read_git_file(repository_dir, head_ref_oid, path):
    if not head_ref_oid:
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(repository_dir), "show", f"{head_ref_oid}:{path}"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False,
        )
    except OSError:
        return None
    return result.stdout if result.returncode == 0 else None


def read_github_file(repository, head_ref_oid, path):
    if not repository or not head_ref_oid:
        return None
    endpoint = "repos/{}/contents/{}?ref={}".format(
        quote(repository, safe="/"), quote(path, safe="/"), quote(head_ref_oid, safe=""))
    try:
        result = subprocess.run(
            ["gh", "api", endpoint], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            check=False, text=True,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    try:
        return base64.b64decode(json.loads(result.stdout)["content"])
    except (KeyError, TypeError, ValueError, binascii.Error):
        return None


def item_links(merged, item):
    parsed = parse_line_spec(item.get("line_spec", ""))
    line = parsed[0] if parsed else None
    path = item.get("file", "")
    pr_url = merged.get("pr_url", "").rstrip("/")
    repository = merged.get("repository") or {}
    repository_url = repository.get("url", "").rstrip("/")
    head_ref_oid = merged.get("head_ref_oid", "")
    links = {}
    if pr_url and path:
        anchor = hashlib.sha256(path.encode()).hexdigest()
        links["pr_diff"] = f"{pr_url}/files#diff-{anchor}" + (f"R{line}" if line else "")
    if repository_url and head_ref_oid and path:
        fragment = f"#L{line}" if line else ""
        if parsed and parsed[1] != line:
            fragment += f"-L{parsed[1]}"
        links["snapshot"] = "{}/blob/{}/{}{}".format(
            repository_url, quote(head_ref_oid, safe=""), quote(path, safe="/"), fragment)
    return links


def prepare_report_data(merged, repository_dir):
    report = copy.deepcopy(merged)
    repository = report.get("repository") or {}
    repository_name = repository.get("name", "")
    cache = {}
    for item in report.get("items", []):
        item["links"] = item_links(report, item)
        path = item.get("file", "")
        if path not in cache:
            raw = read_git_file(repository_dir, report.get("head_ref_oid", ""), path)
            if raw is None:
                raw = read_github_file(repository_name, report.get("head_ref_oid", ""), path)
            if raw is None:
                cache[path] = {"error": "対象コードを取得できませんでした。"}
            elif b"\0" in raw:
                cache[path] = {"error": "バイナリファイルのため、コード抜粋は表示できません。"}
            else:
                try:
                    cache[path] = raw.decode("utf-8")
                except UnicodeDecodeError:
                    cache[path] = {"error": "UTF-8として読めないため、コード抜粋は表示できません。"}
        cached = cache[path]
        item["code_context"] = cached if isinstance(cached, dict) else extract_context(cached, item.get("line_spec", ""))
    return report


def render(merged):
    data = json.dumps(merged, ensure_ascii=False).replace("</", "<\\/")
    return HTML_TEMPLATE.replace("__REVIEW_DATA__", data)


def main(argv):
    if len(argv) != 3:
        print("Usage: generate_review_report.py <merged.json> <output.html>", file=sys.stderr)
        return 1
    with open(argv[1], encoding="utf-8") as f:
        merged = json.load(f)
    report = prepare_report_data(merged, Path.cwd())
    with open(argv[2], "w", encoding="utf-8") as f:
        f.write(render(report))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
