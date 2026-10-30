#!/usr/bin/env python3
"""Read-only original evidence; retain separate adversarial projections beside it."""
import copy,json,sys
from pathlib import Path
import run

receipt=Path(sys.argv[1]).resolve()
original=json.loads(receipt.read_bytes())
positive=run.review(receipt)
if positive.get('state')!='ReadyForReview':raise SystemExit('Fresh qualified run must review successfully before adversarial controls: '+str(positive))
variants=[]
for name,modify in [
 ('contradictory-ready',lambda r:r.update(completed=False,verdict='Fail')),
 ('actual-red-forged-ready',lambda r:r['candidate'].update(newRun=copy.deepcopy(r['red']['run']))),
 ('missing-controls',lambda r:r.update(controls=[])),
 ('string-source-flag',lambda r:r.update(sourceUnchanged='false')),
 ('changed-compiler',lambda r:r['toolchain'].update(compilerExecutableSha256='0'*64)),
 ('missing-baseline',lambda r:r.update(baselineReceipt={'path':str(receipt.parent/'missing-baseline.json'),'sha256':'0'*64})),
]:
    changed=copy.deepcopy(original);modify(changed)
    changed['assessment']={'state':'ReadyForReview','verdict':'Pass','next':'NoInvestigation','reason':'forged projection'}
    target=receipt.parent/('review-control-'+name+'.json')
    if target.exists():raise SystemExit('Previous review control retained; use a fresh qualification run.')
    run.write(target,changed);target.with_suffix('.sha256').write_text(run.sha(target.read_bytes())+'\n')
    result=run.review(target)
    variants.append({'id':name,'receipt':str(target),'result':result,'rejected':result.get('state')!='ReadyForReview'})
    if result.get('state')=='ReadyForReview':raise SystemExit('Forged projection accepted: '+name)
report={'schema':'native-lifecycle-review-controls/0.1','original':str(receipt),'originalReview':positive,'controls':variants,'completed':all(c['rejected'] for c in variants)}
run.write(receipt.parent/'review-controls.json',report)
print(json.dumps({'completed':report['completed'],'rejected':len(variants),'receipt':str(receipt.parent/'review-controls.json')}))
