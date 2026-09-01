#!/usr/bin/env python3
"""Render one config-audit report from audit.json into a self-contained report.html."""

import json
import os
import sys
from pathlib import Path

CONTEXT_PADDING = 3

HTML_TEMPLATE = r"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>設定監査レポート</title>
<style>
:root{--bg:#f6f8fa;--card:#fff;--border:#d1d9e0;--text:#1f2328;--muted:#59636e;--link:#0969da;
--default:#0969da;--overlap:#bf8700;--patch:#bc4c00;--ambiguity:#59636e;--concise:#1a7f37;--conflict:#d1242f;
--apply:#1a7f37;--dismiss:#59636e;--dep:#8250df;}
:root[data-theme="dark"]{--bg:#0d1117;--card:#151b23;--border:#3d444d;--text:#f0f6fc;--muted:#9198a1;--link:#58a6ff;}
@media(prefers-color-scheme:dark){:root:not([data-theme]){--bg:#0d1117;--card:#151b23;--border:#3d444d;--text:#f0f6fc;--muted:#9198a1;--link:#58a6ff;}}
*{box-sizing:border-box}
body{margin:0;padding:16px 16px 90px;background:var(--bg);color:var(--text);font-family:-apple-system,"Hiragino Sans",sans-serif;font-size:14px;line-height:1.6}
a{color:var(--link)}
button{cursor:pointer;border:1px solid var(--border);background:var(--card);color:var(--text);border-radius:6px;padding:5px 10px;font-size:13px}
button:disabled{cursor:not-allowed;opacity:.55}
button[aria-pressed="true"]{outline:2px solid var(--text);outline-offset:2px}
.report-header{margin-bottom:14px}
.report-header h1{font-size:20px;margin:3px 0}
.meta{color:var(--muted);font-size:13px}
.toolbar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:16px}
.theme-picker{display:flex;gap:0}
.theme-picker button{border-radius:0}
.theme-picker button:first-child{border-radius:6px 0 0 6px}
.theme-picker button:last-child{border-radius:0 6px 6px 0}
#expand-all{background:#0969da;border-color:#0969da;color:#fff}
#collapse-all{background:#8250df;border-color:#8250df;color:#fff}
#save-state{background:var(--apply);border-color:var(--apply);color:#fff}
.theme-picker button[data-theme="auto"]{background:#0969da;border-color:#0969da;color:#fff}
.theme-picker button[data-theme="light"]{background:#9a6700;border-color:#9a6700;color:#fff}
.theme-picker button[data-theme="dark"]{background:#8250df;border-color:#8250df;color:#fff}
.manifest{margin-bottom:16px;border:1px solid var(--border);border-radius:8px;background:var(--card);padding:8px 12px}
.manifest summary{cursor:pointer;font-weight:600}
.manifest table{border-collapse:collapse;margin-top:8px;font-size:13px;width:100%}
.manifest th,.manifest td{border:1px solid var(--border);padding:4px 8px;text-align:left}
.manifest td.excluded{color:var(--muted)}
.cat-group{margin-top:20px;padding-left:10px}
.cat-title{margin:0 0 8px;font-size:15px}
.card{background:var(--card);border:1px solid var(--border);border-radius:8px;margin-bottom:8px}
.card.completed{opacity:.62;border-left:4px solid var(--muted)}
.card.completed.decision-apply{border-left-color:var(--apply)}
.card.completed.decision-dismiss{border-left-color:var(--dismiss)}
.card.flash{outline:2px solid var(--dep);outline-offset:2px}
.card-header{display:flex;align-items:center;gap:8px;padding:8px 12px;flex-wrap:wrap}
.card-toggle{display:flex;align-items:center;gap:7px;border:0;padding:0;background:transparent;color:var(--link);text-align:left;flex:1;min-width:220px}
.card-toggle:hover{text-decoration:underline}
.summary{font-weight:600}
.disclosure{width:1.2em;text-align:center;font-weight:700}
.badge{display:inline-flex;align-items:center;gap:3px;border-radius:10px;padding:1px 8px;font-size:11px;font-weight:700;color:#fff;white-space:nowrap}
.badge.cat-default{background:var(--default)}
.badge.cat-overlap{background:var(--overlap)}
.badge.cat-patch{background:var(--patch)}
.badge.cat-ambiguity{background:var(--ambiguity)}
.badge.cat-concise{background:var(--concise)}
.badge.cat-conflict{background:var(--conflict)}
.badge.decision-apply{background:var(--apply)}
.badge.decision-dismiss{background:var(--dismiss)}
.dep-badge{background:var(--dep);border:0;color:#fff;font-size:11px;font-weight:700;border-radius:10px;padding:1px 8px}
.locations{display:flex;gap:6px;font-family:ui-monospace,monospace;font-size:12px;flex-wrap:wrap;color:var(--muted)}
.controls{display:flex;gap:8px;padding:0 12px 8px}
.decision{border:0;margin:0;padding:0;display:flex;gap:8px;flex-wrap:wrap}
.decision label{cursor:pointer;border:1px solid var(--border);border-radius:6px;padding:3px 8px}
.decision .decision-apply{border-color:var(--apply);background:color-mix(in srgb,var(--apply) 12%,transparent)}
.decision .decision-dismiss{border-color:var(--dismiss);background:color-mix(in srgb,var(--dismiss) 12%,transparent)}
.decision .decision-apply input{accent-color:var(--apply)}
.decision .decision-dismiss input{accent-color:var(--dismiss)}
.decision .decision-apply:has(input:checked){border-color:var(--apply);background:var(--apply);color:#fff}
.decision .decision-dismiss:has(input:checked){border-color:var(--dismiss);background:var(--dismiss);color:#fff}
.card-body{display:none;border-top:1px solid var(--border);padding:8px 12px}
.card.open .card-body{display:block}
.detail,.quote-box,.code-context,.diff-box{margin:8px 0;padding:8px;border:1px solid var(--border);border-radius:6px}
.detail-head,.box-head{font-size:12px;color:var(--muted);margin-bottom:4px}
.markdown-line{min-height:1.4em}
.markdown-code{background:color-mix(in srgb,var(--border) 45%,transparent);border-radius:3px;padding:1px 4px;font-family:ui-monospace,monospace}
.markdown-block{overflow:auto;margin:6px 0;padding:8px;background:color-mix(in srgb,var(--border) 30%,transparent);border-radius:4px}
.code-lines,.diff-lines{margin:0;overflow:auto;font-family:ui-monospace,monospace;font-size:12px;line-height:1.5}
.code-line{display:flex;min-width:max-content}
.code-line.target{background:color-mix(in srgb,var(--overlap) 25%,transparent)}
.line-no{width:4em;flex:none;padding-right:8px;text-align:right;color:var(--muted);user-select:none}
.code-text{white-space:pre}
.diff-add{color:var(--apply)}
.diff-del{color:var(--conflict)}
.unavailable{color:var(--muted);font-size:13px}
footer{position:fixed;left:0;right:0;bottom:0;background:var(--card);border-top:1px solid var(--border);padding:10px 16px;display:flex;gap:16px;align-items:center;flex-wrap:wrap;font-size:13px}
#params{font-family:ui-monospace,monospace}
#save-status{color:var(--muted)}
#dep-violations{color:var(--conflict);font-weight:700}
.filter-picker{display:flex;gap:4px;flex-wrap:wrap}
#toast{position:fixed;right:16px;bottom:76px;z-index:1;padding:9px 12px;border-radius:6px;background:var(--apply);color:#fff;box-shadow:0 4px 14px #0004}
#toast[data-kind="error"]{background:var(--conflict)}
</style>
</head>
<body>
<header class="report-header" id="report-header"></header>
<details class="manifest" id="manifest"><summary>監査対象ファイル一覧</summary><div id="manifest-body"></div></details>
<div class="toolbar">
<button id="expand-all">すべて展開</button><button id="collapse-all">すべて折りたたむ</button>
<div class="theme-picker" role="group" aria-label="テーマ"><button data-theme="auto">自動</button><button data-theme="light">ライト</button><button data-theme="dark">ダーク</button></div>
</div>
<div id="report"></div>
<footer><span id="progress"></span><span id="dep-violations"></span><div class="filter-picker" role="group" aria-label="表示する項目"><button data-filter="pending">未処理</button><button data-filter="apply">適用リスト</button><button data-filter="dismiss">対応しないリスト</button><button data-filter="all">すべて</button></div><span id="params"></span><button id="copy-run-dir" disabled>実行ディレクトリをコピー</button><button id="save-state" disabled>状態ファイルを保存</button><span id="save-status" role="status" aria-live="polite">未保存</span></footer>
<div id="toast" role="status" aria-live="polite" hidden></div>
<script>
const DATA = __AUDIT_DATA__;
const state = {schema_version: 1, items: {}};
let fileHandle = null, filterMode = "pending", wasComplete = false, completionPrompted = false, toastTimer = null;
const CAN_SERVER_SAVE = location.protocol === "http:" && location.hostname === "127.0.0.1";
const CAN_FILE_SAVE = typeof window.showSaveFilePicker === "function";
const CAN_SAVE_STATE = CAN_SERVER_SAVE || CAN_FILE_SAVE;
const CATS = [["default","🔵 デフォルト動作と重複"],["overlap","🟡 ルール間の重複"],["patch","🟠 一時的な修正"],["ambiguity","⚪ 曖昧・解釈が不安定"],["concise","🟢 冗長な表現"],["conflict","⚠️ コンフリクト"]];
const CAT_LABEL = Object.fromEntries(CATS);
const DECISIONS = [["apply","✅ 適用する"],["dismiss","🚫 対応しない"]];
const DECISION_LABEL = Object.fromEntries(DECISIONS);
const FILTER_LABEL = {pending:"未処理",apply:"適用リスト",dismiss:"対応しないリスト",all:"すべて"};
const THEME_KEY = "ai-audit-report-theme";
// depends_on は片方向しか書かれていなくても両方向で機能させる(対称和)
const DEPS = new Map();
function buildDeps(){for(const item of DATA.items)DEPS.set(item.id,new Set());for(const item of DATA.items){for(const other of (item.depends_on||[])){if(!DEPS.has(other))continue;DEPS.get(item.id).add(other);DEPS.get(other).add(item.id);}}}
function closure(id){const seen=new Set([id]);const queue=[id];while(queue.length){const current=queue.pop();for(const next of (DEPS.get(current)||[])){if(!seen.has(next)){seen.add(next);queue.push(next);}}}seen.delete(id);return [...seen];}

function el(tag, cls, text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;}
function itemState(id){const key=String(id);if(!state.items[key])state.items[key]={decision:null};return state.items[key];}
function syncStateItems(){for(const item of DATA.items)itemState(item.id);}
function allItemsCompleted(){return DATA.items.every(item=>itemState(item.id).decision!==null);}
function showToast(message,kind="success"){const toast=document.getElementById("toast");clearTimeout(toastTimer);toast.textContent=message;toast.dataset.kind=kind;toast.hidden=false;toastTimer=window.setTimeout(()=>{toast.hidden=true;},4000);}
async function copyRunDir(){const runDir=typeof DATA.run_dir==="string"?DATA.run_dir:"";if(!runDir)return;try{if(navigator.clipboard&&window.isSecureContext){try{await navigator.clipboard.writeText(runDir);showToast("✅ 実行ディレクトリをコピーしました");return;}catch(e){}}const input=document.createElement("textarea");input.value=runDir;input.setAttribute("readonly","");input.style.position="fixed";input.style.opacity="0";document.body.appendChild(input);try{input.select();if(!document.execCommand("copy"))throw new Error("copy failed");}finally{input.remove();}showToast("✅ 実行ディレクトリをコピーしました");}catch(e){showToast("実行ディレクトリをコピーできませんでした","error");}}
function appendInline(parent,text){const re=/(\*\*[^*\n]+\*\*|`[^`\n]+`)/g;let pos=0;for(const match of text.matchAll(re)){parent.appendChild(document.createTextNode(text.slice(pos,match.index)));const token=match[0];if(token.startsWith("**")){parent.appendChild(el("strong","",token.slice(2,-2)));}else{parent.appendChild(el("code","markdown-code",token.slice(1,-1)));}pos=match.index+token.length;}parent.appendChild(document.createTextNode(text.slice(pos)));}
function markdown(parent,text){let inCode=false,code=[];for(const line of String(text||"").split("\n")){if(line.startsWith("```")){if(inCode){parent.appendChild(el("pre","markdown-block",code.join("\n")));code=[];}inCode=!inCode;continue;}if(inCode){code.push(line);continue;}const p=el("div","markdown-line");appendInline(p,line);parent.appendChild(p);}if(inCode)parent.appendChild(el("pre","markdown-block",code.join("\n")));}
function buildHeader(){const h=document.getElementById("report-header");const title=(DATA.platform||"")+" 設定監査レポート";h.appendChild(el("h1","",title));const bits=[];if(DATA.scope)bits.push("スコープ: "+DATA.scope);if(DATA.source_file_mode)bits.push("ソースファイルモード");if(DATA.generated_at)bits.push(DATA.generated_at);h.appendChild(el("p","meta",bits.join(" · ")));document.title=title;}
function buildManifest(){const box=document.getElementById("manifest-body"),rows=DATA.manifest||[];if(!rows.length){document.getElementById("manifest").hidden=true;return;}const table=el("table");const head=el("tr");for(const label of ["ファイル","種別","備考"])head.appendChild(el("th","",label));table.appendChild(head);for(const row of rows){const tr=el("tr");const note=row.note||"";tr.appendChild(el("td",note?"excluded":"",row.file||""));tr.appendChild(el("td","",row.type||""));tr.appendChild(el("td","",note));table.appendChild(tr);}box.appendChild(table);}
function build(){buildDeps();buildHeader();buildManifest();const root=document.getElementById("report");root.textContent="";for(const [cat,title] of CATS){const items=DATA.items.filter(i=>i.category===cat);if(!items.length)continue;const group=el("section","cat-group");group.dataset.category=cat;group.appendChild(el("h2","cat-title",title));for(const item of items)group.appendChild(card(item));root.appendChild(group);}if(!DATA.items.length)root.appendChild(el("p","","対応が必要な項目はありません。"));refresh();}
function locationText(item){const targets=(item.targets&&item.targets.length)?item.targets:[{file:item.file,section:item.section}];return targets.map(t=>t.section?`${t.file} > ${t.section}`:t.file).join(item.category==="conflict"?" ↔ ":" ← ");}
function card(item){const c=el("article","card");c.dataset.id=item.id;const bodyId="item-body-"+item.id;const h=el("div","card-header");const toggle=el("button","card-toggle");toggle.type="button";toggle.setAttribute("aria-expanded","false");toggle.setAttribute("aria-controls",bodyId);toggle.appendChild(el("span","disclosure","▸"));toggle.appendChild(el("span","",item.id+"."));toggle.appendChild(el("span","badge cat-"+item.category,CAT_LABEL[item.category]||item.category));toggle.appendChild(el("span","summary",item.summary||""));toggle.addEventListener("click",()=>setOpen(c,!c.classList.contains("open")));h.appendChild(toggle);h.appendChild(el("span","decision-status"));
const deps=closure(item.id);if(deps.length){const depButton=el("button","dep-badge","🔗 依存: "+deps.map(d=>"#"+d).join(", "));depButton.type="button";depButton.title="依存する項目へ移動";depButton.addEventListener("click",()=>focusCard(deps[0]));h.appendChild(depButton);}
if(item.estimated_reduction)h.appendChild(el("span","meta","削減見込み 約"+item.estimated_reduction+"語"));
h.appendChild(el("span","locations",locationText(item)));c.appendChild(h);
const ctl=el("div","controls");ctl.appendChild(decision(item.id));c.appendChild(ctl);
const body=el("div","card-body");body.id=bodyId;
for(const d of (item.details||[])){const box=el("section","detail");box.appendChild(el("div","detail-head",d.label||""));const content=el("div","text");markdown(content,d.text||"");box.appendChild(content);body.appendChild(box);}
if(item.quote){const box=el("section","quote-box");box.appendChild(el("div","box-head","対象ルール(原文)"));box.appendChild(el("pre","code-lines",item.quote));body.appendChild(box);}
appendContext(body,item.code_context);
appendDiff(body,item.diff);
c.appendChild(body);return c;}
function focusCard(id){const target=document.querySelector(`.card[data-id="${id}"]`);if(!target)return;if(target.hidden){filterMode="all";refresh();}target.scrollIntoView({behavior:"smooth",block:"center"});target.classList.add("flash");window.setTimeout(()=>target.classList.remove("flash"),1500);}
function setOpen(card,open){card.classList.toggle("open",open);const button=card.querySelector(".card-toggle");button.setAttribute("aria-expanded",String(open));button.querySelector(".disclosure").textContent=open?"▾":"▸";}
function decision(id){const group=el("fieldset","decision");group.setAttribute("aria-label","項目の対応方針");for(const [value,label] of DECISIONS){const labelEl=el("label","decision-"+value,label);const input=document.createElement("input");input.type="checkbox";input.value=value;input.addEventListener("change",()=>{applyDecision(id,input.checked?value:null);setOpen(input.closest(".card"),false);refresh();maybeOfferAutoSave();});labelEl.prepend(input);group.appendChild(labelEl);}return group;}
// apply は依存閉包と連動させる。dismiss は片方だけ却下する判断が成立するので連動しない
function applyDecision(id,value){const deps=closure(id);const s=itemState(id);if(value==="apply"&&deps.length){const missing=deps.filter(d=>itemState(d).decision!=="apply");if(missing.length){const ok=window.confirm(`項目${id}は${missing.map(d=>"項目"+d).join("・")}と同時適用が必要です。まとめて「適用する」にしますか？`);if(!ok){s.decision=null;return;}for(const d of deps)itemState(d).decision="apply";}}
if(s.decision==="apply"&&value!=="apply"&&deps.length){const paired=deps.filter(d=>itemState(d).decision==="apply");if(paired.length&&window.confirm(`項目${id}は${paired.map(d=>"項目"+d).join("・")}と同時適用が必要です。${paired.map(d=>"項目"+d).join("・")}も「適用する」を外しますか？`)){for(const d of paired)itemState(d).decision=null;}}
s.decision=value;}
function depViolations(){const bad=[];for(const item of DATA.items){if(itemState(item.id).decision!=="apply")continue;for(const d of closure(item.id)){if(itemState(d).decision!=="apply"&&item.id<d)bad.push([item.id,d]);else if(itemState(d).decision!=="apply"&&item.id>d)bad.push([d,item.id]);}}
return [...new Set(bad.map(p=>p.join("-")))];}
function appendContext(parent,context){if(!context)return;const box=el("section","code-context");box.appendChild(el("div","box-head","対象箇所(前後3行)"));if(context.error){box.appendChild(el("div","unavailable",context.error));parent.appendChild(box);return;}const pre=el("pre","code-lines");for(const line of context.lines){const row=el("span","code-line"+(line.target?" target":""));row.appendChild(el("span","line-no",String(line.number)));row.appendChild(el("span","code-text",line.text));pre.appendChild(row);}box.appendChild(pre);parent.appendChild(box);}
function appendDiff(parent,diff){if(!diff)return;const box=el("section","diff-box");box.appendChild(el("div","box-head","適用される差分"));const pre=el("pre","diff-lines");for(const line of String(diff).split("\n")){const cls=line.startsWith("+")?"diff-add":(line.startsWith("-")?"diff-del":"");pre.appendChild(el("div",cls,line));}box.appendChild(pre);parent.appendChild(box);}
function matchesFilter(s){return filterMode==="all"||(filterMode==="pending"&&s.decision===null)||filterMode===s.decision;}
function refresh(){const picked={apply:[],dismiss:[]};for(const item of DATA.items){const s=itemState(item.id);if(s.decision)picked[s.decision].push(item.id);const c=document.querySelector(`.card[data-id="${item.id}"]`);if(c){c.classList.toggle("completed",s.decision!==null);for(const [value] of DECISIONS)c.classList.toggle("decision-"+value,s.decision===value);c.hidden=!matchesFilter(s);const status=c.querySelector(".decision-status");status.textContent=s.decision?DECISION_LABEL[s.decision]:"";status.className="decision-status"+(s.decision?" badge decision-"+s.decision:"");for(const input of c.querySelectorAll(".decision input"))input.checked=input.value===s.decision;}}
for(const group of document.querySelectorAll(".cat-group"))group.hidden=![...group.querySelectorAll(".card")].some(c=>!c.hidden);
const done=picked.apply.length+picked.dismiss.length;const counts={pending:DATA.items.length-done,apply:picked.apply.length,dismiss:picked.dismiss.length,all:DATA.items.length};
const reduction=DATA.items.filter(i=>picked.apply.includes(i.id)).reduce((sum,i)=>sum+(Number(i.estimated_reduction)||0),0);
document.getElementById("progress").textContent=`未処理 ${counts.pending}/${DATA.items.length}（適用 ${counts.apply} / 対応しない ${counts.dismiss}）` + (reduction?` 短縮見込み 約${reduction}語`:"");
const violations=depViolations();document.getElementById("dep-violations").textContent=violations.length?`依存違反 ${violations.length}（${violations.map(v=>"#"+v.replace("-"," と #")).join(", ")}）`:"";
document.getElementById("params").textContent=picked.apply.length?`適用: ${picked.apply.join(",")}`:"適用: (未選択)";
for(const button of document.querySelectorAll("[data-filter]")){button.setAttribute("aria-pressed",String(button.dataset.filter===filterMode));button.textContent=`${FILTER_LABEL[button.dataset.filter]} (${counts[button.dataset.filter]})`;}
document.getElementById("save-state").disabled=!CAN_SAVE_STATE||done!==DATA.items.length||violations.length>0;}
async function saveToFilePicker(){fileHandle=await window.showSaveFilePicker({suggestedName:"state.json",types:[{description:"JSON",accept:{"application/json":[".json"]}}]});const writer=await fileHandle.createWritable();await writer.write(JSON.stringify(state,null,1));await writer.close();}
async function saveState(){if(!CAN_SAVE_STATE||!allItemsCompleted()||depViolations().length)return;syncStateItems();const status=document.getElementById("save-status");if(!CAN_SERVER_SAVE){const reopenHint="サーバー経由で開き直すと自動保存されます:\n  audit-report "+(DATA.platform_key||"")+"\n\nそれでもこのファイルに保存しますか？";if(!window.confirm(reopenHint)){status.textContent="保存を取り消しました（audit-report で開き直してください）";return;}}status.textContent="保存中…";try{if(CAN_SERVER_SAVE){const response=await fetch("/api/state",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(state)});if(!response.ok)throw new Error(await response.text());}else{await saveToFilePicker();}status.textContent="✅ 保存済み "+new Date().toLocaleTimeString();showToast("✅ state.json を保存しました");}catch(e){if(e&&e.name==="AbortError"){status.textContent="保存を取り消しました";return;}status.textContent="保存に失敗しました。";showToast("state.json の保存に失敗しました","error");}}
function maybeOfferAutoSave(){const complete=allItemsCompleted()&&!depViolations().length;if(complete&&!wasComplete&&CAN_SERVER_SAVE&&!completionPrompted){completionPrompted=true;if(window.confirm("すべての項目を判断しました。state.json に保存しますか？"))saveState();}if(!complete)completionPrompted=false;wasComplete=complete;}
function setTheme(theme){if(theme==="auto")delete document.documentElement.dataset.theme;else document.documentElement.dataset.theme=theme;for(const b of document.querySelectorAll("[data-theme]")){b.setAttribute("aria-pressed",String(b.dataset.theme===theme));}try{localStorage.setItem(THEME_KEY,theme);}catch(e){}}
function heartbeat(){if(CAN_SERVER_SAVE)fetch("/api/heartbeat",{method:"POST",keepalive:true}).catch(()=>{});}
document.getElementById("expand-all").addEventListener("click",()=>document.querySelectorAll(".card").forEach(c=>setOpen(c,true)));
document.getElementById("collapse-all").addEventListener("click",()=>document.querySelectorAll(".card").forEach(c=>setOpen(c,false)));
document.getElementById("save-state").addEventListener("click",saveState);
const copyButton=document.getElementById("copy-run-dir");copyButton.disabled=!(typeof DATA.run_dir==="string"&&DATA.run_dir);copyButton.addEventListener("click",copyRunDir);
document.querySelectorAll("[data-filter]").forEach(b=>b.addEventListener("click",()=>{filterMode=b.dataset.filter;refresh();}));
document.querySelectorAll(".theme-picker button").forEach(b=>b.addEventListener("click",()=>setTheme(b.dataset.theme)));
let savedTheme="auto";try{savedTheme=localStorage.getItem(THEME_KEY)||"auto";}catch(e){}setTheme(savedTheme);
if(!CAN_SAVE_STATE){document.getElementById("save-status").textContent="進捗保存に非対応です。audit-report から開き直してください。";}else if(!CAN_SERVER_SAVE){document.getElementById("save-status").textContent="サーバー経由ではありません（audit-report "+(DATA.platform_key||"")+" で開き直すと自動保存されます）。";}
build();heartbeat();if(CAN_SERVER_SAVE)window.setInterval(heartbeat,60000);
</script>
</body>
</html>
"""


def resolve_path(display_path):
    """表示用パスを読み取り可能な実パスへ。~ と $HOME を展開する(表示側は展開しない)。"""
    return Path(os.path.expandvars(os.path.expanduser(str(display_path))))


def read_config_file(display_path):
    """監査対象ファイルの本文を返す。読めない理由はエラー文字列で返し、例外を投げない。"""
    path = resolve_path(display_path)
    try:
        raw = path.read_bytes()
    except (OSError, ValueError):
        return {"error": "対象ファイルを読み取れませんでした。"}
    if b"\0" in raw:
        return {"error": "バイナリファイルのため、対象箇所は表示できません。"}
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return {"error": "UTF-8として読めないため、対象箇所は表示できません。"}


def extract_context(content, quote, padding=CONTEXT_PADDING):
    """quote の文字列検索で位置を特定し、前後 padding 行を返す。行番号には依存しない。"""
    if not quote:
        return {"error": "引用がないため、対象箇所は表示できません。"}
    lines = content.splitlines()
    quote_lines = [line for line in str(quote).splitlines() if line.strip()]
    if not quote_lines:
        return {"error": "引用がないため、対象箇所は表示できません。"}
    needle = quote_lines[0].strip()
    start = None
    for number, line in enumerate(lines, start=1):
        if needle in line:
            start = number
            break
    if start is None:
        return {"error": "引用が本文中に見つかりません（指摘が古い可能性があります）。"}
    end = min(len(lines), start + len(quote_lines) - 1)
    first = max(1, start - padding)
    last = min(len(lines), end + padding)
    return {"lines": [
        {"number": number, "text": lines[number - 1], "target": start <= number <= end}
        for number in range(first, last + 1)
    ]}


def prepare_report_data(audit):
    report = json.loads(json.dumps(audit))
    cache = {}
    for item in report.get("items", []):
        display_path = item.get("file", "")
        if display_path not in cache:
            cache[display_path] = read_config_file(display_path)
        cached = cache[display_path]
        if isinstance(cached, dict):
            item["code_context"] = cached
        else:
            item["code_context"] = extract_context(cached, item.get("quote", ""))
    return report


def render(audit):
    data = json.dumps(audit, ensure_ascii=False).replace("</", "<\\/")
    return HTML_TEMPLATE.replace("__AUDIT_DATA__", data)


def main(argv):
    if len(argv) != 3:
        print("Usage: generate_audit_report.py <audit.json> <output.html>", file=sys.stderr)
        return 1
    with open(argv[1], encoding="utf-8") as f:
        audit = json.load(f)
    report = prepare_report_data(audit)
    with open(argv[2], "w", encoding="utf-8") as f:
        f.write(render(report))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
