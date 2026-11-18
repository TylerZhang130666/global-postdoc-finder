import {validDate} from './core.mjs';

// Explicit research vocabulary, not an LLM. Names, addresses and publication
// identifiers are never used as search features.
const TOPICS={
 soil:['soil','土壤'], 'soil carbon':['soil carbon','soil organic carbon','土壤碳','有机碳'],
 'soil compaction':['soil compaction','土壤压实','土壤紧实'], 'freeze thaw':['freeze thaw','冻融'],
 ecology:['ecology','ecological','生态'], climate:['climate','气候'],
 agriculture:['agriculture','agricultural','农业'], plant:['plant','植物'],
 hydrology:['hydrology','hydrological','水文'], erosion:['erosion','侵蚀'],
 forestry:['forestry','森林','林业'], biodiversity:['biodiversity','生物多样性'],
 microbiology:['microbiology','microbial','微生物'], biogeochemistry:['biogeochemistry','biogeochemical','生物地球化学'],
 bioinformatics:['bioinformatics','生物信息'], genomics:['genomics','genomic','基因组'],
 genetics:['genetics','genetic','遗传'], neuroscience:['neuroscience','neurosciences','神经科学'],
 biology:['biology','biological','生物学'], chemistry:['chemistry','chemical','化学'],
 physics:['physics','physical sciences','物理'], mathematics:['mathematics','数学'],
 materials:['materials science','材料科学'], engineering:['engineering','工程'],
 robotics:['robotics','robotic','机器人'], medicine:['medicine','medical','医学'],
 cancer:['cancer','oncology','肿瘤','癌症'], immunology:['immunology','immunological','免疫'],
 economics:['economics','economic','经济学'], psychology:['psychology','psychological','心理学'],
 sociology:['sociology','sociological','社会学'], education:['education research','教育学'],
 history:['history','historical','历史'], philosophy:['philosophy','哲学'],
 linguistics:['linguistics','linguistic','语言学'], energy:['renewable energy','energy systems','能源'],
 astronomy:['astronomy','astrophysics','天文学'], geography:['geography','geographical','地理学'],
};
const METHODS={
 'remote sensing':['remote sensing','遥感'], GIS:['gis','geographic information systems','地理信息'],
 Python:['python'], R:['r language','r programming','r语言'], MATLAB:['matlab'], SQL:['sql'],
 statistics:['statistics','statistical analysis','统计'], modelling:['modelling','modeling','建模'],
 'machine learning':['machine learning','机器学习'], 'deep learning':['deep learning','深度学习'],
 'data science':['data science','数据科学'], 'field experiments':['field experiments','field experiment','田间试验','野外试验'],
 'meta analysis':['meta analysis','meta analyses','元分析','荟萃分析'],
 'X ray CT':['x ray ct','computed tomography','micro ct','ct扫描'],
 spectroscopy:['spectroscopy','spectroscopic','光谱'], microscopy:['microscopy','显微'],
 sequencing:['sequencing','测序'], 'mass spectrometry':['mass spectrometry','质谱'],
 'finite element':['finite element','有限元'], 'molecular dynamics':['molecular dynamics','分子动力学'],
 'qualitative research':['qualitative research','定性研究'], 'causal inference':['causal inference','因果推断'],
};
const normalized=s=>String(s??'').normalize('NFKC').toLowerCase().replace(/[–—-]/g,' ').replace(/\s+/g,' ');
export function containsFeature(text,term){
  text=normalized(text);term=normalized(term);
  if(!term)return false;
  if(/^[a-z0-9 ]+$/.test(term)){
    const escaped=term.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
    return new RegExp(`(^|[^a-z0-9])${escaped}([^a-z0-9]|$)`,'u').test(text);
  }
  return text.includes(term);
}
const FEATURE_ALIASES=new Map();
for(const [key,names] of Object.entries({...TOPICS,...METHODS})){
  const values=Object.freeze([key,...names]);
  for(const name of values)FEATURE_ALIASES.set(normalized(name),values);
}
export function aliases(term){return FEATURE_ALIASES.get(normalized(term))??[term];}
export function matchesHost(host,query){
  if(!query.trim())return true;
  const text=[host.name,...(host.aliases??[]),host.institution,host.department,host.research_excerpt,...(host.research_fields??[]),...(host.topics??[]),...(host.search_terms??[])].join(' ');
  const fold=(value,german)=>normalized(value).replace(/[äöüß]/g,c=>german?({ä:'ae',ö:'oe',ü:'ue',ß:'ss'}[c]):c).normalize('NFD').replace(/\p{M}/gu,'');
  return aliases(query).some(term=>containsFeature(text,term)||[true,false].some(german=>containsFeature(fold(text,german),fold(term,german))));
}
export function inferProfile(text){
  text=String(text).slice(0,100000).replace(/https?:\/\/\S+|\S+@\S+/g,' ');
  const detected=dict=>Object.entries(dict).filter(([,a])=>a.some(t=>containsFeature(text,t))).map(([k])=>k);
  const methods=detected(METHODS);
  if(/(?:^|[^A-Za-z0-9])R(?=$|[^A-Za-z0-9])/m.test(text)&&!methods.includes('R'))methods.push('R');
  return {topics:detected(TOPICS),methods,regions:[],start_date:''};
}
export function keywordList(value){
  const list=Array.isArray(value)?value:String(value??'').split(/[,，;；\n]+/);
  const terms=[...new Set(list.map(s=>String(s).trim()).filter(Boolean))];
  if(terms.length>30||terms.some(t=>t.length>70||/@|https?:|[\x00-\x1f]|\d{6,}/i.test(t)))throw new Error('请填写方向或技能词，每项不超过70字，最多30项；不要填写联系方式。');
  return terms;
}
export function normalizeProfile(raw){
  if(!raw||typeof raw!=='object'||Array.isArray(raw))throw new Error('无法读取研究画像');
  const countries={germany:'德国',netherlands:'荷兰',switzerland:'瑞士',sweden:'瑞典',denmark:'丹麦',china:'中国',japan:'日本',usa:'美国','united states':'美国',uk:'英国','united kingdom':'英国',canada:'加拿大',australia:'澳大利亚','new zealand':'新西兰',singapore:'新加坡',france:'法国'};
  const topics=keywordList(raw.topics),methods=keywordList(raw.methods),regions=keywordList(raw.regions).map(r=>countries[r.toLowerCase()]??r);
  const start_date=raw.start_date??'';
  if(start_date&&!validDate(start_date))throw new Error('请选择有效的可入职日期');
  return {schema_version:'postdoc-profile/1',topics,methods,regions,start_date};
}
export function profileMatch(item,profile){
  const text=[item.title,item.name,item.institution,item.department,item.summary,item.research_excerpt,
    ...(item.research_fields??[]),...(item.search_terms??[]),...(item.search_phrases??[]),...(item.topics??[])].filter(Boolean).join(' ');
  const matchedTopics=profile.topics.filter(t=>aliases(t).some(a=>containsFeature(text,a)));
  const matchedMethods=profile.methods.filter(t=>aliases(t).some(a=>containsFeature(text,a)));
  const missing=[...profile.topics,...profile.methods].filter(t=>![...matchedTopics,...matchedMethods].includes(t));
  const regionOK=!profile.regions.length||profile.regions.includes(item.country);
  return {matched:[...matchedTopics,...matchedMethods],missing,regionOK,rank:matchedTopics.length*3+matchedMethods.length*2};
}
export function linkedinSearch(kind,{keywords='',location=''}={}){
  const clean=keywordList(keywords).map(term=>aliases(term)[0]).join(' ').slice(0,220);
  if(!clean)return '';
  const paths={jobs:'/jobs/search/',people:'/search/results/people/',posts:'/search/results/content/'};
  if(!paths[kind])throw new Error('未知的领英搜索类型');
  const u=new URL(paths[kind],'https://www.linkedin.com');
  u.searchParams.set('keywords',kind==='jobs'?`postdoctoral ${clean}`:kind==='people'?clean:`postdoc ${clean}`);
  if(kind==='jobs'&&location)u.searchParams.set('location',keywordList(location).join(' '));
  if(kind!=='jobs'&&location)u.searchParams.set('keywords',u.searchParams.get('keywords')+' '+keywordList(location).join(' '));
  return u.href;
}
