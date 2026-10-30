"""Adversarial protocol and retained-artifact checks, separate from native acceptance execution."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import model
import run

class LifecycleTests(unittest.TestCase):
    def packet(self):
        names=["old-"+str(i) for i in range(12)]
        return dict(baselineAvailable=True,baselineVerdict="Pass",fresh=True,artifactsIntact=True,contract="a"*64,baselineContract="a"*64,oldNamedCases=names,candidateOldCases=names,redCompilation="Pass",greenCompilation="Pass",redFailures=["boundary"],expectedRedFailures=["boundary"],candidateVerdict="Pass",exactPin=True,probeId="memo-scalar-boundary",budget=1)
    def test_output_context_rejects_source_ancestors_and_symlink_contexts(self):
        for path in (run.ROOT,run.ROOT/"artifacts/new-proof",run.ROOT.parent):
            with self.assertRaises(ValueError):run.output_context(path)
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);target=base/"real";target.mkdir();link=base/"alias";link.symlink_to(target,target_is_directory=True)
            with self.assertRaises(ValueError):run.output_context(link/"new-proof")
    def test_complete_observations_request_review_without_checker_authority(self):
        result=model.assess(self.packet());self.assertEqual(result['state'],'ReadyForReview');self.assertNotIn('authoritative',result)
    def test_missing_stale_tampered_failed_baseline_contract_or_compiler_cannot_complete(self):
        for change in [dict(baselineAvailable=False),dict(fresh=False),dict(artifactsIntact=False),dict(baselineVerdict='Fail'),dict(contract='changed'),dict(redCompilation='Fail'),dict(greenCompilation='Unavailable'),dict(redFailures=[])]:
            self.assertNotEqual(model.assess(dict(self.packet(),**change))['state'],'ReadyForReview')
    def test_absent_contracts_and_empty_or_duplicate_red_expectations_cannot_complete(self):
        for invalid in (None,"","invalid","g"*64,"0"*63):
            self.assertNotEqual(model.assess(dict(self.packet(),contract=invalid,baselineContract=invalid))["state"],"ReadyForReview")
        for names in ([],["boundary","boundary"]):
            self.assertNotEqual(model.assess(dict(self.packet(),expectedRedFailures=names,redFailures=names))["state"],"ReadyForReview")
    def test_string_and_numeric_observation_flags_are_not_boolean_evidence(self):
        for key in ("baselineAvailable","fresh","artifactsIntact","exactPin"):
            for invalid in ("false","true",1,0,None):
                self.assertNotEqual(model.assess(dict(self.packet(),**{key:invalid}))["state"],"ReadyForReview")
    def test_reduced_or_duplicated_old_named_selection_is_rejected(self):
        packet=self.packet()
        for names in [packet['oldNamedCases'][:-1],packet['oldNamedCases']+[packet['oldNamedCases'][0]],['foreign']*12]:
            self.assertEqual(model.assess(dict(packet,candidateOldCases=names))['verdict'],'Fail')
    def test_advice_only_selects_registered_probe_with_valid_integer_budget(self):
        packet=dict(self.packet(),candidateVerdict='Fail')
        self.assertEqual(model.assess(packet)['next'],'ProbeRequested')
        for budget in [0,-1,True,float('nan'),float('inf'),1.5]:
            self.assertEqual(model.assess(dict(packet,budget=budget))['next'],'ContextRequired')
        self.assertEqual(model.assess(dict(packet,probeId='arbitrary-shell'))['next'],'ContextRequired')
    def test_intake_rejects_changed_frozen_source_and_unregistered_change(self):
        config=json.loads((run.HERE/'config.json').read_text())
        import shutil
        with tempfile.TemporaryDirectory() as directory:
            temporary=Path(directory)/'lifecycle';shutil.copytree(run.HERE,temporary,ignore=shutil.ignore_patterns('__pycache__'))
            with patch.object(run,'HERE',temporary):
                run.intake(config)
                request=temporary/'change-request.json';value=json.loads(request.read_text());value['maxMemoScalars']=201;request.write_text(json.dumps(value))
                with self.assertRaises(ValueError):run.intake(config)
                value['maxMemoScalars']=200;request.write_text(json.dumps(value))
                frozen=temporary/'baseline'/Path(config['domain']).name;frozen.write_text(frozen.read_text()+'\n// changed frozen input')
                with self.assertRaises(ValueError):run.intake(config)
    def test_review_rejects_missing_or_modified_receipt_artifact_log_and_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);artifact=root/'old-library';artifact.write_bytes(b'frozen');log=root/'native.log';log.write_text('native results')
            receipt=root/'run.json';report=dict(source=run.source_snapshot(),assessment={'state':'ReadyForReview'},baselineReceipt=run.pin(artifact),execution={'log':str(log),'logSha256':run.sha(log.read_bytes())})
            def save():
                run.write(receipt,report);receipt.with_suffix('.sha256').write_text(run.sha(receipt.read_bytes()))
            save();self.assertEqual(run.review(receipt)['state'],'NotAvailable')
            artifact.unlink();self.assertEqual(run.review(receipt)['state'],'NotAvailable')
            artifact.write_bytes(b'changed');self.assertEqual(run.review(receipt)['state'],'NotAvailable')
            artifact.write_bytes(b'frozen');log.write_text('tampered');self.assertEqual(run.review(receipt)['state'],'NotAvailable')
            log.write_text('native results');report['source']['unexpected']='changed';save();self.assertEqual(run.review(receipt)['state'],'NotAvailable')
            receipt.write_text('modified receipt');self.assertEqual(run.review(receipt)['state'],'NotAvailable')

if __name__=='__main__':unittest.main()
