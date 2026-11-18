import {TYPES,PROGRESS,CRITERIA,RESULTS,ACCESS,today,safeURL,normalizeRecord,parseImport,mergeRecords,toCSV,filterSources,searchURL,matchSource,deadlineLabel} from './core.mjs';
const $=id=>document.getElementById(id), KEY='global-postdoc-finder:workbench:v1';
let records=[],sources=[],editing=null,editingSnapshot=null,rawStorage=null,storageBlocked=false,timer;
const text=(tag,value,cls)=>{const e=document.createElement(tag);e.textContent=value;if(cls)e.className=cls;return e;};
function anchor(label,url,cls){const a=text('a',label,cls);a.href=safeURL(url);a.target='_blank';a.rel='noopener noreferrer';return a;}
function toast(message){$('toast').textContent=message;$('toast').hidden=false;clearTimeout(timer);timer=setTimeout(()=>$('toast').hidden=true,5500);}
function storageError(message){$('storage-problem').hidden=false;$('storage-message').textContent=message;}
try{rawStorage=localStorage.getItem(KEY);if(rawStorage){const data=JSON.parse(rawStorage);if(data.schema_version!=='postdoc-workbench/1')throw new Error('未知备份格式');records=parseImport(rawStorage).map((r,i)=>({...r,imported:data.records[i].imported===true}));}}
catch{storageBlocked=true;storageError('浏览器无法读取已保存的数据。为保护原文件，暂不覆盖；请先下载原始数据备份，或尝试恢复浏览器的存储权限。');}
function persist(next){
  if(storageBlocked){toast('本机存储读取异常，请先下载原始数据备份。');return false;}
  try{localStorage.setItem(KEY,JSON.stringify({schema_version:'postdoc-workbench/1',records:next}));records=next;return true;}
  catch{storageError('本机存储不可用或空间不足，本次修改尚未保存。可先导出已有清单备份，再检查浏览器存储权限。');toast('保存失败，表单内容已保留。');return false;}
}
function tab(name,focus=false){for(const b of document.querySelectorAll('[data-tab]')){const active=b.dataset.tab===name;b.setAttribute('aria-selected',String(active));b.tabIndex=active?0:-1;$(b.getAttribute('aria-controls')).hidden=!active;if(active&&focus)b.focus();}if(name==='list')renderRecords();}
document.querySelector('.tabs').setAttribute('role','tablist');
for(const b of document.querySelectorAll('[data-tab]')){b.addEventListener('click',()=>tab(b.dataset.tab));b.addEventListener('keydown',e=>{const tabs=[...document.querySelectorAll('[data-tab]')];let i=tabs.indexOf(b);if(e.key==='ArrowRight')i=(i+1)%tabs.length;else if(e.key==='ArrowLeft')i=(i+tabs.length-1)%tabs.length;else if(e.key==='Home')i=0;else if(e.key==='End')i=tabs.length-1;else return;e.preventDefault();tab(tabs[i].dataset.tab,true);});}
for(const [key,label] of Object.entries(CRITERIA)){const l=text('label',label),select=document.createElement('select');select.id='check-'+key;select.setAttribute('aria-label',label);for(const [v,t] of Object.entries(RESULTS)){const o=text('option',t);o.value=v;select.append(o);}l.append(select);$('check-fields').append(l);}
function renderSources(){
  const region=$('region').value,type=$('route').value,keywords=$('keywords').value;
  const list=filterSources(sources,region,type);$('source-list').replaceChildren();$('source-count').textContent=`${list.length} 个来源`;
  $('source-caption').textContent=region==='all'?'覆盖不同地区的精选入口，按实际公告确认工作地点。':'同时保留全球性入口，请在来源网站继续按地点筛选。';
  if(!list.length){$('source-list').append(text('p','这个组合暂未收录入口，可换一个地区或查看全部来源。','muted'));return;}
  list.forEach((s,i)=>{const row=text('article','','source-card'),body=document.createElement('div');body.append(text('h3',s.name),text('p',`${s.opportunity_types.map(t=>TYPES[t]).join(' / ')} · ${s.regions.join('；')}`,'source-meta'),text('p',s.web_note,'muted'));const links=text('div','','source-links');links.append(anchor('打开官方入口 ↗',s.url));if(keywords.trim())links.append(anchor('关键词检索 ↗',searchURL(s,keywords)));body.append(links);const detail=document.createElement('details');detail.className='help';detail.style.marginTop='14px';detail.append(text('summary','来源说明'),text('p',s.search_method),text('p',`目录记录 ${s.checked_on}：${s.access_note}`));body.append(detail);row.append(body,text('span',String(i+1).padStart(2,'0'),'source-index'));$('source-list').append(row);});
}
$('search-form').addEventListener('submit',e=>{e.preventDefault();renderSources();toast('已更新入口；请进入来源网站查看实际机会。');});
for(const id of ['region','route'])$(id).addEventListener('change',renderSources);
function inspectURL(){const url=safeURL($('source-url')?.value??'');return url;}
const urlInput=$('source-url'),inspect=$('inspect-url'),urlResult=$('url-feedback');
inspect.addEventListener('click',()=>{const url=inspectURL();if(!url){urlResult.textContent='请输入完整、有效的 http:// 或 https:// 链接。';return;}const s=matchSource(url,sources);urlResult.replaceChildren(text('span',s?`域名在来源目录中（${new URL(url).hostname}）。这不证明该页面正在招聘，请打开原公告逐项核实。 `:'网址格式有效，尚未识别为目录中的来源；请确认机构官网和具体公告。 '),anchor('打开链接 ↗',url));});
function resetForm(){editing=null;editingSnapshot=null;$('opportunity-form').reset();$('editing-label').textContent='保存后可在“我的清单”里继续补充。';urlResult.textContent='仅识别网址所属来源；不会自动读取公告或判断是否开放。';}
$('reset-form').addEventListener('click',()=>{if(editing&&!confirm('放弃这次尚未保存的编辑？'))return;resetForm();});
$('add-record').addEventListener('click',()=>{if(editing&&!confirm('当前有正在编辑的机会，是否改为添加新机会？'))return;resetForm();tab('verify');urlInput.focus();});
const fields={title:'record-title',institution:'institution',country:'country',source_url:'source-url',opportunity_type:'record-type',progress:'progress',deadline:'deadline',date_checked:'checked-on',application_access:'availability',next_action:'next-action',evidence:'evidence'};
$('checked-on').max=today();
$('opportunity-form').addEventListener('submit',e=>{e.preventDefault();try{const old=records.find(r=>r.id===editing);if(editing&&!old)throw new Error('这条记录已在其他标签页删除。请清空表单后重新添加。');if(editing&&JSON.stringify(old)!==editingSnapshot&&!confirm('这条记录已在其他标签页修改。要用当前表单覆盖吗？'))return;let record=Object.fromEntries(Object.entries(fields).map(([k,id])=>[k,$(id).value]));record={...old,...record,id:editing??crypto.randomUUID(),checks:Object.fromEntries(Object.keys(CRITERIA).map(k=>[k,$('check-'+k).value]))};record=normalizeRecord(record);if(!editing&&records.length>=1000)throw new Error('清单最多保存 1000 条，请先导出整理');if(!editing&&records.some(r=>r.source_url===record.source_url&&r.title===record.title)&&!confirm('清单中已有相同标题和链接，仍要另存一条吗？'))return;const next=editing?records.map(r=>r.id===editing?record:r):[record,...records];if(persist(next)){resetForm();renderRecords();tab('list');toast('已保存到本机清单。');}}catch(error){toast(error.message);}});
function editRecord(r){editing=r.id;editingSnapshot=JSON.stringify(r);for(const [key,id] of Object.entries(fields))$(id).value=r[key]??'';for(const key of Object.keys(CRITERIA))$('check-'+key).value=r.checks[key];$('editing-label').textContent='正在编辑：'+r.title;tab('verify');$('record-title').focus();}
function renderRecords(){
  $('list-count').textContent=records.length;
  $('stats').replaceChildren();const statistics=[[records.length,'全部机会'],[records.filter(r=>r.progress==='checking').length,'正在核实'],[records.filter(r=>r.progress==='preparing').length,'准备材料'],[records.filter(r=>r.progress==='applied').length,'已提交申请']];for(const [n,label] of statistics){const s=text('div','','stat');s.append(text('b',n),text('span',label));$('stats').append(s);}
  const query=$('list-query').value.trim().toLocaleLowerCase(),typeFilter=$('list-type')?.value??'all',progress=$('list-progress')?.value??'all';
  const selected=records.filter(r=>(typeFilter==='all'||r.opportunity_type===typeFilter)&&(progress==='all'||r.progress===progress)&&[r.title,r.institution,r.country,r.next_action,r.evidence].join(' ').toLocaleLowerCase().includes(query));
  $('records').replaceChildren();$('list-caption').textContent=`显示 ${selected.length} / ${records.length} 条。日期提示按当前浏览器日期 ${today()} 计算，不会据此自动标记关闭。`;
  if(!selected.length){const empty=text('div','','empty-state');empty.style.cssText='text-align:center;padding:48px 20px;background:var(--soft)';empty.append(text('h3',records.length?'暂时没有符合的机会':'清单还空着，慢慢来。'),text('p',records.length?'换个关键词，或调整类型与进度筛选。':'从一个官方链接开始，先记下来，再逐项核实。','muted'));if(!records.length){const b=text('button','添加第一个机会 →','secondary');b.addEventListener('click',()=>$('add-record').click());empty.append(b);}$('records').append(empty);}
  for(const r of selected){const card=text('article','','record-card'),top=text('div','','record-top'),heading=document.createElement('div');heading.append(text('h3',r.title),text('p',[r.institution||'机构未记录',r.country||'地点未记录',TYPES[r.opportunity_type]].join(' · '),'record-meta'));top.append(heading,text('span',PROGRESS[r.progress],'badge'));card.append(top);const facts=text('div','','record-facts');facts.append(text('span',ACCESS[r.application_access]),text('span',deadlineLabel(r.deadline)),text('span','人工核验：'+(r.date_checked||'未记录')));card.append(facts);if(r.next_action)card.append(text('p','下一步：'+r.next_action,'record-next'));const actions=text('div','','record-actions');actions.append(anchor('查看原始链接 ↗',r.source_url));const edit=text('button','编辑记录');edit.addEventListener('click',()=>editRecord(r));actions.append(edit);const del=text('button','删除','delete');del.addEventListener('click',()=>{if(confirm(`删除「${r.title}」？此操作只影响本机清单。`)&&persist(records.filter(x=>x.id!==r.id))){renderRecords();toast('已从本机清单删除。');}});actions.append(del);card.append(actions);const details=document.createElement('details');details.append(text('summary','查看核验记录'+(r.imported?' · 导入后未重新联网核实':'')));const checks=text('div','','check-summary');for(const [key,label] of Object.entries(CRITERIA))checks.append(text('span',`${label}：${RESULTS[r.checks[key]]}`));details.append(checks,text('p',r.evidence||'尚未填写证据与备注。','evidence-text'));if(r.skill_record)details.append(text('p','导入时的完整 Skill 记录会随 JSON 备份保留；网页不重新计算分数或行动优先级。'));card.append(details);$('records').append(card);}
  for(const id of ['export-json','export-csv'])$(id).disabled=!records.length;
}
for(const id of ['list-type','list-progress'])$(id).addEventListener('change',renderRecords);
$('list-query').addEventListener('input',renderRecords);
function download(content,type,name){const url=URL.createObjectURL(new Blob([content],{type})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),2000);}
$('export-json').addEventListener('click',()=>download(JSON.stringify({schema_version:'postdoc-workbench/1',exported_on:today(),records},null,2),'application/json',`postdoc-list-${today()}.json`));
$('export-csv').addEventListener('click',()=>download(toCSV(records),'text/csv;charset=utf-8',`postdoc-list-${today()}.csv`));
$('recover-storage').addEventListener('click',()=>download(rawStorage??'','text/plain',`postdoc-raw-backup-${today()}.txt`));
$('import-button').addEventListener('click',()=>$('import-file').click());
$('import-file').addEventListener('change',async e=>{const file=e.target.files[0];if(!file)return;try{if(file.size>5*1024*1024)throw new Error('请使用小于 5 MB 的文件');const incoming=parseImport(await file.text());const merged=mergeRecords(records,incoming);if(persist(merged.records)){renderRecords();toast(`导入 ${merged.added} 条，跳过 ${merged.skipped} 条相同记录；未重新联网核实。`);}}catch(error){toast('导入失败，原清单未改变。'+error.message);}finally{e.target.value='';}});
// A second tab must not silently overwrite a newer saved list.
window.addEventListener('storage',e=>{if(e.key!==KEY)return;try{records=e.newValue?parseImport(e.newValue):[];renderRecords();toast('已同步本浏览器另一个标签页的清单；当前表单未保存的内容已保留。');}catch{storageBlocked=true;rawStorage=e.newValue;storageError('另一个标签页写入的数据无法读取。请先下载原始数据备份。');}});
renderRecords();tab('search');
try{const response=await fetch('./data/sources.json');if(!response.ok)throw new Error('来源目录加载失败');const data=await response.json();sources=data.sources;renderSources();}
catch{$('source-count').textContent='';$('source-list').replaceChildren(text('p','来源目录暂时加载失败。请刷新页面重试，或从页脚打开 GitHub 目录；本机清单仍可使用。','muted'));}
