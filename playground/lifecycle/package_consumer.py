"""Build local verifier archives and exercise fresh consumers without producer source imports."""
import base64,csv,io,json,os,shutil,subprocess,tarfile,zipfile
from pathlib import Path


def wheel(root,destination,sha):
    name='python_assay-0.1.0.dist-info';entries={}
    for file in sorted((root/'src/python_assay').glob('*.py')):entries['python_assay/'+file.name]=file.read_bytes()
    entries[name+'/METADATA']=b'Metadata-Version: 2.1\nName: python-assay\nVersion: 0.1.0\nRequires-Python: >=3.14\nLicense: Apache-2.0\n\nLocally packed existing verifier.\n'
    entries[name+'/WHEEL']=b'Wheel-Version: 1.0\nGenerator: astra-local-stdlib-wheel/0.1\nRoot-Is-Purelib: true\nTag: py3-none-any\n'
    entries[name+'/entry_points.txt']=b'[console_scripts]\npython-assay = python_assay.cli:main\n'
    entries[name+'/licenses/LICENSE']=(root/'LICENSE').read_bytes()
    record=io.StringIO();writer=csv.writer(record,lineterminator='\n')
    for path,data in entries.items():writer.writerow([path,'sha256='+base64.urlsafe_b64encode(bytes.fromhex(sha(data))).decode().rstrip('='),str(len(data))])
    writer.writerow([name+'/RECORD','','']);entries[name+'/RECORD']=record.getvalue().encode()
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as archive:
        for path,data in sorted(entries.items()):archive.writestr(path,data)


def tar_files(destination,files):
    with tarfile.open(destination,'w:gz') as archive:
        for path,name in files:archive.add(path,arcname=name,recursive=False)


def extract(archive,directory):
    directory.mkdir(parents=True)
    with tarfile.open(archive) as source:
        for member in source.getmembers():
            if member.issym() or member.islnk() or Path(member.name).is_absolute() or '..' in Path(member.name).parts:raise ValueError('Unsafe packed archive')
        source.extractall(directory,filter='data')


def prove(language,compiler,root,here,output,domain_source,harness,expected,checked,execute,observe,pin,sha,write):
    packed=output/'packages';packed.mkdir()
    consumer=output/'independent-consumer';consumer.mkdir()
    app=consumer/'application';(app/'domain').mkdir(parents=True)
    copied=app/'domain'/domain_source.name;shutil.copy2(domain_source,copied)
    result={'scope':'Locally packed existing verifier; static authority remains lexical or strict-syntax as documented.','producerSourceReferences':False,'consumerRoot':str(consumer),'completed':False}
    if language=='Python':
        archive=packed/'python_assay-0.1.0-py3-none-any.whl';wheel(root,archive,sha)
        site=consumer/'site-packages'
        result['install']=checked(compiler+['-I','-m','pip','install','--disable-pip-version-check','--no-index','--no-deps','--target',str(site),str(archive)],consumer,output/'consumer-install.log')
        launcher=consumer/'checker.py';launcher.write_text('import sys;sys.path.insert(0,'+repr(str(site))+');from python_assay.cli import main;raise SystemExit(main())\n')
        command=compiler+['-I',str(launcher),'check',str(app/'domain'),'--json']
        origin=checked(compiler+['-I','-c','import sys;sys.path.insert(0,'+repr(str(site))+');import python_assay;print(python_assay.__file__)'],consumer,output/'consumer-origin.log')
        if str(root/'src') in origin['stdout'] or str(site) not in origin['stdout']:raise ValueError('Consumer imported producer source')
        result['origin']=origin
        result['installedModules']=[pin(p) for p in sorted((site/'python_assay').glob('*.py'))]
    elif language=='Rust':
        target=output/'producer-tool-build'
        result['producerBuild']=checked(['cargo','build','--release','--offline','--locked','--target-dir',str(target)],root,output/'packed-tool-build.log')
        stage=packed/'rust-assay';stage.mkdir();shutil.copy2(target/'release/rust-assay',stage/'rust-assay');shutil.copy2(root/'LICENSE',stage/'LICENSE')
        archive=packed/'rust-assay-linux-x64.tar.gz';tar_files(archive,[(p,'rust-assay/'+p.name) for p in stage.iterdir()])
        extract(archive,consumer/'installed');binary=consumer/'installed/rust-assay/rust-assay'
        command=[str(binary),'check',str(app/'domain'),'--json'];result['binary']=pin(binary)
    elif language=='Swift':
        archive=packed/'SwiftAssay-source.tar.gz'
        files=[(root/'Package.swift','SwiftAssay/Package.swift'),(root/'LICENSE','SwiftAssay/LICENSE')]
        for base in ['Sources','Tests']:
            files.extend((p,'SwiftAssay/'+str(p.relative_to(root))) for p in sorted((root/base).rglob('*')) if p.is_file())
        tar_files(archive,files);extract(archive,consumer/'installed')
        scratch=consumer/'swift-build'
        result['consumerBuild']=checked(['swift','build','--package-path',str(consumer/'installed/SwiftAssay'),'--scratch-path',str(scratch),'-c','release','--jobs','2','--skip-update'],consumer,output/'consumer-build.log')
        result['installedSources']=[pin(p) for p in sorted((consumer/'installed/SwiftAssay').rglob('*')) if p.is_file()]
        binary=scratch/'release/swift-assay';command=[str(binary),'check',str(app/'domain'),'--json'];result['binary']=pin(binary)
    else:
        result['producerBuild']=checked([str(root/'kotlin-assay'),'--self-test'],root,output/'packed-tool-build.log')
        archive=packed/'kotlin-assay-preview.jar';shutil.copy2(root/'build/kotlin-assay.jar',archive)
        installed=consumer/'installed';installed.mkdir();binary=installed/'kotlin-assay.jar';shutil.copy2(archive,binary)
        lock=json.loads((root/'toolchain.lock.json').read_text());home=Path(lock['compilerHome'])
        deps=[Path(lock['persistentCollectionsJar'])]+[Path(lock[key]['jar']) for key in ['kotlinx-serialization-core-jvm','kotlinx-serialization-json-jvm']]
        cp=os.pathsep.join(map(str,[binary,*sorted((home/'lib').glob('*.jar')),*deps]))
        (app/'tests').mkdir();shutil.copy2(harness,app/'tests/Main.kt')
        run_tests=app/'run-tests.py'
        run_tests.write_text('import subprocess;from pathlib import Path;root=Path(__file__).resolve().parent;classpath=str(root/".kotlinassay/compiled.jar")+'+repr(os.pathsep+str(home/'lib/kotlin-stdlib.jar'))+';raise SystemExit(subprocess.run(["java","-cp",classpath,"playground.expenseguard.tests.MainKt","expanded"]).returncode)\n')
        write(app/'.kotlinassay.json',{'schema':'kotlin-assay-policy/0.1','profile':'strict-syntax/0.1','domainRoots':['domain'],'boundaryRoots':['tests'],'requiredCommands':[['python3','run-tests.py']]})
        command=['env','KOTLIN_ASSAY_COMPILER='+str(home/'bin/kotlinc'),'KOTLIN_ASSAY_TOOLCHAIN_SHA256='+sha((root/'toolchain.lock.json').read_bytes()),'java','-cp',cp,'kotlinassay.adapters.CliKt','verify',str(app)]
        result['binary']=pin(binary);result['declaredToolchainDependencies']=[str(home),*map(str,deps)]
        result['runtimeDependencies']=[pin(p) for p in [*sorted((home/'lib').glob('*.jar')),*deps]]
    result['archive']=pin(archive)
    result['verification']=checked(command,consumer,output/'consumer-verification.log')
    parsed=json.loads(result['verification']['stdout'])
    verdict=parsed.get('verdict');kind=verdict.get('kind') if isinstance(verdict,dict) else verdict
    if kind!='Pass':raise ValueError('Packed checker did not grant its documented scoped Pass')
    if language=='Kotlin':
        result['nativeAcceptanceLog']=pin(app/'.kotlinassay/command-0.log')
        result['nativeCompiledApplication']=pin(app/'.kotlinassay/compiled.jar')
    result['reportedCheckerVerdict']=verdict
    result['checkerReceipt']=parsed
    result['applicationSource']=pin(copied)
    if any(str(root/'src') in arg or str(root/'Sources') in arg or str(root/'kotlin-assay')==arg for arg in command):raise ValueError('Consumer execution references producer source')
    result['completed']=True
    return result
