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


LEAD_LINES = 30
LINE_SPEC = re.compile(r"^~?(?P<start>[1-9][0-9]*)(?:-(?P<end>[1-9][0-9]*))?$")


HTML_TEMPLATE = r"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Review Report</title>
<style>
:root{--bg:#f4f5f8;--card:#fff;--surface:#f7f8fa;--border:#e3e6ec;--text:#1b1f27;--muted:#667085;--link:#4f46e5;--shadow:0 1px 2px #1018280d,0 1px 3px #1018280f;--shadow-hover:0 4px 14px #1018281a;
--high:#e5484d;--medium:#d9930d;--low:#2fa66a;--claude:#d97757;--gemini:#4285f4;--codex:#10a37f;--carry:#7c5cf0;--carry-fixed:#d6409f;
--blue:#2563eb;--slate:#475467;--copy:#0891b2;--inline-code:#d6336c;--on-solid:#fff;
--code-bg:#f6f8fa;--code-line:#1f2328;--code-target:#fff3c4;
--hl-keyword:#cf222e;--hl-string:#0a3069;--hl-number:#0550ae;--hl-comment:#6e7781;--hl-title:#8250df;--hl-attr:#116329;--hl-meta:#953800;}
:root[data-theme="dark"]{--bg:#1b1f27;--card:#242935;--surface:#2c3240;--border:#3a4151;--text:#e8ebf1;--muted:#a9b3c4;--link:#8b93ff;--shadow:0 1px 2px #0004;--shadow-hover:0 4px 16px #0006;--carry:#a78bfa;--carry-fixed:#f472b6;
--blue:#60a5fa;--slate:#cbd5e1;--copy:#22d3ee;--inline-code:#f783ac;--on-solid:#0b0d12;
--code-bg:#1d212b;--code-line:#e6edf3;--code-target:#4b3f14;
--hl-keyword:#ff7b72;--hl-string:#a5d6ff;--hl-number:#79c0ff;--hl-comment:#8b949e;--hl-title:#d2a8ff;--hl-attr:#7ee787;--hl-meta:#ffa657;}
@media(prefers-color-scheme:dark){:root:not([data-theme]){--bg:#1b1f27;--card:#242935;--surface:#2c3240;--border:#3a4151;--text:#e8ebf1;--muted:#a9b3c4;--link:#8b93ff;--shadow:0 1px 2px #0004;--shadow-hover:0 4px 16px #0006;--carry:#a78bfa;--carry-fixed:#f472b6;
--blue:#60a5fa;--slate:#cbd5e1;--copy:#22d3ee;--inline-code:#f783ac;--on-solid:#0b0d12;
--code-bg:#1d212b;--code-line:#e6edf3;--code-target:#4b3f14;
--hl-keyword:#ff7b72;--hl-string:#a5d6ff;--hl-number:#79c0ff;--hl-comment:#8b949e;--hl-title:#d2a8ff;--hl-attr:#7ee787;--hl-meta:#ffa657;}}
*{box-sizing:border-box}
body{margin:0;padding:28px 24px 110px;background:var(--bg);color:var(--text);font-family:system-ui,-apple-system,"Hiragino Sans","Hiragino Kaku Gothic ProN",sans-serif;font-size:14px;line-height:1.65;-webkit-font-smoothing:antialiased}
#report,.report-header,.toolbar{max-width:1440px;margin-left:auto;margin-right:auto}
a{color:var(--link);text-decoration:none}a:hover{text-decoration:underline}
button{cursor:pointer;font:inherit;font-size:13px;font-weight:500;border:1px solid var(--border);background:var(--card);color:var(--text);border-radius:8px;padding:6px 12px;transition:background .15s,border-color .15s,box-shadow .15s}
button:hover:not(:disabled){background:var(--surface);border-color:color-mix(in srgb,var(--muted) 45%,var(--border))}
button:disabled{cursor:not-allowed;opacity:.5}
button:focus-visible,.decision input:focus-visible{outline:2px solid var(--link);outline-offset:2px}
.report-header{margin-bottom:18px}
.breadcrumbs,.meta,.save-help{color:var(--muted);font-size:13px}
.breadcrumbs{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.report-header h1{font-size:24px;line-height:1.35;letter-spacing:-.01em;margin:6px 0 4px}
.author{margin:0;color:var(--muted);font-size:13px}
.toolbar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:22px}
#expand-all{--c:var(--blue)}#collapse-all{--c:var(--carry)}#copy-run-dir{--c:var(--copy)}
#expand-all,#collapse-all,#copy-run-dir,.theme-picker button,.filter-picker button{color:var(--c);background:color-mix(in srgb,var(--c) 12%,var(--card));border-color:color-mix(in srgb,var(--c) 40%,var(--border))}
#expand-all:hover:not(:disabled),#collapse-all:hover:not(:disabled),#copy-run-dir:hover:not(:disabled),.theme-picker button:hover,.filter-picker button:hover{background:color-mix(in srgb,var(--c) 22%,var(--card));border-color:var(--c)}
.theme-picker button[aria-pressed="true"],.filter-picker button[aria-pressed="true"]{background:var(--c);border-color:var(--c);color:var(--on-solid);font-weight:600}
.theme-picker{display:flex;margin-left:auto;gap:6px}
.theme-picker button[data-theme="auto"]{--c:var(--blue)}.theme-picker button[data-theme="light"]{--c:var(--medium)}.theme-picker button[data-theme="dark"]{--c:var(--link)}
.priority-group{margin-top:28px}
.prio-title{display:flex;align-items:center;gap:8px;margin:0 0 10px;font-size:13px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:var(--muted)}
.prio-title::before{content:"";width:9px;height:9px;border-radius:50%;background:var(--prio)}
.priority-group[data-priority="high"]{--prio:var(--high)}.priority-group[data-priority="medium"]{--prio:var(--medium)}.priority-group[data-priority="low"]{--prio:var(--low)}
.prio-count{font-size:12px;font-weight:600;padding:0 8px;border-radius:999px;background:color-mix(in srgb,var(--prio) 14%,transparent);color:var(--prio)}
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;margin-bottom:10px;box-shadow:var(--shadow);transition:box-shadow .15s,opacity .15s}
.card:hover{box-shadow:var(--shadow-hover)}
.card.completed{opacity:.6}
.card-header{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:4px 24px;align-items:start;padding:12px 16px 6px}.card-meta{display:flex;align-items:center;justify-content:flex-end;gap:12px;min-width:0;padding-top:2px}
.card-toggle{display:flex;align-items:center;gap:8px;border:0;padding:0;background:transparent;color:var(--text);text-align:left;flex-wrap:wrap;min-width:0;font-weight:600;font-size:14px;border-radius:6px}
.card-toggle:hover{background:transparent;text-decoration:none;color:var(--link)}
.summary{font-weight:600;flex:1 1 100%;padding-left:26px;line-height:1.55}
.disclosure{width:1.2em;text-align:center;color:var(--muted);flex:none}
.badge{display:inline-flex;align-items:center;gap:4px;border-radius:999px;padding:1px 9px;font-size:11px;font-weight:700;white-space:nowrap;--c:var(--muted);color:var(--c);background:color-mix(in srgb,var(--c) 14%,transparent)}
.badge.high{--c:var(--high)}.badge.medium{--c:var(--medium)}.badge.low{--c:var(--low)}
.badge.ai-claude{--c:var(--claude)}.badge.ai-gemini{--c:var(--gemini)}.badge.ai-codex{--c:var(--codex)}.badge.ai-unknown{--c:var(--muted)}
.badge.carry{--c:var(--carry)}.badge.carry.carry-fixed{--c:var(--carry-fixed)}.badge.done{--c:var(--muted)}
.badge.decision-dismiss{--c:var(--muted)}.badge.decision-fix{--c:var(--low)}.badge.decision-post{--c:var(--link)}
.ai-icon{width:12px;height:12px;fill:currentColor;stroke:currentColor;stroke-width:1.6}
.confidence{color:var(--muted);font-size:12px;white-space:nowrap}
.file-links{display:flex;gap:12px;min-width:0;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px;flex-wrap:wrap}
.file-path{display:block;max-width:30rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;direction:rtl;text-align:left}.controls{display:flex;gap:8px;padding:6px 16px 14px}
.decision{border:0;margin:0;padding:0;display:flex;gap:8px;flex-wrap:wrap}
.decision label{display:inline-flex;align-items:center;gap:6px;cursor:pointer;border:1px solid color-mix(in srgb,var(--c) 40%,var(--border));border-radius:8px;padding:4px 12px;font-size:13px;font-weight:500;color:var(--c);background:color-mix(in srgb,var(--c) 10%,var(--card));transition:background .15s,border-color .15s}
.decision label:hover{background:color-mix(in srgb,var(--c) 20%,var(--card));border-color:var(--c)}
.decision input{accent-color:var(--link)}
.decision .decision-fix{--c:var(--low)}.decision .decision-post{--c:var(--link)}.decision .decision-dismiss{--c:var(--muted)}
.decision input{accent-color:var(--c)}
.decision label:has(input:checked){border-color:var(--c);background:var(--c);color:var(--on-solid);font-weight:600}
.card.completed.decision-fix{border-color:color-mix(in srgb,var(--low) 40%,var(--border))}
.card.completed.decision-post{border-color:color-mix(in srgb,var(--link) 40%,var(--border))}
.card-body{display:none;border-top:1px solid var(--border);padding:14px 16px 16px}
.card.open .card-body{display:block}
.source{--c:var(--muted);margin:0 0 12px;padding:12px 14px;background:color-mix(in srgb,var(--c) 7%,var(--card));border-left:3px solid var(--c);border-radius:10px}
.source.ai-claude{--c:var(--claude)}.source.ai-gemini{--c:var(--gemini)}.source.ai-codex{--c:var(--codex)}
.code-context{margin:0;padding:0;border-radius:10px;overflow:hidden;background:var(--code-bg);border:1px solid var(--border)}
.src-head{font-size:12px;font-weight:700;color:var(--c);margin-bottom:6px}
.context-head{font-size:12px;color:var(--muted);padding:8px 14px;border-bottom:1px solid var(--border)}
.markdown-line{min-height:1.4em}
.markdown-code{background:color-mix(in srgb,var(--inline-code) 12%,transparent);color:var(--inline-code);border-radius:4px;padding:1px 5px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.92em}
.markdown-block{overflow:auto;margin:8px 0;padding:10px 12px;background:var(--code-bg);border:1px solid var(--border);border-radius:8px}
.code-lines{margin:0;padding:8px 0;overflow:auto;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px;line-height:1.6;color:var(--code-line)}
.code-line{display:flex;min-width:max-content;padding-right:14px}
.code-line.target{background:var(--code-target)}
.line-no{width:3.6em;flex:none;padding-right:12px;text-align:right;color:var(--muted);user-select:none}
.code-text{white-space:pre}
.hljs-keyword,.hljs-built_in,.hljs-literal,.hljs-selector-tag,.hljs-doctag{color:var(--hl-keyword)}
.hljs-string,.hljs-regexp,.hljs-template-variable,.hljs-addition{color:var(--hl-string)}
.hljs-number,.hljs-symbol,.hljs-bullet,.hljs-variable,.hljs-selector-id{color:var(--hl-number)}
.hljs-comment,.hljs-quote,.hljs-deletion{color:var(--hl-comment);font-style:italic}
.hljs-title,.hljs-section,.hljs-selector-class,.hljs-type,.hljs-class .hljs-title{color:var(--hl-title)}
.hljs-attr,.hljs-attribute,.hljs-name,.hljs-tag,.hljs-property{color:var(--hl-attr)}
.hljs-meta,.hljs-params,.hljs-subst{color:var(--hl-meta)}
.hljs-emphasis{font-style:italic}.hljs-strong{font-weight:700}
.unavailable{color:var(--muted);font-size:13px;padding:10px 14px}
footer{position:fixed;left:0;right:0;bottom:0;background:color-mix(in srgb,var(--card) 82%,transparent);-webkit-backdrop-filter:blur(14px) saturate(160%);backdrop-filter:blur(14px) saturate(160%);border-top:1px solid var(--border);padding:10px 20px;display:flex;gap:14px;align-items:center;flex-wrap:wrap;font-size:13px}
#params{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--muted);font-size:12px}
#save-status{color:var(--muted)}
.filter-picker{display:flex;gap:6px;flex-wrap:wrap}
.filter-picker button[data-filter="pending"]{--c:var(--medium)}.filter-picker button[data-filter="fix"]{--c:var(--low)}.filter-picker button[data-filter="post"]{--c:var(--blue)}.filter-picker button[data-filter="dismiss"]{--c:var(--muted)}.filter-picker button[data-filter="all"]{--c:var(--slate)}
#save-state{background:var(--link);border-color:var(--link);color:var(--on-solid);margin-left:auto}
#save-state:hover:not(:disabled){background:color-mix(in srgb,var(--link) 88%,#000);border-color:transparent}
#toast{position:fixed;right:20px;bottom:84px;z-index:1;padding:10px 14px;border-radius:10px;background:var(--low);color:#fff;box-shadow:0 8px 24px #0004}
#toast[data-kind="error"]{background:var(--high)}
@media(max-width:900px){.card-header{grid-template-columns:minmax(0,1fr)}.card-meta{justify-content:flex-start;padding-left:26px;flex-wrap:wrap}.file-path{max-width:100%}}
@media(max-width:640px){body{padding:16px 12px 150px}.report-header h1{font-size:20px}.theme-picker{margin-left:0}#save-state{margin-left:0}}
</style>
<script defer src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.2/highlight.min.js" integrity="sha512-VSPLUv/n1Bmn+4zoxBNwpuFAO3//79I0Aax/qHDx24R47vylPcc9PrHDCqlePwHnh3joiM7/YTQhcXyQAAxvPQ==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
</head>
<body>
<header class="report-header" id="report-header"></header>
<div class="toolbar">
<button id="expand-all">すべて展開</button><button id="collapse-all">すべて折りたたむ</button>
<div class="theme-picker" role="group" aria-label="テーマ"><button data-theme="auto">自動</button><button data-theme="light">ライト</button><button data-theme="dark">ダーク</button></div>
</div>
<div id="report"></div>
<footer><span id="progress"></span><div class="filter-picker" role="group" aria-label="表示する指摘"><button data-filter="pending">未処理</button><button data-filter="fix">修正リスト</button><button data-filter="post">投稿リスト</button><button data-filter="dismiss">対応しないリスト</button><button data-filter="all">すべて</button></div><span id="params"></span><button id="copy-run-dir" disabled>実行ディレクトリをコピー</button><button id="save-state" disabled>状態ファイルを保存</button><span id="save-status" role="status" aria-live="polite">未保存</span></footer>
<div id="toast" role="status" aria-live="polite" hidden></div>
<script>
const DATA = __REVIEW_DATA__;
const state = {schema_version: 2, items: {}};
let fileHandle = null, filterMode = "pending", wasComplete = false, completionPrompted = false, toastTimer = null;
const CAN_SERVER_SAVE = location.protocol === "http:" && location.hostname === "127.0.0.1";
const CAN_FILE_SAVE = typeof window.showSaveFilePicker === "function";
const CAN_SAVE_STATE = CAN_SERVER_SAVE || CAN_FILE_SAVE;
const PRIO = [["high","High Priority"],["medium","Medium Priority"],["low","Low Priority"]];
const CARRY = {skipped_before:"前回スキップ",should_be_fixed:"前回対応済のはず",fixed_before:"前回修正済み（再指摘）",fix_skipped_before:"前回修正スキップ",fix_rejected_before:"前回修正却下",posted_before:"前回コメント投稿済み",should_be_posted:"前回投稿済のはず",post_skipped_before:"前回投稿スキップ"};
const DECISIONS = [["fix","🔧 修正する"],["post","💬 コメント投稿"],["dismiss","🚫 対応しない"]];
const DECISION_LABEL = Object.fromEntries(DECISIONS);
const FILTER_LABEL = {pending:"未処理",fix:"修正リスト",post:"投稿リスト",dismiss:"対応しないリスト",all:"すべて"};
const CARRY_STYLE = {fixed_before:"carry-fixed"};
const AI = {claude:{name:"Claude",shape:"claude"},codex:{name:"Codex",shape:"codex"},gemini:{name:"Gemini",shape:"gemini"}};
const THEME_KEY = "ai-review-report-theme";

function el(tag, cls, text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;}
function externalLink(text, href, cls){const a=el("a",cls,text);try{const url=new URL(href);if(url.protocol==="https:"||url.protocol==="http:"){a.href=url.href;a.target="_blank";a.rel="noopener noreferrer";return a;}}catch(e){}return el("span",cls,text);}
function itemState(id){const key=String(id);if(!state.items[key])state.items[key]={decision:null};return state.items[key];}
function syncStateItems(){for(const item of DATA.items)itemState(item.id);}
function allItemsCompleted(){return DATA.items.every(item=>itemState(item.id).decision!==null);}
function showToast(message,kind="success"){const toast=document.getElementById("toast");clearTimeout(toastTimer);toast.textContent=message;toast.dataset.kind=kind;toast.hidden=false;toastTimer=window.setTimeout(()=>{toast.hidden=true;},4000);}
async function copyRunDir(){const runDir=typeof DATA.run_dir==="string"?DATA.run_dir:"";if(!runDir)return;try{if(navigator.clipboard&&window.isSecureContext){try{await navigator.clipboard.writeText(runDir);showToast("✅ 実行ディレクトリをコピーしました");return;}catch(e){}}const input=document.createElement("textarea");input.value=runDir;input.setAttribute("readonly","");input.style.position="fixed";input.style.opacity="0";document.body.appendChild(input);try{input.select();if(!document.execCommand("copy"))throw new Error("copy failed");}finally{input.remove();}showToast("✅ 実行ディレクトリをコピーしました");}catch(e){showToast("実行ディレクトリをコピーできませんでした", "error");}}
function aiIcon(kind){const svg=document.createElementNS("http://www.w3.org/2000/svg","svg");svg.setAttribute("viewBox","0 0 16 16");svg.setAttribute("aria-hidden","true");svg.classList.add("ai-icon");const path=document.createElementNS(svg.namespaceURI,"path");const paths={claude:"M3 4h10v3H3zM3 9h10v3H3z",codex:"M8 1l2 3 3.5.5-2.5 2.5.6 3.5L8 9l-3.1 1.5.6-3.5L3 4.5 6.5 4z",gemini:"M8 1.2l1.4 5.4 5.4 1.4-5.4 1.4L8 14.8 6.6 9.4 1.2 8l5.4-1.4z"};path.setAttribute("d",paths[kind]||paths.codex);svg.appendChild(path);return svg;}
function aiBadge(ai){const info=AI[ai]||{name:ai||"AI",shape:"unknown"};const b=el("span","badge ai-"+(AI[ai]?ai:"unknown"));b.appendChild(aiIcon(info.shape));b.appendChild(document.createTextNode(info.name));return b;}
function maxConfidence(item){const values=item.sources.map(s=>Number(s.confidence)||0);return values.length?Math.max(...values):0;}
function appendInline(parent,text){const re=/(\*\*[^*\n]+\*\*|`[^`\n]+`)/g;let pos=0;for(const match of text.matchAll(re)){parent.appendChild(document.createTextNode(text.slice(pos,match.index)));const token=match[0];if(token.startsWith("**")){const strong=el("strong","",token.slice(2,-2));parent.appendChild(strong);}else{parent.appendChild(el("code","markdown-code",token.slice(1,-1)));}pos=match.index+token.length;}parent.appendChild(document.createTextNode(text.slice(pos)));}
function markdown(parent,text){let inCode=false,code=[];for(const line of String(text||"").split("\n")){if(line.startsWith("```")){if(inCode){parent.appendChild(el("pre","markdown-block",code.join("\n")));code=[];}inCode=!inCode;continue;}if(inCode){code.push(line);continue;}const p=el("div","markdown-line");appendInline(p,line);parent.appendChild(p);}if(inCode)parent.appendChild(el("pre","markdown-block",code.join("\n")));}
function buildHeader(){const h=document.getElementById("report-header"),repo=DATA.repository||{};const crumbs=el("div","breadcrumbs");if(repo.url)crumbs.appendChild(externalLink(repo.name||"リポジトリ",repo.url));else crumbs.appendChild(el("span","",repo.name||"リポジトリ情報なし"));if(DATA.head_ref_name)crumbs.appendChild(el("span","","/ "+DATA.head_ref_name));if(DATA.pr_url)crumbs.appendChild(externalLink("PR #"+DATA.pr_number,DATA.pr_url));else crumbs.appendChild(el("span","","PR #"+DATA.pr_number));h.appendChild(crumbs);const title=DATA.pr_title||"AI Review Report";h.appendChild(el("h1","",title));if(DATA.pr_author)h.appendChild(el("p","author","作成者: "+DATA.pr_author));document.title=title+" · AI Review Report";}
function build(){buildHeader();const root=document.getElementById("report");root.textContent="";for(const [prio,title] of PRIO){const items=DATA.items.filter(i=>i.priority===prio);if(!items.length)continue;const group=el("section","priority-group");group.dataset.priority=prio;const heading=el("h2","prio-title",title);heading.appendChild(el("span","prio-count",String(items.length)));group.appendChild(heading);for(const item of items)group.appendChild(card(item));root.appendChild(group);}if(!DATA.items.length)root.appendChild(el("p","","対応が必要な指摘はありません。"));refresh();}
function card(item){const c=el("article","card");c.dataset.id=item.id;const bodyId="item-body-"+item.id;const h=el("div","card-header");const toggle=el("button","card-toggle");toggle.type="button";toggle.setAttribute("aria-expanded","false");toggle.setAttribute("aria-controls",bodyId);toggle.appendChild(el("span","disclosure","▸"));toggle.appendChild(el("span","",item.id+"."));toggle.appendChild(el("span","badge "+item.priority,item.priority.toUpperCase()));for(const s of item.sources)toggle.appendChild(aiBadge(s.ai));if(item.carryover)toggle.appendChild(el("span","badge carry "+(CARRY_STYLE[item.carryover]||""),CARRY[item.carryover]||item.carryover));toggle.appendChild(el("span","summary",item.area+": "+item.summary));toggle.addEventListener("click",()=>setOpen(c,!c.classList.contains("open")));h.appendChild(toggle);const meta=el("div","card-meta");meta.appendChild(el("span","decision-status"));meta.appendChild(el("span","confidence","最大信頼度 "+maxConfidence(item)+"%"));const links=el("span","file-links");if(item.links&&item.links.pr_diff)links.appendChild(externalLink("PR差分",item.links.pr_diff));links.appendChild(filePathLink(item));meta.appendChild(links);h.appendChild(meta);c.appendChild(h);const ctl=el("div","controls");ctl.appendChild(decision(item.id));c.appendChild(ctl);const body=el("div","card-body");body.id=bodyId;for(const s of item.sources){const box=el("section","source ai-"+(AI[s.ai]?s.ai:"unknown"));box.appendChild(el("div","src-head",(AI[s.ai]?.name||s.ai)+" #"+s.original_number+" (影響度: "+s.impact+" / 信頼度: "+s.confidence+")"));const content=el("div","text");markdown(content,s.text);box.appendChild(content);body.appendChild(box);}appendContext(body,item.code_context,item.file);c.appendChild(body);return c;}
function filePathLink(item){const text=item.file+":"+item.line_spec;const node=item.links&&item.links.snapshot?externalLink(text,item.links.snapshot,"file-path"):el("span","file-path",text);node.textContent="";node.appendChild(el("bdi","",text));node.title=text;return node;}
function setOpen(card,open){card.classList.toggle("open",open);const button=card.querySelector(".card-toggle");button.setAttribute("aria-expanded",String(open));button.querySelector(".disclosure").textContent=open?"▾":"▸";}
function decision(id){const group=el("fieldset","decision");group.setAttribute("aria-label","指摘の対応方針");for(const [value,label] of DECISIONS){const labelEl=el("label","decision-"+value,label);const input=document.createElement("input");input.type="checkbox";input.value=value;input.addEventListener("change",()=>{const s=itemState(id);s.decision=input.checked?value:null;setOpen(input.closest(".card"),false);refresh();maybeOfferAutoSave();});labelEl.prepend(input);group.appendChild(labelEl);}return group;}
const HL_ALIAS={sh:"bash",zsh:"bash",py:"python",js:"javascript",jsx:"javascript",ts:"typescript",tsx:"typescript",yml:"yaml",md:"markdown",rb:"ruby",rs:"rust",kt:"kotlin",toml:"ini",html:"xml",htm:"xml"};
function highlightLang(file){if(typeof hljs==="undefined")return null;const name=String(file||"").split("/").pop().toLowerCase();const ext=name.includes(".")?name.split(".").pop():name;const lang=HL_ALIAS[ext]||ext;return hljs.getLanguage(lang)?lang:null;}
function splitHighlighted(html){const out=[],open=[];for(const raw of html.split("\n")){const line=open.join("")+raw;for(const m of raw.matchAll(/<span[^>]*>|<\/span>/g)){if(m[0]==="</span>")open.pop();else open.push(m[0]);}out.push(line+"</span>".repeat(open.length));}return out;}
function highlightedLines(context,file){const lines=context.lines;const lang=highlightLang(file);if(!lang)return null;try{const lead=context.lead||[];const rows=splitHighlighted(hljs.highlight(lead.concat(lines.map(l=>l.text)).join("\n"),{language:lang,ignoreIllegals:true}).value).slice(lead.length);return rows.length===lines.length?rows:null;}catch(e){return null;}}
function appendContext(parent,context,file){if(!context)return;const box=el("section","code-context");box.appendChild(el("div","context-head","対象コード（前後3行）"));if(context.error){box.appendChild(el("div","unavailable",context.error));parent.appendChild(box);return;}const pre=el("pre","code-lines");const colored=highlightedLines(context,file);context.lines.forEach((line,i)=>{const row=el("span","code-line"+(line.target?" target":""));row.appendChild(el("span","line-no",String(line.number)));const text=el("span","code-text");if(colored)text.innerHTML=colored[i];else text.textContent=line.text;row.appendChild(text);pre.appendChild(row);});box.appendChild(pre);parent.appendChild(box);}
function matchesFilter(s){return filterMode==="all"||(filterMode==="pending"&&s.decision===null)||filterMode===s.decision;}
function refresh(){const picked={fix:[],post:[],dismiss:[]};for(const item of DATA.items){const s=itemState(item.id);if(s.decision)picked[s.decision].push(item.id);const c=document.querySelector(`.card[data-id="${item.id}"]`);if(c){c.classList.toggle("completed",s.decision!==null);for(const [value] of DECISIONS)c.classList.toggle("decision-"+value,s.decision===value);c.hidden=!matchesFilter(s);const status=c.querySelector(".decision-status");status.textContent=s.decision?DECISION_LABEL[s.decision]:"";status.className="decision-status"+(s.decision?" badge decision-"+s.decision:"");for(const input of c.querySelectorAll(".decision input"))input.checked=input.value===s.decision;}}for(const group of document.querySelectorAll(".priority-group"))group.hidden=![...group.querySelectorAll(".card")].some(c=>!c.hidden);const done=picked.fix.length+picked.post.length+picked.dismiss.length;const counts={pending:DATA.items.length-done,fix:picked.fix.length,post:picked.post.length,dismiss:picked.dismiss.length,all:DATA.items.length};document.getElementById("progress").textContent=`未処理 ${counts.pending}/${DATA.items.length}（修正 ${counts.fix} / 投稿 ${counts.post} / 対応しない ${counts.dismiss}）`;const parts=[];if(picked.fix.length)parts.push(`修正: ${picked.fix.join(",")}`);if(picked.post.length)parts.push(`投稿: ${picked.post.join(",")}`);document.getElementById("params").textContent=parts.length?parts.join(" / "):"修正・投稿: (未選択)";for(const button of document.querySelectorAll("[data-filter]")){button.setAttribute("aria-pressed",String(button.dataset.filter===filterMode));button.textContent=`${FILTER_LABEL[button.dataset.filter]} (${counts[button.dataset.filter]})`;}document.getElementById("save-state").disabled=!CAN_SAVE_STATE||done!==DATA.items.length;}
async function saveToFilePicker(){fileHandle=await window.showSaveFilePicker({suggestedName:"state.json",types:[{description:"JSON",accept:{"application/json":[".json"]}}]});const writer=await fileHandle.createWritable();await writer.write(JSON.stringify(state,null,1));await writer.close();}
async function saveState(){if(!CAN_SAVE_STATE||!allItemsCompleted())return;syncStateItems();const status=document.getElementById("save-status");if(!CAN_SERVER_SAVE){const reopenHint="サーバー経由で開き直すと自動保存されます:\n  review-report "+(DATA.pr_number??"")+"\n\nそれでもこのファイルに保存しますか？";if(!window.confirm(reopenHint)){status.textContent="保存を取り消しました（review-report で開き直してください）";return;}}status.textContent="保存中…";try{if(CAN_SERVER_SAVE){const response=await fetch("/api/state",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(state)});if(!response.ok)throw new Error(await response.text());}else{await saveToFilePicker();}status.textContent="✅ 保存済み "+new Date().toLocaleTimeString();showToast("✅ state.json を保存しました");}catch(e){if(e&&e.name==="AbortError"){status.textContent="保存を取り消しました";return;}status.textContent="保存に失敗しました。";showToast("state.json の保存に失敗しました", "error");}}
function maybeOfferAutoSave(){const complete=allItemsCompleted();if(complete&&!wasComplete&&CAN_SERVER_SAVE&&!completionPrompted){completionPrompted=true;if(window.confirm("すべての指摘を判断しました。state.json に保存しますか？"))saveState();}if(!complete)completionPrompted=false;wasComplete=complete;}
function setTheme(theme){if(theme==="auto")delete document.documentElement.dataset.theme;else document.documentElement.dataset.theme=theme;for(const b of document.querySelectorAll("[data-theme]")){b.setAttribute("aria-pressed",String(b.dataset.theme===theme));}try{localStorage.setItem(THEME_KEY,theme);}catch(e){}}
function heartbeat(){if(CAN_SERVER_SAVE)fetch("/api/heartbeat",{method:"POST",keepalive:true}).catch(()=>{});}
document.getElementById("expand-all").addEventListener("click",()=>document.querySelectorAll(".card").forEach(c=>setOpen(c,true)));document.getElementById("collapse-all").addEventListener("click",()=>document.querySelectorAll(".card").forEach(c=>setOpen(c,false)));document.getElementById("save-state").addEventListener("click",saveState);const copyButton=document.getElementById("copy-run-dir");copyButton.disabled=!(typeof DATA.run_dir==="string"&&DATA.run_dir);copyButton.addEventListener("click",copyRunDir);document.querySelectorAll("[data-filter]").forEach(b=>b.addEventListener("click",()=>{filterMode=b.dataset.filter;refresh();}));document.querySelectorAll(".theme-picker button").forEach(b=>b.addEventListener("click",()=>setTheme(b.dataset.theme)));let savedTheme="auto";try{savedTheme=localStorage.getItem(THEME_KEY)||"auto";}catch(e){}setTheme(savedTheme);if(!CAN_SAVE_STATE){document.getElementById("save-status").textContent="進捗保存に非対応です。レビューコマンドから開き直してください。";}else if(!CAN_SERVER_SAVE){document.getElementById("save-status").textContent="サーバー経由ではありません（review-report "+(DATA.pr_number??"")+" で開き直すと自動保存されます）。";}document.addEventListener("DOMContentLoaded",build);heartbeat();if(CAN_SERVER_SAVE)window.setInterval(heartbeat,60000);
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
    # 表示しない先行行: 複数行文字列やコメントの途中から始まる抜粋でもハイライトの状態を正しく引き継ぐため
    lead = lines[max(0, first - 1 - LEAD_LINES):first - 1]
    return {"lead": lead, "lines": [
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
