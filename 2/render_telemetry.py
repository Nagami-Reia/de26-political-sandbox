#!/usr/bin/env python3
"""Render a self-contained first-quadrant telemetry chart from telemetry JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


TEMPLATE = r'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>决策支持变化遥测</title>
<style>
:root{color-scheme:light dark;--bg:light-dark(#fbfbfc,#111318);--fg:light-dark(#172033,#edf1f7);--muted:light-dark(#687083,#9aa5b7);--grid:light-dark(#d9dee8,#343b49);--plot:light-dark(#fff,#171a21);--s1:#3974d8;--s2:#d26a32;--s3:#2b936f;--s4:#8d61c5;--s5:#be4666;--s6:#8a761c}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}main{max-width:1100px;margin:auto;padding:20px}h1{font-size:20px;font-weight:600;margin:0 0 4px}.sub{color:var(--muted);margin:0 0 16px}.controls{display:flex;gap:14px;flex-wrap:wrap;align-items:end;margin-bottom:12px}.control{display:grid;gap:4px}.control label{color:var(--muted);font-size:12px}select{font:inherit;padding:6px 28px 6px 8px;border:1px solid var(--grid);border-radius:6px;background:var(--plot);color:var(--fg)}#legend{display:flex;gap:6px 14px;flex-wrap:wrap;margin:8px 0 10px}#legend button{border:0;background:transparent;color:var(--fg);padding:5px 0;font:inherit;cursor:pointer}#legend button[aria-pressed="false"]{opacity:.38}.swatch{display:inline-block;width:18px;height:3px;margin-right:6px;vertical-align:middle}.chart-wrap{position:relative;background:var(--plot);border:1px solid var(--grid);min-height:430px}svg{display:block;width:100%;height:430px}.axis,.grid{stroke:var(--grid);stroke-width:1}.grid{opacity:.65}.axis-text{fill:var(--muted);font-size:12px}.axis-title{fill:var(--fg);font-size:12px}.event-line{stroke:var(--grid);stroke-width:1;opacity:.45}.series{fill:none;stroke-width:2.3}.model{stroke-dasharray:7 5}.point{stroke-width:2}.tooltip{position:absolute;pointer-events:none;background:var(--fg);color:var(--bg);padding:8px 10px;border-radius:6px;max-width:330px;display:none;font-size:12px;z-index:4}.note{color:var(--muted);margin-top:10px;font-size:12px}.empty{position:absolute;inset:0;display:grid;place-items:center;color:var(--muted);pointer-events:none}
@media(max-width:560px){main{padding:12px}svg{height:390px}.chart-wrap{min-height:390px}}
</style>
</head>
<body><main>
<h1>决策后支持变化</h1>
<p class="sub">每次事件后记录一次；观测值、潜在模型状态与取整后的模型即时估计保持可区分。横轴为事件/决策步，纵轴固定 0–100。</p>
<div class="controls">
  <div class="control"><label for="unit">量纲</label><select id="unit"><option value="percent">百分比 / 模型即时估计</option><option value="index_0_100">模型支持指数</option></select></div>
  <div class="control"><label for="scope">范围</label><select id="scope"><option value="all">全部范围</option></select></div>
</div>
<div id="legend" aria-label="数据序列"></div>
<div class="chart-wrap"><svg id="chart" role="img" aria-label="第一象限支持变化折线图"></svg><div id="tooltip" class="tooltip" role="tooltip"></div><div id="empty" class="empty" hidden>当前量纲与范围暂无数据</div></div>
<p class="note">实线/实心点＝有来源的真实观测；虚线/空心点＝模型潜在状态或模型即时估计。模型即时估计不是每一步都真实实施一次民调。相邻事件与变化只表示模型中的事件结算顺序。</p>
</main>
<script>
const data=__DATA__;
const colors=['var(--s1)','var(--s2)','var(--s3)','var(--s4)','var(--s5)','var(--s6)'];
const labels={public_job_satisfaction:'个人工作满意度',vote_intention:'政党投票意向',vote_intention_latent:'政党支持潜在状态',vote_intention_nowcast:'政党支持模型即时估计',government_satisfaction:'政府满意度',election_vote_share:'选举得票率',faction_ballot_support:'党团表决支持',direct_mayor_preference:'直接市长偏好',good_governing_mayor:'适任市长评价',party_elite_support:'党内精英支持指数',member_organization_support:'党员/组织支持指数',public_acceptance:'公众接受指数',electoral_momentum:'选举动量指数'};
const state={unit:'percent',scope:'all',hidden:new Set()};
const svg=document.getElementById('chart'), legend=document.getElementById('legend'), tip=document.getElementById('tooltip'), empty=document.getElementById('empty');
const scope=document.getElementById('scope'), unit=document.getElementById('unit');
const scopes=[...new Set(data.support_points.map(d=>d.scope))].sort();
for(const s of scopes){const o=document.createElement('option');o.value=s;o.textContent=s;scope.appendChild(o)}
unit.addEventListener('change',()=>{state.unit=unit.value;state.hidden.clear();draw()});scope.addEventListener('change',()=>{state.scope=scope.value;state.hidden.clear();draw()});
function esc(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function seriesName(d){return `${d.subject} · ${labels[d.measure]||d.measure} · ${d.scope}`}
function key(d){return d.series_key}
function el(name,attrs={}){const n=document.createElementNS('http://www.w3.org/2000/svg',name);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,v);return n}
function draw(){
  const width=svg.clientWidth||760,height=svg.clientHeight||430,m={top:18,right:20,bottom:58,left:68};
  svg.setAttribute('viewBox',`0 0 ${width} ${height}`);svg.replaceChildren();
  const points=data.support_points.filter(d=>d.unit===state.unit&&(state.scope==='all'||d.scope===state.scope));
  const grouped=new Map();for(const d of points){if(!grouped.has(key(d)))grouped.set(key(d),[]);grouped.get(key(d)).push(d)}
  const groups=[...grouped.entries()].map(([k,v])=>[k,v.sort((a,b)=>a.step-b.step)]);
  empty.hidden=groups.length>0;legend.replaceChildren();
  groups.forEach(([k,vals],i)=>{const b=document.createElement('button');b.type='button';b.setAttribute('aria-pressed',String(!state.hidden.has(k)));const sw=document.createElement('span');sw.className='swatch';sw.style.background=colors[i%colors.length];b.append(sw,document.createTextNode(seriesName(vals[0])));b.onclick=()=>{state.hidden.has(k)?state.hidden.delete(k):state.hidden.add(k);draw()};legend.appendChild(b)});
  const maxStep=Math.max(1,...data.events.map(d=>d.step));const x=v=>m.left+(v/maxStep)*(width-m.left-m.right);const y=v=>height-m.bottom-(v/100)*(height-m.top-m.bottom);
  for(let v=0;v<=100;v+=20){svg.appendChild(el('line',{x1:m.left,x2:width-m.right,y1:y(v),y2:y(v),class:'grid'}));const t=el('text',{x:m.left-10,y:y(v)+4,'text-anchor':'end',class:'axis-text'});t.textContent=v;svg.appendChild(t)}
  const tickEvery=Math.max(1,Math.ceil(maxStep/(width<500?4:8)));for(let s=0;s<=maxStep;s+=tickEvery){svg.appendChild(el('line',{x1:x(s),x2:x(s),y1:height-m.bottom,y2:height-m.bottom+5,class:'axis'}));const t=el('text',{x:x(s),y:height-m.bottom+21,'text-anchor':'middle',class:'axis-text'});t.textContent=s;svg.appendChild(t)}
  svg.appendChild(el('line',{x1:m.left,x2:m.left,y1:m.top,y2:height-m.bottom,class:'axis'}));svg.appendChild(el('line',{x1:m.left,x2:width-m.right,y1:height-m.bottom,y2:height-m.bottom,class:'axis'}));
  const xt=el('text',{x:(m.left+width-m.right)/2,y:height-13,'text-anchor':'middle',class:'axis-title','data-axis':'x'});xt.textContent='事件 / 决策步';svg.appendChild(xt);const yt=el('text',{x:16,y:(m.top+height-m.bottom)/2,transform:`rotate(-90 16 ${(m.top+height-m.bottom)/2})`,'text-anchor':'middle',class:'axis-title','data-axis':'y'});yt.textContent=state.unit==='percent'?'支持 / 满意 / 得票（%）':'模型支持指数（0–100）';svg.appendChild(yt);
  groups.forEach(([k,vals],i)=>{if(state.hidden.has(k))return;const color=colors[i%colors.length],path=el('path',{class:`series ${vals[0].evidence_status==='MODEL_ESTIMATE'?'model':''}`,stroke:color,d:vals.map((d,j)=>`${j?'L':'M'}${x(d.step)},${y(d.value)}`).join(' ')});svg.appendChild(path);for(const d of vals){const c=el('circle',{cx:x(d.step),cy:y(d.value),r:4.5,class:'point',stroke:color,fill:d.evidence_status==='OBSERVED'?color:'var(--plot)'});c.style.cursor='pointer';c.addEventListener('pointerenter',ev=>showTip(ev,d));c.addEventListener('pointermove',ev=>positionTip(ev));c.addEventListener('pointerleave',hideTip);svg.appendChild(c)}})
}
function showTip(ev,d){const event=data.events.find(e=>e.step===d.step);tip.innerHTML=`<strong>${esc(seriesName(d))}</strong><br>${d.value}${d.unit==='percent'?'%':' / 100'} · 第 ${d.step} 步<br>${esc(event?.action||'')}<br>${d.source_id?`来源 ${esc(d.source_id)}`:'模型估计'}`;tip.style.display='block';positionTip(ev)}
function positionTip(ev){const box=svg.parentElement.getBoundingClientRect();tip.style.left=Math.min(box.width-tip.offsetWidth-8,Math.max(8,ev.clientX-box.left+12))+'px';tip.style.top=Math.max(8,ev.clientY-box.top-tip.offsetHeight-12)+'px'}function hideTip(){tip.style.display='none'}
new ResizeObserver(draw).observe(svg);draw();
</script></body></html>'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    html = TEMPLATE.replace("__DATA__", json.dumps(payload, ensure_ascii=False).replace("</", "<\\/"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding="utf-8")


def render_payload(payload: dict, output: Path) -> None:
    html = TEMPLATE.replace("__DATA__", json.dumps(payload, ensure_ascii=False).replace("</", "<\\/"))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    main()
