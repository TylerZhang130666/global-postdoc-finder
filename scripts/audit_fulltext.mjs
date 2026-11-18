// Compare real website matching on identical records, without expiry filters.
import fs from 'node:fs';
import {matchesJob} from '../web/jobs.mjs';
const [baselinePath,currentPath,queriesPath,outPath]=process.argv.slice(2);
if(!outPath)throw new Error('Usage: node scripts/audit_fulltext.mjs baseline.json current.json queries.json out.json');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const baseline=read(baselinePath),current=read(currentPath),queries=read(queriesPath);
const byId=new Map(current.jobs.map(j=>[j.id,j]));
const same=baseline.jobs.filter(j=>byId.has(j.id)),oldIds=new Set(baseline.jobs.map(j=>j.id));
const distinct=new Set();
const comparisons=queries.map(query=>{
  const old=same.filter(j=>matchesJob(j,query));
  const next=same.filter(j=>matchesJob({...j,...Object.fromEntries(Object.entries(byId.get(j.id)).filter(([k])=>k.startsWith('search_')))},query));
  const ids=new Set(old.map(j=>j.id));const added=next.filter(j=>!ids.has(j.id));
  added.forEach(j=>distinct.add(j.id));
  return {query,before:old.length,after:next.length,new_matches:added.length,new_job_ids:added.map(j=>j.id)};
});
const report={method:'Same baseline listing metadata; only search_terms/search_phrases replaced. Actual website matcher. No expiry filter. Query-job matches are not unique vacancies or fit assessments.',baseline_generated_at:baseline.generated_at,current_generated_at:current.generated_at,compared_jobs:same.length,queries:comparisons.length,new_query_job_pairs:comparisons.reduce((n,r)=>n+r.new_matches,0),distinct_previously_missed_jobs:distinct.size,added_listing_jobs:current.jobs.filter(j=>!oldIds.has(j.id)).length,coverage:current.sources.map(s=>({source_id:s.id,total:current.jobs.filter(j=>j.source_id===s.id).length,indexed:s.body_indexed,unavailable:s.body_unavailable,pending:s.body_pending,coverage:s.coverage})),comparisons};
fs.writeFileSync(outPath,JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({...report,comparisons:comparisons.map(({new_job_ids,...r})=>r)},null,2));
