import {safeURL,today} from './core.mjs';
import {profileMatch} from './profile.mjs?v=9';

const TOPICS = {
  土壤:['soil'], 碳:['carbon'], 生态:['ecology','ecological'], 遥感:['remote sensing','hyperspectral','satellite'],
  生物信息:['bioinformatics','bioinformatic'], 机器学习:['machine learning'], 人工智能:['artificial intelligence','machine learning',' ai '],
  环境:['environment','environmental'], 气候:['climate'], 农业:['agriculture','agricultural'],
  生物:['biology','biological'], 化学:['chemistry','chemical'], 物理:['physics','physical'], 医学:['medicine','medical'],
  土壤碳:['soil carbon','soil organic carbon'],生态学:['ecology','ecological'],生物信息学:['bioinformatics'],
};
export function matchesJob(job,query,includeDetails=true){
  const detail=includeDetails?[...(job.search_terms??[]),...(job.search_phrases??[])]:[];
  const haystack=[job.title,job.institution,job.department,job.country,job.location,job.summary,...detail].join(' ').toLowerCase();
  const contains=word=>/^[a-z]{1,3}$/.test(word)?new RegExp(`(^|[^a-z0-9])${word}([^a-z0-9]|$)`,'i').test(haystack):haystack.includes(word);
  return query.trim().toLowerCase().split(/\s+/).filter(Boolean).every(token=>(TOPICS[token]??[token]).some(contains));
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
const timestamp=value=>value&&Number.isFinite(Date.parse(value))?new Date(value).toLocaleString('zh-CN',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',timeZoneName:'short'}):'未记录';
const external=(label,url,cls)=>{const a=el('a',label,cls);a.href=safeURL(url);a.target='_blank';a.rel='noopener noreferrer';return a;};

export async function initJobs({onSave,isSaved,getProfile=()=>null,onData=()=>{}}){
  let data={jobs:[],sources:[]},filtered=[],page=1,selected=null;
  const PAGE_SIZE=15;
  function saveButton(job){const saved=isSaved(job.url),b=el('button',saved?'已收藏':'收藏',saved?'save-job saved':'save-job');b.type='button';b.setAttribute('aria-label',`${saved?'已收藏':'收藏'}：${job.title}`);b.disabled=saved;b.addEventListener('click',()=>{onSave(job);render();});return b;}
  function detail(job){
    const block=el('div','','detail-body');
    block.append(el('p',job.country+(job.location?' · '+job.location:''),'detail-country'),el('h2',job.title),el('p',job.institution,'detail-employer'));
    if(job.department)block.append(el('p',job.department,'muted'));
    const actions=el('div','','detail-actions');actions.append(external('查看原公告 ↗',job.url,'primary'),saveButton(job));block.append(actions);
    const facts=el('dl','','job-facts');
    for(const [label,value] of [['截止',date(job.deadline_at)||'未注明'],['发布',date(job.posted_at)||'未注明'],['导师',job.notice_details?.faculty],['来源',job.source_name],['收录',date(job.last_seen)]]){if(value)facts.append(el('dt',label),el('dd',value));}
    block.append(facts);
    const info=job.notice_details??{};
    if(info.faculty)block.append(el('p','导师：'+info.faculty,'muted'));
    if(info.excerpt||job.summary){block.append(el('h3','研究内容 · 公告摘录'),el('p',info.excerpt||job.summary,'job-excerpt'));}
    for(const [label,value] of [['要求摘录',info.requirements],['申请材料 / 方式',info.application]]){
      if(value?.length){block.append(el('h3',label));const list=el('ul','','notice-extracts');for(const line of value)list.append(el('li',line));block.append(list);}
    }
    for(const [label,value] of [['薪酬原文',info.salary],['合同相关原文',info.contract]])if(value)block.append(el('h3',label),el('p',value,'job-excerpt'));
    if(getProfile()){const match=profileMatch(job,getProfile());if(match.matched.length)block.append(el('p','与你的共同词：'+match.matched.join('、'),'match-reason'));}
    if(!info.salary||!info.contract)block.append(el('p',[!info.salary?'薪酬未提取':null,!info.contract?'合同期限未提取':null].filter(Boolean).join(' · '),'muted'));
    if(job.detail_status==='indexed')block.append(el('p','正文已索引 · '+date(job.detail_checked_at)+(job.detail_refresh_failed?' · 本轮更新失败，保留上次索引':''),'muted'));
    else block.append(el('p',job.detail_status==='unavailable'?'正文暂不可读，仅检索标题和摘要':'正文待索引，当前检索标题和摘要','muted'));
    if(job.stale)block.append(el('p','该来源本轮未完整更新，以上是上次记录。','stale-note'));
    block.append(el('p','申请要求及是否仍在招聘，请以原公告为准。','detail-footnote'));
    return block;
  }
  function showDetail(job,openMobile=false){selected=job;$('job-detail').replaceChildren(detail(job));for(const card of document.querySelectorAll('.job-card'))card.classList.toggle('selected',card.dataset.id===job.id);if(openMobile&&matchMedia('(max-width: 760px)').matches){$('mobile-detail').replaceChildren(detail(job));$('job-dialog').showModal();}}
  function render(){
    const profile=getProfile();
    $('profile-sort-option').disabled=!profile;
    if(!profile&&$('job-sort').value==='profile')$('job-sort').value='recent';
    filtered=searchJobs(data.jobs,{query:$('keywords').value,country:$('region').value,source:$('source-filter').value,sort:$('job-sort').value,hideExpired:$('hide-expired').checked});
    if($('job-sort').value==='profile'&&profile)filtered=filtered.map(job=>({job,match:profileMatch(job,profile)})).filter(x=>x.match.regionOK&&x.match.rank>0).sort((a,b)=>b.match.rank-a.match.rank).map(x=>x.job);
    const pages=Math.max(1,Math.ceil(filtered.length/PAGE_SIZE));page=Math.min(page,pages);
    $('results-count').textContent=`${filtered.length} 个岗位`;$('job-results').replaceChildren();
    $('job-detail').hidden=!filtered.length;
    document.querySelector('.jobs-layout').classList.toggle('no-results',!filtered.length);
    if(!filtered.length){
      const empty=el('div','','search-empty'),country=$('region').value,source=$('source-filter').value;
      const base=searchJobs(data.jobs,{country,source,hideExpired:$('hide-expired').checked});
      const sourceCount=new Set(base.map(j=>j.source_id)).size;
      empty.append(el('h2','当前收录中暂无匹配'),el('p',`${country==='all'?'当前范围':country}收录 ${base.length} 个岗位，来自 ${sourceCount} 个来源。`),el('p','只检索已收录内容，不代表没有相关岗位。','muted'));
      const buttons=el('div','','empty-actions');
      if($('keywords').value.trim()){const clear=el('button','清除关键词','secondary');clear.addEventListener('click',()=>{$('keywords').value='';page=1;render();});buttons.append(clear);}
      if(country!=='all'){
        const elsewhere=searchJobs(data.jobs,{query:$('keywords').value,source,hideExpired:$('hide-expired').checked}).filter(j=>j.country!==country).length;
        if(elsewhere){const other=el('button',`查看其他地区（${elsewhere}）`,'secondary');other.addEventListener('click',()=>{$('region').value='all';page=1;render();});buttons.append(other);}
      }
      empty.append(buttons);$('job-results').append(empty);$('job-detail').replaceChildren();$('pagination').hidden=true;return;
    }
    for(const job of filtered.slice((page-1)*PAGE_SIZE,page*PAGE_SIZE)){
      const card=el('article','','job-card');card.dataset.id=job.id;
      const main=el('button','','job-select');main.type='button';main.append(el('p',job.institution,'job-employer'),el('h2',job.title),el('p',[job.country,job.department||job.location].filter(Boolean).join(' · '),'job-location'));
      main.addEventListener('click',()=>showDetail(job,true));card.append(main);
      if($('keywords').value.trim()&&!matchesJob(job,$('keywords').value,false))card.append(el('p','匹配公告正文','body-match'));
      if($('job-sort').value==='profile'&&profile)card.append(el('p','共同词：'+profileMatch(job,profile).matched.join('、'),'match-reason'));
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
  function options(id,items,label){const selected=$(id).value;$(id).replaceChildren();for(const [value,title] of [['all',label],...items]){const o=el('option',title);o.value=value;$(id).append(o);}if(selected!=='all'&&!items.some(([value])=>value===selected)){const o=el('option',selected);o.value=selected;$(id).append(o);}$(id).value=selected;}
  async function load(manual=false){
    const button=$('refresh-jobs');if(button.disabled)return;button.disabled=true;button.textContent='读取中…';
    try{
      const response=await fetch('./data/jobs.json?refresh='+Date.now(),{cache:'no-store'});if(!response.ok)throw new Error();
      const next=await response.json();if(!Array.isArray(next.jobs)||!Array.isArray(next.sources)||next.schema_version!=='postdoc-jobs/1')throw new Error();
      const changed=next.generated_at!==data.generated_at;data=next;onData(data);
      options('region',[...new Set(data.jobs.map(j=>j.country))].sort().map(v=>[v,v]),'全部地区');
      options('source-filter',data.sources.map(s=>[s.id,s.name]),'全部来源');
      const observed=data.jobs.map(j=>j.last_seen).filter(Boolean).sort().at(-1);
      $('index-date').textContent='最近收录 '+timestamp(observed);
      $('coverage-list').replaceChildren();for(const s of data.sources){
        const sourceJobs=data.jobs.filter(j=>j.source_id===s.id),row=el('div','','coverage-source');
        const heading=el('p','','coverage-row');heading.append(external(s.name,s.url),el('span',`${sourceJobs.length} 条 · ${s.status==='ok'?'已更新':s.status==='partial'?'部分更新':'未更新'}`));
        const seen=sourceJobs.map(j=>j.last_seen).sort().at(-1);row.append(heading,el('small',`${timestamp(seen)} · ${s.pages_read??0} 页 · ${s.scope??''}${s.coverage==='page_limit'?'（达到本版分页上限）':''}`));row.append(el('small',`正文 ${s.body_indexed??sourceJobs.filter(j=>j.detail_status==='indexed').length}/${sourceJobs.length} · 待读取 ${s.body_pending??0} · 暂不可读 ${s.body_unavailable??0}`));$('coverage-list').append(row);
      }
      $('index-total').textContent=`${data.jobs.length} 条记录 · ${data.sources.length} 个来源 · 正文 ${data.jobs.filter(j=>j.detail_status==='indexed').length}/${data.jobs.length}`;
      $('refresh-status').textContent=manual?(changed?'岗位库已更新':'已检查，暂无新版本'):'';render();
    }catch{
      $('refresh-status').textContent='暂时无法更新，保留上次记录';
      if(!data.jobs.length){$('results-count').textContent='暂时无法加载';$('job-results').replaceChildren(el('p','点击“刷新”重试。','search-empty'));}
    }finally{button.disabled=false;button.textContent='刷新';}
  }
  $('refresh-jobs').addEventListener('click',()=>load(true));
  await load();
  return {refresh:render};
}
