"""Read-only publication checks. No training, downloads or GPU initialization."""
import argparse,ast,csv,hashlib,json,re,subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE='e6aceaac73b4c66744f0fe9098da613de63d140f'
BLOCKED_SUFFIXES={'.pt','.pth','.ckpt','.pkl','.pickle','.joblib','.ubj','.safetensors','.onnx','.npz','.zip','.parquet','.jsonl'}
FORBIDDEN_CSV={'article_text','body','text','headline','title','summary','content','article_id','record_id','prompt','response','api_key','access_token'}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def public_files():
    result=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard'],cwd=ROOT,text=True)
    return sorted({ROOT/p for p in result.splitlines() if p and (ROOT/p).is_file()})

def check():
    errors=[];files=public_files();total=0;link_count=0;python_count=0
    secret=re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{25,}|AIza[A-Za-z0-9_-]{30,}|(?:AKIA|ASIA)[A-Z0-9]{16}|sk-[A-Za-z0-9]{24,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)')
    private_prefix='/'+'ibmnas/'
    source_rows=list(csv.DictReader((ROOT/'provenance/public_sources.csv').open()))
    for row in source_rows:
        p=ROOT/row['published_path']
        if not p.is_file() or sha(p)!=row['published_sha256']:errors.append('source digest mismatch: '+row['published_path'])
    for p in files:
        name=str(p.relative_to(ROOT));total+=p.stat().st_size
        if p.is_symlink():errors.append('symlink: '+name)
        if p.suffix in BLOCKED_SUFFIXES:errors.append('forbidden artifact: '+name)
        if any(part in {'data','outputs','logs','vendor','.cache'} or part.startswith('.venv') for part in p.relative_to(ROOT).parts):errors.append('excluded directory: '+name)
        if p.stat().st_size>2_000_000:errors.append('file exceeds2MB: '+name)
        if p.suffix=='.png':
            # PNG text chunks can carry workstation paths; scan the container bytes.
            if private_prefix.encode() in p.read_bytes():errors.append('private PNG metadata: '+name)
            continue
        try:text=p.read_text()
        except UnicodeDecodeError:errors.append('unexpected binary: '+name);continue
        if secret.search(text):errors.append('possible secret: '+name)
        home_pattern='/'+r'Users/[^/\s]+|/'+r'home/[^/\s]+'
        if private_prefix in text or re.search(home_pattern,text):errors.append('private workstation path: '+name)
        if p.suffix=='.csv':
            with p.open(newline='') as f:header=next(csv.reader(f),[])
            bad=set(header)&FORBIDDEN_CSV
            if bad:errors.append('per-article/private CSV columns '+str(sorted(bad))+': '+name)
        if p.suffix=='.py':
            python_count+=1
            try:ast.parse(text)
            except SyntaxError as e:errors.append('syntax: '+name+': '+str(e))
        if p.suffix=='.md':
            for target in re.findall(r'\]\(([^)]+)\)',text):
                target=target.split(' "',1)[0].strip('<>')
                if re.match(r'https?://|mailto:|#',target):continue
                target=target.split('#',1)[0]
                if target:
                    link_count+=1
                    if not (p.parent/target).exists():errors.append('broken link: '+name+' -> '+target)
    # Existing E0 scientific artifacts must remain byte-identical.
    for name in ['RESULTS.md','requirements.txt','notebooks/stock_market_models.ipynb']:
        original=subprocess.check_output(['git','show',BASE+':'+name],cwd=ROOT)
        if (ROOT/name).read_bytes()!=original:errors.append('legacy E0 changed: '+name)
    if total>20_000_000:errors.append('release exceeds20MB')
    result={'status':'FAILED' if errors else 'PASSED','public_files':len(files),'total_bytes':total,'copied_source_digests_verified':len(source_rows),'Python_files_parsed':python_count,'relative_links_checked':link_count,'E0_original_scientific_artifacts_unchanged':True,'raw_data_or_models_allowed':False,'errors':errors}
    if errors:raise AssertionError(json.dumps(result,ensure_ascii=False,indent=2))
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',type=Path);a=p.parse_args();result=check()
    if a.report:
        if a.report.exists():raise FileExistsError('Report output must be new')
        a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
