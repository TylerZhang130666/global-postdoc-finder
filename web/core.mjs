export const TYPES = {advertised_job:'已发布岗位', fellowship:'博后基金', potential_host:'导师与团队线索'};
export const PROGRESS = {saved:'刚收藏', checking:'核实中', preparing:'准备材料', contacted:'已联系', applied:'已申请', archived:'已归档'};
export const CRITERIA = {degree_timing:'学位与毕业时间', start_date:'可接受的入职时间', language:'语言要求', nationality:'国籍要求（如有）', residence:'流动性 / 居留要求', user_constraints:'薪酬、合同与个人条件'};
export const RESULTS = {unknown:'待核实', pass:'已有证据支持', fail:'确认不符合', not_applicable:'不适用'};
export const ACCESS = {unconfirmed:'申请状态待确认', open:'记录为开放', scheduled:'后续轮次', closed:'记录为关闭', not_applicable:'未确认招聘空缺'};
export function today(){const d=new Date();return [d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-');}
export function safeURL(value){
  if(typeof value!=='string'||/[\x00-\x20\x7f]/.test(value.trim())||value.length>4000)return '';
  try{const u=new URL(value.trim());return ['https:','http:'].includes(u.protocol)&&u.hostname&&!u.username&&!u.password?u.href:'';}catch{return '';}
}
export function canonicalURL(value){const url=safeURL(value);if(!url)return '';const u=new URL(url);for(const k of [...u.searchParams.keys()])if(/^utm_/i.test(k)||['fbclid','gclid'].includes(k))u.searchParams.delete(k);u.searchParams.sort();return u.href;}
export function validDate(value){return typeof value==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(value)&&Number(value.slice(0,4))>=1900&&Number(value.slice(0,4))<=2200&&!Number.isNaN(Date.parse(value+'T00:00:00Z'))&&new Date(value+'T00:00:00Z').toISOString().slice(0,10)===value;}
export function deadlineLabel(date,asOf=today()){
  if(!validDate(date))return '截止时间待核实';
  const days=Math.round((Date.parse(date+'T00:00:00Z')-Date.parse(asOf+'T00:00:00Z'))/86400000);
  if(days<0)return '所记日期已过，需查是否延期';
  if(days===0)return '所记截止为今天，请核实当地时区';
  return `${date} · 约 ${days} 天后`;
}
function field(value,name,max=12000){if(value==null)return '';if(typeof value!=='string'||value.length>max)throw new Error(`${name} 应为不超过 ${max} 字符的文字`);return value.trim();}
function dateField(value,name){if(value==null||value==='')return '';if(!validDate(value))throw new Error(`${name} 应为有效的 YYYY-MM-DD 日期`);return value;}
export function normalizeRecord(raw){
  if(!raw||typeof raw!=='object'||Array.isArray(raw))throw new Error('每条机会应是一个对象');
  const type=raw.opportunity_type??'advertised_job';if(!Object.hasOwn(TYPES,type))throw new Error('机会类型不受支持');
  const title=field(raw.title,'标题',300);if(!title)throw new Error('每条机会都需要标题');
  const url=safeURL(raw.source_url);if(!url)throw new Error(`「${title}」的来源应为不含登录凭据的 HTTP(S) 链接`);
  const progress=raw.progress??'saved';if(!Object.hasOwn(PROGRESS,progress))throw new Error('跟进进度不受支持');
  const checks=Object.fromEntries(Object.keys(CRITERIA).map(k=>[k,'unknown']));
  if(raw.checks!=null){if(typeof raw.checks!=='object'||Array.isArray(raw.checks))throw new Error('核验项目格式不正确');for(const k of Object.keys(CRITERIA)){if(raw.checks[k]!=null){if(!Object.hasOwn(RESULTS,raw.checks[k]))throw new Error('核验结果不受支持');checks[k]=raw.checks[k];}}}
  if(Array.isArray(raw.eligibility_checks))for(const c of raw.eligibility_checks)if(c&&Object.hasOwn(checks,c.criterion)&&Object.hasOwn(RESULTS,c.result))checks[c.criterion]=c.result;
  const access=raw.application_access??'unconfirmed';if(!Object.hasOwn(ACCESS,access)&&access!=='invitation_only')throw new Error('申请状态不受支持');
  const checked=dateField(raw.date_checked,'核验日期');if(checked&&checked>today())throw new Error('核验日期不能在未来');
  let evidence=field(raw.evidence??'','证据备注');
  if(!evidence&&raw.eligibility_checks){evidence=raw.eligibility_checks.map(c=>`${String(c.criterion??'')}: ${String(c.evidence??'未记录证据')}`).join('\n');}
  if(!evidence&&raw.source_locator)evidence=field(raw.source_locator,'原文位置');
  return {
    id:field(raw.id,'记录编号',100)||globalThis.crypto.randomUUID(),
    title, institution:field(raw.institution,'机构',200),country:field(raw.country??raw.country_region,'国家或地区',100),source_url:url,opportunity_type:type,progress,
    deadline:dateField(raw.deadline,'截止日期'),date_checked:checked,application_access:access==='invitation_only'?'unconfirmed':access,
    checks,evidence,next_action:field(raw.next_action,'下一步',500),imported:raw.imported===true,
    // Preserve the full Skill evidence without trusting scores or executing supplied fields.
    ...(raw.skill_record?{skill_record:raw.skill_record}:raw.record_id?{skill_record:raw}:{}),
  };
}
export function parseImport(text){
  if(typeof text!=='string'||text.length>5*1024*1024)throw new Error('请使用小于 5 MB 的 JSON 文件');
  let data;try{data=JSON.parse(text);}catch{throw new Error('文件不是有效的 JSON');}
  if(!Array.isArray(data)&&data?.schema_version&&data.schema_version!=='postdoc-workbench/1')throw new Error('不支持这个备份版本，请保留原文件');
  const list=Array.isArray(data)?data:data?.records;
  if(!Array.isArray(list)||list.length>1000)throw new Error('应为记录数组或含 records 的对象，最多 1000 条');
  return list.map((r,i)=>{try{return {...normalizeRecord(r),imported:true};}catch(e){throw new Error(`第 ${i+1} 条：${e.message}`);}});
}
export function identity(r){return [canonicalURL(r.source_url),r.title,r.institution,r.deadline].join('\u001f');}
export function mergeRecords(existing,incoming){
  const result=[...existing];const known=new Set(existing.map(identity));let added=0,skipped=0;
  for(const record of incoming){const key=identity(record);if(known.has(key)){skipped++;continue;}const next={...record};if(result.some(r=>r.id===next.id))next.id=globalThis.crypto.randomUUID();result.push(next);known.add(key);added++;}
  if(result.length>1000)throw new Error('合并后超过 1000 条，请先导出并整理清单');
  return {records:result,added,skipped};
}
export function csvCell(value){let s=String(value??'');if(/^[\s\uFEFF]*[=+\-@]/.test(s))s="'"+s;return '"'+s.replaceAll('"','""')+'"';}
export function toCSV(records){const rows=[['标题','机构','国家或地区','类型','跟进进度','来源链接','记录的截止日期','人工核验日期','记录的申请状态','下一步','证据备注']];for(const r of records)rows.push([r.title,r.institution,r.country,TYPES[r.opportunity_type],PROGRESS[r.progress],r.source_url,r.deadline,r.date_checked,ACCESS[r.application_access],r.next_action,r.evidence]);return '\uFEFF'+rows.map(row=>row.map(csvCell).join(',')).join('\r\n');}
export function searchURL(source,keywords){const u=new URL('https://www.google.com/search');const domain=new URL(source.url).hostname;u.searchParams.set('q',`site:${domain} ${keywords.trim()} ${source.opportunity_types.includes('advertised_job')?'postdoc':''}`.trim());return u.href;}
export function filterSources(sources,region,type){return sources.filter(s=>(type==='all'||s.opportunity_types.includes(type))&&(region==='all'||s.web_regions.includes(region)||s.web_regions.includes('global')));}
export function matchSource(url,sources){const parsed=safeURL(url);if(!parsed)return null;const exact=sources.find(s=>canonicalURL(s.url)===canonicalURL(parsed));if(exact)return exact;const host=new URL(parsed).hostname;return sources.find(s=>{const target=new URL(s.url).hostname;return host===target||host.endsWith('.'+target);})??null;}
