import { readFile, writeFile, access } from 'node:fs/promises';
import { resolve } from 'node:path';
const root=process.argv[2];
if(!root)throw new Error('Usage: node install-performance-scenario.mjs <candidate-root>');
const component=resolve(root,'client/src/components/QueueOverview.tsx');
try {await access(component);throw new Error('Scenario already installed; refusing to overwrite.');}catch(e){if(e.code!=='ENOENT')throw e;}
const appPath=resolve(root,'client/src/App.tsx');
let app=await readFile(appPath,'utf8');
if(!app.includes('<section className="summary"'))throw new Error('App layout changed. Integrate QueueOverview manually on a review branch. No files written.');
const source=`import { fixtures } from '../../../server/store';
const records = fixtures(12000);
export function QueueOverview({search}: {search: string}) {
  const visible = records.filter(t => (t.customer + ' ' + t.title).toLowerCase().includes(search.toLowerCase()));
  const preview = visible.map(ticket => ({...ticket, customerRequests: visible.filter(other => other.customer === ticket.customer).length}));
  return <section aria-label="Queue overview"><h2>Customer overview — {visible.length} requests</h2><div style={{maxHeight:280,overflow:'auto'}}>{preview.map(t=><p key={t.id}>{t.id} · {t.customer} · {t.title} · {t.customerRequests} customer requests</p>)}</div></section>;
}
`;
app=`import { QueueOverview } from './components/QueueOverview';\n`+app.replace('<section className="summary"','<QueueOverview search={query.q} />\n        <section className="summary"');
await writeFile(component,source);await writeFile(appPath,app);
console.log('Performance scenario installed on the supplied working copy. Run typecheck and start the app.');
