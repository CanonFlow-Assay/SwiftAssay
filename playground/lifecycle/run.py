#!/usr/bin/env python3
"""Frozen native baseline, named R6 change, retained red/green and packed verifier consumer."""
from __future__ import annotations
import argparse,copy,hashlib,importlib.util,json,os,shutil,subprocess,sys,tarfile,zipfile,base64,csv,io
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
sys.path.insert(0,str(HERE))
from model import assess
spec=importlib.util.spec_from_file_location("expenseguard_experiment",HERE.parent/"run.py")
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
sha=prior.digest
write=prior.write_json
execute=prior.execute
observe=prior.observe


def source_snapshot():
    done=subprocess.run(["git","-C",str(ROOT),"ls-files","-c","-o","--exclude-standard","-z"],capture_output=True,check=True)
    files=sorted(set(done.stdout.split(b"\0"))-{b""})
    result={}
    for item in files:
        p=ROOT/os.fsdecode(item)
        if p.is_symlink() or not p.is_file():raise ValueError("Missing or symlinked producer input: "+str(p))
        result[str(p.relative_to(ROOT))]=sha(p.read_bytes())
    return result


def checked(argv,cwd,log):
    result=execute(list(map(str,argv)),cwd,log)
    if result["status"]!="Completed" or result["exitCode"]!=0:
        raise ValueError("Required command did not complete successfully: "+str(log))
    return result


def pin(path):return {"path":str(path),"sha256":sha(path.read_bytes())}


def compile_domain(language,compiler,source,work,log):
    work.mkdir(parents=True)
    name={"Python":"expense.py","Rust":"expense.rs","Swift":"Expense.swift","Kotlin":"Expense.kt"}[language]
    file=work/name;file.write_bytes(source.read_bytes())
    if language=="Python":
        artifact=work/"expense.pyc"
        command=compiler+["-c","import py_compile;py_compile.compile('expense.py',cfile='expense.pyc',dfile='frozen-domain/expense.py',doraise=True,invalidation_mode=py_compile.PycInvalidationMode.CHECKED_HASH)"]
    elif language=="Rust":
        artifact=work/"libexpense.rlib";command=compiler+["--edition=2024","--crate-type","rlib","--crate-name","expense","-Dwarnings",name,"-o",str(artifact)]
    elif language=="Swift":
        artifact=work/"libExpenseDomain.so";command=compiler+["-swift-version","6","-warnings-as-errors","-enable-testing","-emit-library","-emit-module","-module-name","ExpenseDomain",name,"-emit-module-path",str(work/"ExpenseDomain.swiftmodule"),"-o",str(artifact)]
    else:
        artifact=work/"domain.jar";command=compiler+[name,"-jvm-target","21","-Werror","-d",str(artifact)]
    built=checked(command,work,log)
    if language=="Python":file.unlink() # Import the real compiled module; no source fallback.
    return artifact,built


def compile_tests(language,compiler,harness,domain_artifact,work,log):
    work.mkdir(parents=True)
    names={"Python":"main.py","Rust":"main.rs","Swift":"main.swift","Kotlin":"Main.kt"}
    text=harness.read_text()
    if language=="Rust":text=text.replace("mod expense;","extern crate expense;")
    if language=="Swift" and "import ExpenseDomain" not in text:text="@testable import ExpenseDomain\n"+text
    file=work/names[language];file.write_text(text)
    if language=="Python":
        shutil.copy2(domain_artifact,work/"expense.pyc")
        built=checked(compiler+["-c","import ast;ast.parse(open('main.py').read())"],work,log)
        command=compiler+["-B",str(file)]
    elif language=="Rust":
        binary=work/"tests";built=checked(compiler+["--edition=2024","-Dwarnings",str(file),"--extern","expense="+str(domain_artifact),"-o",str(binary)],work,log);command=[str(binary)]
    elif language=="Swift":
        binary=work/"tests";built=checked(compiler+["-swift-version","6","-warnings-as-errors",str(file),"-I",str(domain_artifact.parent),"-L",str(domain_artifact.parent),"-lExpenseDomain","-Xlinker","-rpath","-Xlinker",str(domain_artifact.parent),"-o",str(binary)],work,log);command=[str(binary)]
    else:
        binary=work/"tests.jar";built=checked(compiler+[str(file),"-classpath",str(domain_artifact),"-jvm-target","21","-Werror","-include-runtime","-d",str(binary)],work,log);command=["java","-cp",str(binary)+os.pathsep+str(domain_artifact),"playground.expenseguard.tests.MainKt"]
    built["testSource"]=pin(file)
    if language=="Python":built["domainCopy"]=pin(work/"expense.pyc")
    else:built["testBinary"]=pin(binary)
    if language=="Swift":built["domainInterface"]=pin(domain_artifact.parent/"ExpenseDomain.swiftmodule")
    return command,built


def run_cases(command,work,names,log):
    result=observe(execute(command+["expanded"],work,log),names)
    return result


def intake(config):
    scope=json.loads((HERE/"input-scope.json").read_text())
    if scope.get("schema")!="expenseguard-input-scope/0.1" or scope.get("memoText")!="Well-formed Unicode text" or scope.get("originalBusinessRequirementsChanged") is not False:raise ValueError("Unsupported memo input scope")
    request=json.loads((HERE/"change-request.json").read_text())
    required={"schema","id","description","maxMemoScalars","precedes","preserves","requiredNewCases"}
    if set(request)!=required or request["schema"]!="assay-change-request/0.1" or request["id"]!="R6" or type(request["maxMemoScalars"]) is not int or request["maxMemoScalars"]!=200 or request["precedes"]!="R5" or request["preserves"]!=["R1","R2","R3","R4","R5"] or request["requiredNewCases"]!=config["newNamedCases"]:
        raise ValueError("Unsupported or altered named change; register and implement it deliberately.")
    manifest=json.loads((HERE/"baseline-manifest.json").read_text())
    for name,identity in manifest["files"].items():
        observed=(HERE/"baseline"/name).read_bytes()
        original=subprocess.check_output(["git","-C",str(ROOT),"show",config["baseCommit"]+":"+identity["producerPath"]])
        if sha(observed)!=identity["sha256"] or sha(original)!=identity["sha256"]:
            raise ValueError("Frozen baseline input differs from its original Git source: "+name)
    if sha((HERE/"baseline/contract.json").read_bytes())!=manifest["contractSha256"]:
        raise ValueError("Frozen baseline contract changed")
    frozen=json.loads((HERE/"baseline/requirements.json").read_text())
    if frozen["selections"]["expanded"]!=config["oldNamedCases"] or len(config["oldNamedCases"])!=12:raise ValueError("Frozen baseline selection changed.")
    acceptance=json.loads((HERE/"acceptance.json").read_text())
    if [c["id"] for c in acceptance["cases"]]!=config["oldNamedCases"]+config["newNamedCases"]:raise ValueError("Acceptance intake is incomplete or reduced.")
    candidate_requirements=json.loads((HERE/"requirements.json").read_text())
    if candidate_requirements["precedence"] != ["R1","R2","R3","R4","R6","R5"] or candidate_requirements["requirements"][:5] != frozen["requirements"] or candidate_requirements["requirements"][-1].get("maxMemoScalars") != 200 or candidate_requirements["cases"] != acceptance["cases"]:
        raise ValueError("Candidate requirements differ from the registered additive change.")
    return request


def package_consumer(language,compiler,output,domain_source,harness,expected):
    from package_consumer import prove
    return prove(language,compiler,ROOT,HERE,output,domain_source,harness,expected,checked,execute,observe,pin,sha,write)


def run(output):
    config=json.loads((HERE/"config.json").read_text());language=config["language"]
    before=source_snapshot();request=intake(config)
    frozen=HERE/"baseline"/Path(config["domain"]).name
    old_harness=HERE/"baseline"/Path(config["harness"]).name
    new_harness=HERE/{"Python":"main.py","Rust":"main.rs","Swift":"main.swift","Kotlin":"Main.kt"}[language]
    candidate=ROOT/"playground"/config["domain"]
    all_names=config["oldNamedCases"]+config["newNamedCases"]
    report={"schema":"assay-native-lifecycle/0.1","language":language,"baseCommit":config["baseCommit"],"producerCommit":subprocess.check_output(["git","-C",str(ROOT),"rev-parse","HEAD"],text=True).strip(),"dirty":bool(subprocess.check_output(["git","-C",str(ROOT),"status","--porcelain"],text=True)),"source":before,"requirements":pin(HERE/"baseline/requirements.json"),"inputScope":pin(HERE/"input-scope.json"),"candidateRequirements":pin(HERE/"requirements.json"),"changeRequest":pin(HERE/"change-request.json"),"acceptance":pin(HERE/"acceptance.json"),"authority":"Native fixture lifecycle only; existing checker receipts retain their own authority.","verdict":"Inconclusive","completed":False}
    write(output/"run.json",report)
    tooling,compiler,_=prior.toolchain(language,output);report["toolchain"]=tooling
    old_artifact,old_build=compile_domain(language,compiler,frozen,output/"baseline/domain",output/"baseline-domain-build.log")
    frozen_pin=pin(old_artifact)
    old_command,old_compile=compile_tests(language,compiler,old_harness,old_artifact,output/"baseline/tests",output/"baseline-tests-build.log")
    old_run=run_cases(old_command,output/"baseline/tests",config["oldNamedCases"],output/"baseline-old12.log")
    baseline={"schema":"expenseguard-frozen-baseline/0.1","source":pin(frozen),"artifact":frozen_pin,"domainBuild":old_build,"harnessBuild":old_compile,"oldNamedCases":config["oldNamedCases"],"testMinimum":12,"contract":pin(HERE/"baseline/contract.json"),"run":old_run}
    write(output/"baseline.json",baseline)
    report["baselineReceipt"]=pin(output/"baseline.json")
    if old_run["verdict"]!="Pass":raise ValueError("Original twelve-case baseline failed; no change interpretation is eligible.")
    red_command,red_compile=compile_tests(language,compiler,new_harness,old_artifact,output/"red/tests",output/"red-tests-build.log")
    red=run_cases(red_command,output/"red/tests",all_names,output/"red-acceptance.log")
    new_artifact,new_build=compile_domain(language,compiler,candidate,output/"candidate/domain",output/"candidate-domain-build.log")
    green_command,green_compile=compile_tests(language,compiler,new_harness,new_artifact,output/"candidate/new-tests",output/"candidate-new-tests-build.log")
    green=run_cases(green_command,output/"candidate/new-tests",all_names,output/"candidate-new22.log")
    preserved_command,preserved_compile=compile_tests(language,compiler,old_harness,new_artifact,output/"candidate/old-tests",output/"candidate-old-tests-build.log")
    preserved=run_cases(preserved_command,output/"candidate/old-tests",config["oldNamedCases"],output/"candidate-old12.log")
    report.update(baseline=baseline,red={"artifact":frozen_pin,"compile":red_compile,"run":red},candidate={"source":pin(candidate),"artifact":pin(new_artifact),"domainBuild":new_build,"newHarnessBuild":green_compile,"newRun":green,"oldHarnessBuild":preserved_compile,"oldRun":preserved})
    # Actual failed original baseline, using the unchanged old domain artifact.
    failed_text=old_harness.read_text().replace('2500','2501',1)
    bad_harness=output/("failed-"+old_harness.name);bad_harness.write_text(failed_text)
    # Change the known positive expected value, not an input, in a separate test copy.
    failed_text=old_harness.read_text()
    if language=="Python":failed_text=failed_text.replace('"Approved",2500','"Approved",2501',1).replace('"Approved", 2500','"Approved", 2501',1)
    elif language=="Rust":failed_text=failed_text.replace('Decision::Approved(2500)','Decision::Approved(2501)',1)
    elif language=="Swift":failed_text=failed_text.replace('.approved(2500)','.approved(2501)',1)
    else:failed_text=failed_text.replace('Approved(2500L)','Approved(2501L)',1)
    if failed_text==old_harness.read_text():raise ValueError("Failed-baseline control anchor missing")
    bad_harness.write_text(failed_text)
    bad_command,bad_compile=compile_tests(language,compiler,bad_harness,old_artifact,output/"failed-baseline/tests",output/"failed-baseline-build.log")
    bad=run_cases(bad_command,output/"failed-baseline/tests",config["oldNamedCases"],output/"failed-baseline.log")
    report["failedBaselineControl"]={"compile":bad_compile,"run":bad}
    report["consumer"]=package_consumer(language,compiler,output,candidate,new_harness,all_names)
    packet={"baselineAvailable":True,"baselineVerdict":old_run["verdict"],"fresh":before==source_snapshot() and not report["dirty"],"artifactsIntact":sha(old_artifact.read_bytes())==frozen_pin["sha256"],"contract":sha((HERE/"contract.json").read_bytes()),"baselineContract":baseline["contract"]["sha256"],"oldNamedCases":config["oldNamedCases"],"candidateOldCases":config["oldNamedCases"] if preserved["verdict"]=="Pass" else [],"redCompilation":"Pass","greenCompilation":"Pass","redFailures":red.get("failed"),"expectedRedFailures":config["expectedRedFailures"],"candidateVerdict":green["verdict"],"exactPin":tooling["exactPinQualified"],"probeId":"memo-scalar-boundary","budget":1}
    report["assessment"]=assess(packet);report["assessmentInput"]=packet
    controls=[]
    for name,change in [("missing-baseline",{"baselineAvailable":False}),("stale-source",{"fresh":False}),("reduced-test-selection",{"candidateOldCases":config["oldNamedCases"][:-1]}),("changed-contract",{"contract":"0"*64}),("failed-original-baseline",{"baselineVerdict":bad["verdict"]})]:
        observed=assess(dict(packet,**change));controls.append({"id":name,"assessment":observed,"rejected":observed["state"]!="ReadyForReview"})
    tampered=output/"tampered-baseline-artifact";shutil.copy2(old_artifact,tampered)
    with tampered.open("ab") as stream:stream.write(b"tampered")
    tamper_assess=assess(dict(packet,artifactsIntact=sha(tampered.read_bytes())==frozen_pin["sha256"]))
    controls.append({"id":"tampered-artifact","artifact":pin(tampered),"assessment":tamper_assess,"rejected":tamper_assess["state"]!="ReadyForReview"})
    report["controls"]=controls
    report["sourceUnchanged"]=before==source_snapshot()
    report["completed"]=report["assessment"]["state"]=="ReadyForReview" and bad["verdict"]=="Fail" and all(c["rejected"] for c in controls) and report["consumer"]["completed"] and report["sourceUnchanged"]
    report["verdict"]=report["assessment"]["verdict"] if report["assessment"]["verdict"] != "Pass" or report["completed"] else "Fail"
    report["nonclaims"]=["No new blocking rule admission or semantic purity claim.","No package publication, provider calls or automatic equivalence.","Packed checker static verdict is separate from native behavior execution.","ReadyForReview is not human acceptance or release approval."]
    return report


def output_context(path):
    path=Path(os.path.abspath(path))
    if path==ROOT or ROOT in path.parents or path in ROOT.parents:
        raise ValueError("Evidence must be outside the producer and cannot contain producer inputs.")
    for item in [path,*path.parents]:
        if item.is_symlink():raise ValueError("Evidence output context contains a symlink.")
    return path


def _review(receipt):
    import tempfile
    receipt=Path(os.path.abspath(receipt));out=output_context(receipt.parent)
    if receipt.suffix!='.json' or receipt.is_symlink():raise ValueError("Unsupported or aliased receipt path")
    data=receipt.read_bytes()
    if sha(data)!=receipt.with_suffix('.sha256').read_text().strip():raise ValueError("Receipt bytes changed")
    r=json.loads(data)
    required={'schema','language','baseCommit','producerCommit','dirty','source','requirements','inputScope','candidateRequirements','changeRequest','acceptance','verdict','completed','toolchain','baseline','baselineReceipt','red','candidate','failedBaselineControl','consumer','assessment','assessmentInput','controls','sourceUnchanged'}
    if not isinstance(r,dict) or not required.issubset(r) or r['schema']!='assay-native-lifecycle/0.1':raise ValueError("Incomplete lifecycle schema")
    if any(type(r[k]) is not bool for k in ('dirty','completed','sourceUnchanged')):raise ValueError("Completion/source flags require booleans")
    if r['verdict'] not in ('Pass','Fail','Inconclusive','ToolFailure'):raise ValueError("Unknown lifecycle verdict")
    if (r['assessment'].get('state')=='ReadyForReview') != (r['completed'] is True and r['verdict']=='Pass'):
        raise ValueError("Assessment projection contradicts completion/verdict")
    config=json.loads((HERE/'config.json').read_text());intake(config)
    language=config['language'];old=config['oldNamedCases'];names=old+config['newNamedCases']
    if r['language']!=language or r['baseCommit']!=config['baseCommit']:raise ValueError("Candidate identity changed")
    if r['producerCommit']!=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip():raise ValueError("Producer revision changed")
    if r['dirty'] or bool(subprocess.check_output(['git','-C',str(ROOT),'status','--porcelain'],text=True)):raise ValueError("Qualification requires committed, clean producer inputs")
    if r['source']!=source_snapshot() or r['sourceUnchanged'] is not True:raise ValueError("Producer inputs changed")
    def artifact(record,expected=None,source=False):
        if not isinstance(record,dict) or not {'path','sha256'}.issubset(record) or not isinstance(record['path'],str) or not isinstance(record['sha256'],str):raise ValueError("Missing artifact binding")
        file=Path(os.path.abspath(record['path']));scope=ROOT if source else out
        if expected is not None and file!=Path(os.path.abspath(expected)):raise ValueError("Artifact role/path changed")
        if file.is_symlink() or not file.is_file() or not file.resolve().is_relative_to(scope.resolve()):raise ValueError("Missing/unsafe artifact")
        if sha(file.read_bytes())!=record['sha256']:raise ValueError("Artifact bytes changed")
        return file
    def execution(record,expected_log=None,success=False):
        if not isinstance(record,dict) or not {'argv','status','exitCode','stdout','stderr','stdoutSha256','stderrSha256','log','logSha256'}.issubset(record):raise ValueError("Incomplete execution record")
        if not isinstance(record['argv'],list) or not all(isinstance(x,str) for x in record['argv']):raise ValueError("Malformed command vector")
        if record['status']!='Completed' or type(record['exitCode']) is not int:raise ValueError("Interrupted or invalid execution")
        log=artifact({'path':record['log'],'sha256':record['logSha256']},expected_log)
        raw=log.read_bytes();stdout,separator,stderr=raw.partition(b'\n--- stderr ---\n')
        if not separator or stdout.decode('utf8',errors='replace')!=record['stdout'] or stderr.decode('utf8',errors='replace')!=record['stderr'] or sha(stdout)!=record['stdoutSha256'] or sha(stderr)!=record['stderrSha256']:raise ValueError("Raw output binding differs from record")
        if success and record['exitCode']!=0:raise ValueError("Required compile/tool command failed")
        return dict(record,stdout=stdout.decode('utf8',errors='replace'),stderr=stderr.decode('utf8',errors='replace'))
    def cases(record,expected,log):
        actual=observe(execution(record['execution'],out/log),expected)
        if {key:record.get(key) for key in ('verdict','tests','failed')} != {key:actual.get(key) for key in ('verdict','tests','failed')}:raise ValueError("Cached native result differs from raw named test output")
        if actual['verdict'] not in ('Pass','Fail'):raise ValueError("Incomplete named acceptance results")
        return actual
    def build(record,log):
        execution(record,out/log,True)
        for key in ('testSource','domainCopy','testBinary','domainInterface'):
            if key in record:artifact(record[key])
        return 'Pass'
    for key,path in [('inputScope',HERE/'input-scope.json'),('requirements',HERE/'baseline/requirements.json'),('candidateRequirements',HERE/'requirements.json'),('changeRequest',HERE/'change-request.json'),('acceptance',HERE/'acceptance.json')]:artifact(r[key],path,True)
    baseline_file=artifact(r['baselineReceipt'],out/'baseline.json')
    b=r['baseline'];c=r['candidate']
    if json.loads(baseline_file.read_bytes())!=b:raise ValueError("Frozen baseline receipt changed")
    if b['oldNamedCases']!=old or type(b['testMinimum']) is not int or b['testMinimum']!=12:raise ValueError("Frozen test minima changed")
    artifact(b['source'],HERE/'baseline'/Path(config['domain']).name,True)
    artifact(b['contract'],HERE/'baseline/contract.json',True)
    old_artifact=artifact(b['artifact']);new_artifact=artifact(c['artifact'])
    if old_artifact==new_artifact or r['red']['artifact']!=b['artifact']:raise ValueError("Old artifact is not separately frozen")
    artifact(r['red']['artifact'],old_artifact)
    artifact(c['source'],ROOT/'playground'/config['domain'],True)
    for label,record in [('baseline-domain-build.log',b['domainBuild']),('baseline-tests-build.log',b['harnessBuild']),('red-tests-build.log',r['red']['compile']),('candidate-domain-build.log',c['domainBuild']),('candidate-new-tests-build.log',c['newHarnessBuild']),('candidate-old-tests-build.log',c['oldHarnessBuild']),('failed-baseline-build.log',r['failedBaselineControl']['compile'])]:build(record,label)
    for record in [b['harnessBuild'],r['red']['compile'],c['newHarnessBuild'],c['oldHarnessBuild'],r['failedBaselineControl']['compile']]:
        if 'testSource' not in record or ('domainCopy' if language=='Python' else 'testBinary') not in record:raise ValueError("Actual native test output artifact is unbound")
    old_run=cases(b['run'],old,'baseline-old12.log')
    red=cases(r['red']['run'],names,'red-acceptance.log')
    green=cases(c['newRun'],names,'candidate-new22.log')
    kept=cases(c['oldRun'],old,'candidate-old12.log')
    bad=cases(r['failedBaselineControl']['run'],old,'failed-baseline.log')
    if bad['verdict']!='Fail' or bad['failed']!=['approved']:raise ValueError("Actual failed-original-baseline control missing")
    consumer=r['consumer']
    if type(consumer.get('completed')) is not bool or consumer['completed'] is not True or consumer.get('producerSourceReferences') is not False:raise ValueError("Independent consumer did not complete")
    archive=artifact(consumer['archive'])
    app_source=artifact(consumer['applicationSource'])
    if sha(app_source.read_bytes())!=sha((ROOT/'playground'/config['domain']).read_bytes()):raise ValueError("Consumer source differs from candidate")
    verified=execution(consumer['verification'],out/'consumer-verification.log',True)
    observed_receipt=json.loads(verified['stdout'])
    if observed_receipt!=consumer['checkerReceipt']:raise ValueError("Cached checker receipt differs from actual retained output")
    verdict=observed_receipt.get('verdict');kind=verdict.get('kind') if isinstance(verdict,dict) else verdict
    if kind!='Pass' or verdict!=consumer['reportedCheckerVerdict']:raise ValueError("Consumer checker observation is not Pass")
    if any(str(ROOT/'src') in arg or str(ROOT/'Sources') in arg or str(ROOT/'kotlin-assay')==arg for arg in verified['argv']):raise ValueError("Consumer command references producer source")
    if language=='Python':
        execution(consumer['install'],out/'consumer-install.log',True);origin=execution(consumer['origin'],out/'consumer-origin.log',True)
        installed=consumer.get('installedModules')
        expected_files=sorted(p.name for p in (ROOT/'src/python_assay').glob('*.py'))
        if not isinstance(installed,list) or sorted(Path(p['path']).name for p in installed)!=expected_files:raise ValueError("Incomplete installed Python modules")
        with zipfile.ZipFile(archive) as wheel_archive:
            for entry in installed:
                file=artifact(entry)
                if file.read_bytes()!=wheel_archive.read('python_assay/'+file.name) or file.read_bytes()!=(ROOT/'src/python_assay'/file.name).read_bytes():raise ValueError("Installed Python module differs from packed/current producer bytes")
        if str(out/'independent-consumer/site-packages') not in origin['stdout']:raise ValueError("Python import origin changed")
    else:
        binary=artifact(consumer['binary'])
        if language=='Rust':
            execution(consumer['producerBuild'],out/'packed-tool-build.log',True)
            with tarfile.open(archive) as tar:
                if tar.extractfile('rust-assay/rust-assay').read()!=binary.read_bytes():raise ValueError("Installed Rust binary differs from archive")
        elif language=='Swift':
            execution(consumer['consumerBuild'],out/'consumer-build.log',True)
            installed=consumer.get('installedSources')
            if not isinstance(installed,list) or not installed:raise ValueError("SwiftPM installed source is unbound")
            for entry in installed:artifact(entry)
            with tarfile.open(archive) as tar:
                for entry in installed:
                    file=Path(entry['path']);relative=file.relative_to(out/'independent-consumer/installed/SwiftAssay')
                    if tar.extractfile('SwiftAssay/'+str(relative)).read()!=file.read_bytes() or file.read_bytes()!=(ROOT/relative).read_bytes():raise ValueError("SwiftPM consumer source differs from current archive producer")
        else:
            execution(consumer['producerBuild'],out/'packed-tool-build.log',True)
            if archive.read_bytes()!=binary.read_bytes():raise ValueError("Installed verifier JAR differs from archive")
            log=artifact(consumer['nativeAcceptanceLog']);artifact(consumer['nativeCompiledApplication'])
            raw=log.read_text();rows=observe({'stdout':raw,'exitCode':0,'status':'Completed'},names)
            if rows['verdict']!='Pass':raise ValueError("Consumer named acceptance did not pass")
            commands=observed_receipt.get('commands',[])
            if len(commands)!=1 or commands[0].get('status')!='Passed' or type(commands[0].get('exitCode')) is not int or commands[0]['exitCode']!=0 or commands[0].get('outputSha256')!=sha(log.read_bytes()):raise ValueError("Consumer command output binding changed")
            lock=json.loads((ROOT/'toolchain.lock.json').read_text());home=Path(lock['compilerHome'])
            deps=[Path(lock['persistentCollectionsJar'])]+[Path(lock[k]['jar']) for k in ('kotlinx-serialization-core-jvm','kotlinx-serialization-json-jvm')]
            expected=sorted(str(p) for p in [*sorted((home/'lib').glob('*.jar')),*deps])
            actual=consumer.get('runtimeDependencies',[])
            if sorted(p['path'] for p in actual)!=expected:raise ValueError("Kotlin runtime dependency scope changed")
            for entry in actual:
                if not Path(entry['path']).is_file() or sha(Path(entry['path']).read_bytes())!=entry['sha256']:raise ValueError("Kotlin runtime dependency changed")
    with tempfile.TemporaryDirectory(prefix='native-lifecycle-tool-review-') as directory:
        current,_,_=prior.toolchain(language,Path(directory))
    tool=r['toolchain'];execution(tool['execution'],out/'toolchain.log',True)
    if current['exactPinQualified'] is not True or tool.get('exactPinQualified') is not True or current['runtimePin']!=tool.get('runtimePin') or current['observed']!=tool.get('observed') or current['compilerExecutableSha256']!=tool.get('compilerExecutableSha256'):raise ValueError("Current native compiler/runtime does not match qualified evidence")
    if tool.get('java') is not None:execution(tool['java'],out/'java.log',True)
    packet={'baselineAvailable':True,'baselineVerdict':old_run['verdict'],'fresh':True,'artifactsIntact':True,'contract':sha((HERE/'contract.json').read_bytes()),'baselineContract':b['contract']['sha256'],'oldNamedCases':old,'candidateOldCases':old if kept['verdict']=='Pass' else [],'redCompilation':'Pass','greenCompilation':'Pass','redFailures':red['failed'],'expectedRedFailures':config['expectedRedFailures'],'candidateVerdict':green['verdict'],'exactPin':True,'probeId':'memo-scalar-boundary','budget':1}
    derived=assess(packet)
    controls=r['controls'];expected_ids=['missing-baseline','stale-source','reduced-test-selection','changed-contract','failed-original-baseline','tampered-artifact']
    if not isinstance(controls,list) or [control.get('id') for control in controls]!=expected_ids:raise ValueError("Missing required controls")
    changes=[{'baselineAvailable':False},{'fresh':False},{'candidateOldCases':old[:-1]},{'contract':'0'*64},{'baselineVerdict':bad['verdict']}]
    for control,change in zip(controls[:5],changes):
        projected=assess(dict(packet,**change))
        if control.get('rejected') is not True or control.get('assessment')!=projected or projected['state']=='ReadyForReview':raise ValueError("Control projection differs from observations")
    tampered=artifact(controls[-1]['artifact'],out/'tampered-baseline-artifact')
    tamper_result=assess(dict(packet,artifactsIntact=sha(tampered.read_bytes())==b['artifact']['sha256']))
    if controls[-1].get('rejected') is not True or controls[-1].get('assessment')!=tamper_result or tamper_result['state']=='ReadyForReview':raise ValueError("Tampered baseline control is unavailable")
    computed=derived['state']=='ReadyForReview' and old_run['verdict']=='Pass' and green['verdict']=='Pass' and kept['verdict']=='Pass' and bad['verdict']=='Fail'
    computed_verdict=derived['verdict'] if derived['verdict']!='Pass' or computed else 'Fail'
    if r['assessmentInput']!=packet or r['assessment']!=derived or r['completed'] is not computed or r['verdict']!=computed_verdict:raise ValueError("Lifecycle projection differs from independently reconstructed raw evidence")
    return derived


def review(receipt):
    try:return _review(receipt)
    except (OSError,ValueError,KeyError,TypeError,AttributeError,subprocess.SubprocessError,zipfile.BadZipFile,tarfile.TarError) as error:
        return {'state':'NotAvailable','verdict':'Inconclusive','next':'ContextRequired','reason':str(error)}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);parser.add_argument('--review',type=Path)
    args=parser.parse_args()
    if args.review:
        result=review(args.review.resolve());print(json.dumps(result));return 0 if result['state']=='ReadyForReview' else 2
    if not args.output:parser.error('Supply a fresh --output directory or --review receipt.')
    try:output=output_context(args.output)
    except ValueError as error:parser.error(str(error))
    if output.exists():parser.error('Existing evidence is retained; choose a fresh output.')
    if HERE==output or HERE in output.parents:parser.error('Evidence cannot overwrite lifecycle source.')
    output.mkdir(parents=True)
    try:report=run(output)
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as error:
        report=json.loads((output/'run.json').read_text()) if (output/'run.json').exists() else {}
        report.update(verdict='ToolFailure',completed=False,error=str(error))
    write(output/'run.json',report);(output/'run.sha256').write_text(sha((output/'run.json').read_bytes())+'\n')
    print(json.dumps({'verdict':report['verdict'],'completed':report['completed'],'receipt':str(output/'run.json')}))
    return {'Pass':0,'Fail':1,'Inconclusive':2,'ToolFailure':3}[report['verdict']]

if __name__=='__main__':raise SystemExit(main())
