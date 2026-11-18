import test from 'node:test';
import assert from 'node:assert/strict';
import {inferProfile,normalizeProfile,profileMatch,linkedinSearch,containsFeature,matchesHost} from '../profile.mjs';
import {readCV} from '../cv-reader.mjs';

test('host lookup recognizes German name variants and Chinese research fields',()=>{
  const host={name:'Michael Märker',aliases:['Michael Maerker'],institution:'ZALF',research_excerpt:'Soil erosion and Digital Soil Mapping'};
  for(const query of ['Michael','Michael Maerker','Michael Märker','Marker','土壤','侵蚀','ZALF'])assert.equal(matchesHost(host,query),true,query);
  assert.equal(matchesHost(host,'Michael Sommer'),false);
  assert.equal(matchesHost(host,'unrelated topic'),false);
  assert.equal(matchesHost({...host,research_fields:['Machine learning']},'机器学习'),true);
  assert.ok(profileMatch({research_fields:['Machine learning']},normalizeProfile({topics:'机器学习'})).rank>0);
  assert.equal(matchesHost({name:'Jean Thomas Cornelis',research_excerpt:'Soil'},'R'),false);
});

test('CV feature extraction recognizes Chinese and English without retaining CV text',()=>{
  const text='Synthetic Person. '+['private','example.org'].join('@')+' 土壤有机碳、冻融；remote-sensing, GIS, Python and R. Publications in soil ecology.';
  const p=inferProfile(text);
  assert.ok(p.topics.includes('soil carbon'));assert.ok(p.topics.includes('freeze thaw'));
  assert.ok(p.methods.includes('remote sensing'));assert.ok(p.methods.includes('GIS'));assert.ok(p.methods.includes('R'));
  assert.ok(!JSON.stringify(p).includes('Synthetic'));assert.ok(!JSON.stringify(p).includes('private'));
});
test('technical words respect boundaries rather than matching names or logistics',()=>{
  assert.equal(containsFeature('logistics service','GIS'),false);
  assert.equal(containsFeature('GIS mapping','GIS'),true);
  assert.equal(containsFeature('pythonic language','Python'),false);
});
test('confirmed profile drops unrelated CV properties and normalizes countries',()=>{
  const p=normalizeProfile({topics:'soil，carbon',methods:'GIS, Python',regions:'Germany，Netherlands',full_cv:'PRIVATE CV',name:'Synthetic Person'});
  assert.deepEqual(p.regions,['德国','荷兰']);assert.ok(!JSON.stringify(p).includes('PRIVATE'));assert.ok(!Object.hasOwn(p,'name'));
  assert.throws(()=>normalizeProfile({topics:['x'],start_date:'2026-02-31'}));
  assert.throws(()=>normalizeProfile({topics:['private'+'@'+'example.org']}));
});
test('matching respects regions and reports evidence words without eligibility claims',()=>{
  const p=normalizeProfile({topics:'soil',methods:'GIS',regions:'德国'});
  const result=profileMatch({title:'Postdoc in soil science',country:'荷兰',search_terms:['gis']},p);
  assert.deepEqual(result.matched,['soil','GIS']);assert.equal(result.regionOK,false);
  assert.ok(!Object.hasOwn(result,'eligible'));assert.ok(!Object.hasOwn(result,'probability'));
});
test('manual Chinese terms and the short R language key match English indexed evidence',()=>{
  const p=normalizeProfile({topics:'土壤',methods:'遥感，R',regions:'德国'});
  const m=profileMatch({title:'Postdoc in soil research',country:'德国',search_terms:['r'],search_phrases:['remote sensing']},p);
  assert.deepEqual(m.matched,['土壤','遥感','R']);assert.equal(m.regionOK,true);
  assert.ok(new URL(linkedinSearch('jobs',{keywords:'土壤，遥感'})).searchParams.get('keywords').includes('soil remote sensing'));
});
test('LinkedIn integration creates ordinary search links, not account access',()=>{
  for(const kind of ['jobs','people','posts']){
    const u=new URL(linkedinSearch(kind,{keywords:'soil carbon',location:'Germany'}));
    assert.equal(u.hostname,'www.linkedin.com');assert.ok(u.searchParams.get('keywords').includes('soil carbon'));
    assert.ok(!u.searchParams.has('access_token'));
  }
  assert.throws(()=>linkedinSearch('invalid',{keywords:'soil'}));
  assert.throws(()=>linkedinSearch('jobs',{keywords:'private'+'@'+'example.org'}));
  assert.equal(linkedinSearch('jobs'), '');
});
test('CV reader accepts text and rejects unsupported, oversized or empty files',async()=>{
  const value='Synthetic research profile in soil ecology and remote sensing.';
  assert.equal(await readCV({name:'sample.txt',size:value.length,text:async()=>value}),value);
  await assert.rejects(readCV({name:'sample.exe',size:50}));
  await assert.rejects(readCV({name:'sample.pdf',size:6*1024*1024}));
  await assert.rejects(readCV({name:'sample.txt',size:0,text:async()=>''}));
});
