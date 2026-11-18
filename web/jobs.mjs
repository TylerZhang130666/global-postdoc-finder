import {safeURL,today} from './core.mjs';

const TOPICS = {
  土壤:['soil'], 碳:['carbon'], 生态:['ecology','ecological'], 遥感:['remote sensing','hyperspectral','satellite'],
  生物信息:['bioinformatics','bioinformatic'], 机器学习:['machine learning'], 人工智能:['artificial intelligence','machine learning',' ai '],
  环境:['environment','environmental'], 气候:['climate'], 农业:['agriculture','agricultural'],
  生物:['biology','biological'], 化学:['chemistry','chemical'], 物理:['physics','physical'], 医学:['medicine','medical'],
  土壤碳:['soil carbon','soil organic carbon'],生态学:['ecology','ecological'],生物信息学:['bioinformatics'],
};
export function matchesJob(job,query){
  const haystack=[job.title,job.institution,job.department,job.country,job.location,job.summary].join(' ').toLowerCase();
  return query.trim().toLowerCase().split(/\s+/).filter(Boolean).every(token=>(TOPICS[token]??[token]).some(word=>haystack.includes(word)));
}
export function expired(job,now=new Date()){
  if(!job.deadline_at)return false;
  const value=job.deadline_at;
  if(/^\d{4}-\d{2}-\d{2}$/.test(value)){const local=[now.getFullYear(),String(now.getMonth()+1).padStart(2,'0'),String(now.getDate()).padStart(2,'0')].join('-');return value<local;}
  const stamp=Date.parse(value);return Number.isFinite(stamp)&&stamp<now.getTime();
}
export function searchJobs(jobs,{query='',country='all',source='all',sort='recent',hideExpired=true,now=new Date()}={}){
  const list=jobs.filter(j=>safeURL(j.url)&&matchesJob(j,query)&&(country==='all'||j.country===country)&&(source==='all'||j.source_id===source)&&(!hideExpired||!expired(j,now)));
  return list.sort((a,b)=>{
    if(sort==='deadline'){const date=j=>j.deadline_at&&Number.isFinite(Date.parse(j.deadline_at))?Date.parse(j.deadline_at):Infinity;return date(a)-date(b)||a.title.localeCompare(b.title);}
    const stamp=j=>Date.parse(j.posted_at)||0;return stamp(b)-stamp(a)||a.title.localeCompare(b.title);
  });
}
const el=(tag,value,cls)=>{const n=document.createElement(tag);if(value)n.textContent=value;if(cls)n.className=cls;return n;};
const $=id=>document.getElementById(id);
const date=value=>value&&Number.isFinite(Date.parse(value))?new Date(value).toLocaleDateString('zh-CN',{year:'numeric',month:'2-digit',day:'2-digit'}):'';
const external=(label,url,cls)=>{const a=el('a',label,cls);a.href=safeURL(url);a.target='_blank';a.rel='noopener noreferrer';return a;};

export async function initJobs({onSave,isSaved}){
  let data={jobs:[],sources:[]},filtered=[],page=1,selected=null;
  const PAGE_SIZE=15;
  function saveButton(job){const saved=isSaved(job.url),b=el('button',saved?'已收藏':'收藏',saved?'save-job saved':'save-job');b.type='button';b.setAttribute('aria-label',`${saved?'已收藏':'收藏'}：${job.title}`);b.disabled=saved;b.addEventListener('click',()=>{onSave(job);render();});return b;}
  function detail(job){
    const block=el('div','','detail-body');
    block.append(el('p',job.country+(job.location?' · '+job.location:''),'detail-country'),el('h2',job.title),el('p',job.institution,'detail-employer'));
    if(job.department)block.append(el('p',job.department,'muted'));
    const actions=el('div','','detail-actions');actions.append(external('查看原公告 ↗',job.url,'primary'),saveButton(job));block.append(actions);
    const facts=el('dl','','job-facts');
    for(const [label,value] of [['截止',date(job.deadline_at)||'未注明'],['发布',date(job.posted_at)||'未注明'],['来源',job.source_name],['收录',date(job.last_seen)]]){facts.append(el('dt',label),el('dd',value));}
    block.append(facts);
    if(job.summary){block.append(el('h3','岗位摘要'),el('p',job.summary,'job-excerpt'));}
    if(job.stale)block.append(el('p','该来源本轮未完整更新，以上是上次记录。','stale-note'));
    block.append(el('p','申请要求及是否仍在招聘，请以原公告为准。','detail-footnote'));
    return block;
  }
  function showDetail(job,openMobile=false){selected=job;$('job-detail').replaceChildren(detail(job));for(const card of document.querySelectorAll('.job-card'))card.classList.toggle('selected',card.dataset.id===job.id);if(openMobile&&matchMedia('(max-width: 760px)').matches){$('mobile-detail').replaceChildren(detail(job));$('job-dialog').showModal();}}
  function render(){
    filtered=searchJobs(data.jobs,{query:$('keywords').value,country:$('region').value,source:$('source-filter').value,sort:$('job-sort').value,hideExpired:$('hide-expired').checked});
    const pages=Math.max(1,Math.ceil(filtered.length/PAGE_SIZE));page=Math.min(page,pages);
    $('results-count').textContent=`${filtered.length} 个岗位`;$('job-results').replaceChildren();
    if(!filtered.length){const empty=el('div','','search-empty');empty.append(el('h2','没有找到岗位'),el('p','换个关键词，或试试英文。'));const reset=el('button','清除筛选','secondary');reset.addEventListener('click',()=>{$('search-form').reset();page=1;render();});empty.append(reset);$('job-results').append(empty);$('job-detail').replaceChildren();$('pagination').hidden=true;return;}
    for(const job of filtered.slice((page-1)*PAGE_SIZE,page*PAGE_SIZE)){
      const card=el('article','','job-card');card.dataset.id=job.id;
      const main=el('button','','job-select');main.type='button';main.append(el('p',job.institution,'job-employer'),el('h2',job.title),el('p',[job.country,job.department||job.location].filter(Boolean).join(' · '),'job-location'));
      main.addEventListener('click',()=>showDetail(job,true));card.append(main);
      const bottom=el('div','','job-card-bottom');bottom.append(el('span',job.deadline_at?'截止 '+date(job.deadline_at):'截止未注明'),saveButton(job));card.append(bottom);if(job.stale)card.append(el('small','上次记录','stale-note'));$('job-results').append(card);
    }
    const visible=filtered.slice((page-1)*PAGE_SIZE,page*PAGE_SIZE);showDetail(visible.find(j=>j.id===selected?.id)??visible[0]);
    if($('job-dialog').open)$('mobile-detail').replaceChildren(detail(selected));
    $('pagination').hidden=pages===1;$('page-label').textContent=`${page} / ${pages}`;$('prev-page').disabled=page===1;$('next-page').disabled=page===pages;
  }
  const resetPage=()=>{page=1;render();};
  $('search-form').addEventListener('submit',e=>{e.preventDefault();resetPage();});
  for(const id of ['region','source-filter','job-sort','hide-expired'])$(id).addEventListener('change',resetPage);
  let debounce;$('keywords').addEventListener('input',()=>{clearTimeout(debounce);debounce=setTimeout(resetPage,180);});
  for(const b of document.querySelectorAll('[data-keyword]'))b.addEventListener('click',()=>{$('keywords').value=b.dataset.keyword;resetPage();});
  $('prev-page').addEventListener('click',()=>{page--;render();$('results-count').scrollIntoView({block:'start',behavior:'smooth'});});
  $('next-page').addEventListener('click',()=>{page++;render();$('results-count').scrollIntoView({block:'start',behavior:'smooth'});});
  $('close-detail').addEventListener('click',()=>$('job-dialog').close());
  try{
    const response=await fetch('./data/jobs.json');if(!response.ok)throw new Error();data=await response.json();if(!Array.isArray(data.jobs)||!Array.isArray(data.sources))throw new Error();
    const countries=[...new Set(data.jobs.map(j=>j.country))].sort();for(const name of countries){const o=el('option',name);o.value=name;$('region').append(o);}
    for(const s of data.sources){const option=el('option',s.name);option.value=s.id;$('source-filter').append(option);}
    const observed=data.sources.map(s=>s.observed_at).filter(Boolean).sort().at(-1);$('index-date').textContent=observed?'收录于 '+date(observed):'暂无新收录';
    $('coverage-list').replaceChildren();for(const s of data.sources){const count=data.jobs.filter(j=>j.source_id===s.id).length;const row=el('p','','coverage-row');row.append(external(s.name,s.url),el('span',`${count} 条 · ${s.status==='ok'?'已更新':s.status==='partial'?'部分更新':'上次记录'}`));$('coverage-list').append(row);}
    $('index-total')?.replaceChildren(document.createTextNode(`${data.jobs.length} 条记录 · ${data.sources.length} 个来源`));
    render();
  }catch{$('results-count').textContent='暂时无法加载';$('job-results').replaceChildren(el('p','刷新页面重试。你的收藏不受影响。','search-empty'));}
  return {refresh:render};
}
