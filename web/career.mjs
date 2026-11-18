import {safeURL,today} from './core.mjs';
import {inferProfile,normalizeProfile,profileMatch,linkedinSearch} from './profile.mjs?v=7';
import {expired} from './jobs.mjs?v=7';
import {readCV} from './cv-reader.mjs?v=7';

const KEY='global-postdoc-finder:profile:v1';
const $=id=>document.getElementById(id);
const el=(tag,text='',cls='')=>{const n=document.createElement(tag);n.textContent=text;if(cls)n.className=cls;return n;};
const link=(label,url)=>{const a=el('a',label);a.href=safeURL(url);a.target='_blank';a.rel='noopener noreferrer';return a;};

export function initCareer({onSaveHost,isSaved,onProfile,goToJobs}){
  let profile=null,hosts=[],jobs=[],hostPage=1,storageOK=true;
  try{const saved=localStorage.getItem(KEY);if(saved)profile=normalizeProfile(JSON.parse(saved));}
  catch{storageOK=false;$('profile-message').textContent='无法读取已存画像，请导出当前输入或清除画像后重试。';}
  function showProfile(){
    $('profile-topics').value=profile?.topics.join('，')??'';$('profile-methods').value=profile?.methods.join('，')??'';
    $('profile-regions').value=profile?.regions.join('，')??'';$('profile-start').value=profile?.start_date??'';
  }
  showProfile();
  function useText(raw){
    const detected=inferProfile(raw);
    // Only editable feature words are retained, never the source CV text.
    $('profile-topics').value=detected.topics.join('，');$('profile-methods').value=detected.methods.join('，');
    $('profile-message').textContent=detected.topics.length+detected.methods.length?'已提取候选词，请检查、补充后保存。原文件未保存。':'没有识别出方向词，请手动填写研究方向和方法。';
  }
  $('cv-file').addEventListener('change',async e=>{
    const file=e.target.files[0];if(!file)return;
    $('profile-message').textContent='正在本机读取…';$('cv-file').disabled=true;
    try{useText(await readCV(file));}
    catch(error){$('profile-message').textContent=error.message||'读取失败，请使用TXT或粘贴文字。';}
    finally{e.target.value='';$('cv-file').disabled=false;}
  });
  $('read-cv-text').addEventListener('click',()=>{
    const raw=$('cv-text').value;if(raw.trim().length<30){$('profile-message').textContent='请粘贴至少30字简历内容，或直接填写方向与方法。';return;}
    useText(raw);$('cv-text').value='';
  });
  $('profile-form').addEventListener('submit',e=>{
    e.preventDefault();
    try{
      const next=normalizeProfile({topics:$('profile-topics').value,methods:$('profile-methods').value,regions:$('profile-regions').value,start_date:$('profile-start').value});
      if(!next.topics.length&&!next.methods.length)throw new Error('请至少填一个研究方向或方法');
      if(!storageOK)throw new Error('请先清除无法读取的旧画像，再保存');
      localStorage.setItem(KEY,JSON.stringify(next));profile=next;
      $('profile-message').textContent='画像已保存在本浏览器。按共同关键词排序，申请条件仍需核实。';
      renderMatches();renderHosts();onProfile(profile);
    }catch(error){$('profile-message').textContent=error.message;}
  });
  $('clear-profile').addEventListener('click',()=>{
    try{localStorage.removeItem(KEY);}catch{$('profile-message').textContent='浏览器存储无法清除，请检查权限。';return;}
    storageOK=true;profile=null;showProfile();$('cv-text').value='';$('profile-message').textContent='已清除本机画像。';renderMatches();renderHosts();onProfile(null);
  });
  $('export-profile').addEventListener('click',()=>{
    if(!profile){$('profile-message').textContent='先保存研究画像。';return;}
    const blob=new Blob([JSON.stringify(profile,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=el('a');a.href=url;a.download='research-profile-'+today()+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),2000);
  });
  function renderLinkedIn(){
    $('linkedin-links').replaceChildren();
    try{
      const keywords=$('linkedin-keywords').value,location=$('linkedin-location').value;
      if(!keywords.trim()){$('linkedin-message').textContent='填写方向词，再打开领英搜索。';return;}
      for(const [kind,label] of [['jobs','岗位 ↗'],['people','人物 ↗'],['posts','招聘动态 ↗']]){
        const query=kind==='posts'?keywords+' hiring':keywords;
        $('linkedin-links').append(link(label,linkedinSearch(kind,{keywords:query,location})));
      }
      $('linkedin-message').textContent='只传以上关键词和地点；需要登录时在领英完成。';
    }catch(error){$('linkedin-message').textContent=error.message;}
  }
  for(const id of ['linkedin-keywords','linkedin-location'])$(id).addEventListener('input',renderLinkedIn);
  $('linkedin-use-profile').addEventListener('click',()=>{
    if(!profile){$('linkedin-message').textContent='请先保存研究画像，或直接填写方向词。';return;}
    $('linkedin-keywords').value=[...profile.topics.slice(0,1),...profile.methods.slice(0,1)].join('，');
    $('linkedin-location').value=profile.regions[0]??'';renderLinkedIn();
  });
  renderLinkedIn();
  function matching(items){
    if(!profile)return [];
    return items.map(item=>({item,match:profileMatch(item,profile)})).filter(x=>x.match.regionOK&&x.match.rank>0).sort((a,b)=>b.match.rank-a.match.rank||a.item.title?.localeCompare(b.item.title??'')||a.item.name?.localeCompare(b.item.name??''));
  }
  function renderMatches(){
    $('matched-jobs').replaceChildren();$('matched-hosts').replaceChildren();
    if(!profile){$('match-caption').textContent='保存研究画像后，查看相关岗位和导师。';return;}
    const j=matching(jobs.filter(j=>!expired(j))),h=matching(hosts);
    $('match-caption').textContent=`${j.length} 条岗位、${h.length} 条导师线索有共同关键词；不代表已满足申请条件。`;
    for(const [list,target,label] of [[j,'matched-jobs','岗位'],[h,'matched-hosts','导师']]){
      if(!list.length)$(target).append(el('p',`当前收录中没有匹配的${label}，可调整画像词或地区。`,'muted'));
      for(const {item,match} of list.slice(0,8)){
        const card=el('article','','match-card');card.append(link(item.title??item.name,item.url),el('p',`${item.institution} · ${item.country}`,'muted'),el('p','共同词：'+match.matched.join('、'),'match-reason'));
        if(label==='导师')card.append(el('p',hostStatus(item),'muted'));
        $(target).append(card);
      }
    }
  }
  $('view-profile-jobs').addEventListener('click',()=>{if(profile)goToJobs();else $('profile-message').textContent='请先保存研究画像。';});
  function hostStatus(host){
    if(host.vacancy_status==='not_checked')return '研究方向线索 · 招聘未核实';
    const related=host.related_jobs??[],visible=related.filter(j=>!expired(j)&&!j.stale);
    return visible.length?'关联公开岗位公告 · 当前状态见原公告':'关联公告可能已过期或未更新';
  }
  function renderHosts(){
    const query=$('host-query').value.trim().toLowerCase(),country=$('host-region').value;
    let selected=hosts.filter(h=>(country==='all'||h.country===country)&&[h.name,h.institution,h.department,h.research_excerpt,...(h.topics??[]),...(h.search_terms??[])].join(' ').toLowerCase().includes(query));
    if($('host-mine').checked){selected=matching(selected).map(x=>x.item);}
    const pages=Math.max(1,Math.ceil(selected.length/12));hostPage=Math.min(hostPage,pages);
    $('host-count').textContent=`${selected.length} 位导师 / 团队`;$('host-results').replaceChildren();
    if(!selected.length)$('host-results').append(el('p','当前范围没有匹配。可清除关键词或调整地区。','search-empty'));
    for(const host of selected.slice((hostPage-1)*12,hostPage*12)){
      const card=el('article','','host-card');card.append(el('h2',host.name),el('p',[host.institution,host.country,host.department].filter(Boolean).join(' · '),'muted'),el('p',host.research_excerpt||'研究内容见原网页。'),el('p',hostStatus(host),'host-status'));
      if(profile){const match=profileMatch(host,profile);if(match.matched.length)card.append(el('p','共同词：'+match.matched.join('、'),'match-reason'));}
      const actions=el('div','','host-actions');actions.append(link(host.evidence_kind==='faculty_in_advert'?'查看导师相关公告 ↗':'研究主页 ↗',host.url));
      actions.append(link('在领英找这位研究人员 ↗',linkedinSearch('people',{keywords:host.name+' '+host.institution})));
      const save=el('button',isSaved(host.url)?'已收藏':'收藏团队','save-job');save.disabled=isSaved(host.url);save.addEventListener('click',()=>{onSaveHost(host);renderHosts();});actions.append(save);card.append(actions);
      const more=el('details');more.append(el('summary','来源与相关公告'),el('p',host.research_basis,'muted'),el('p','资料读取：'+host.checked_at?.slice(0,10),'muted'));
      for(const j of host.related_jobs??[]){more.append(link(j.title,j.url),el('p',j.deadline_at?'截止：'+j.deadline_at.slice(0,10):'截止未注明','muted'));}
      card.append(more);$('host-results').append(card);
    }
    $('host-pagination').hidden=pages<=1;$('host-page-label').textContent=`${hostPage} / ${pages}`;$('host-prev').disabled=hostPage<=1;$('host-next').disabled=hostPage>=pages;
  }
  for(const id of ['host-query','host-region','host-mine'])$(id).addEventListener(id==='host-query'?'input':'change',()=>{hostPage=1;renderHosts();});
  $('host-prev').addEventListener('click',()=>{hostPage--;renderHosts();});$('host-next').addEventListener('click',()=>{hostPage++;renderHosts();});
  $('host-mine').addEventListener('change',()=>{if($('host-mine').checked&&!profile){$('host-mine').checked=false;$('host-caption').textContent='请先到“我的匹配”保存研究画像。';renderHosts();}});
  async function loadHosts(){
    try{const response=await fetch('./data/hosts.json?refresh='+Date.now(),{cache:'no-store'});if(!response.ok)throw new Error();const d=await response.json();if(d.schema_version!=='postdoc-hosts/1'||!Array.isArray(d.hosts))throw new Error();hosts=d.hosts.filter(h=>safeURL(h.url));
      $('host-caption').textContent=`收录 ${hosts.length} 位导师 / 团队，${new Set(hosts.map(h=>h.country)).size} 个地区。研究主页仅证明研究方向，招聘状态单独标注。`;
      for(const country of [...new Set(hosts.map(h=>h.country))].sort()){const o=el('option',country);o.value=country;$('host-region').append(o);}renderHosts();renderMatches();
    }catch{$('host-caption').textContent='导师库暂时无法加载，请刷新页面重试。';}
  }
  loadHosts();renderMatches();
  return {getProfile:()=>profile,setData:data=>{jobs=data.jobs;renderMatches();},refresh:()=>{renderHosts();renderMatches();}};
}
