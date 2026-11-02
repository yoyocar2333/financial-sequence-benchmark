"""Genuine fixed FinBERT and upstreamV1spaCy, no prices or future labels read."""
import argparse
import gzip
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import traceback
import numpy as np
import pandas as pd
from e4b_core import ROOT,OUT,FINBERT_REV,sha,dump,now


def assemble(out):
    apple=pd.read_csv(out/'raw/apple_newsroom_articles_recollected.csv',keep_default_na=False)
    old=pd.read_csv(out/'inputs/AAPL_news_historical_smoke.csv',keep_default_na=False)
    rows=[]
    sources=[('apple_newsroom_recollected',apple),('phase7a_original_summary',old)]
    if (out/'audits/fnspid_bounded_recovery.json').exists():
        for ticker in ('AAPL','TSLA'):
            fn=pd.read_csv(out/'raw'/f'FNSPID_{ticker}_contiguous_block_2012_2025.csv',keep_default_na=False)
            normalized=pd.DataFrame({'article_id':fn.Url,'ticker':ticker,'timestamp':fn.Date.str.replace(' UTC','+00:00',regex=False),
                'title':fn.Article_title,'content':fn.Article,'source':fn.Publisher,'url':fn.Url})
            assert normalized.content.eq('').all()
            sources.append(('fnspid_bounded_headlines',normalized))
    for source,frame in sources:
        for r in frame.to_dict('records'):
            pub=r.get('publication_date') if source.startswith('apple') else r['timestamp'][:10]
            if pub>'2025-12-31':raise ValueError('Post2025 article excluded before text inference')
            text_hash=hashlib.sha256((r['title']+'\n\n'+r['content']).encode()).hexdigest()
            document_id=hashlib.sha256(r['url'].encode()).hexdigest()[:24]
            version_id=hashlib.sha256((document_id+'|'+text_hash+'|'+source+('|' + r['ticker'] if source.startswith('fnspid') else '')).encode()).hexdigest()
            rows.append({'record_id':version_id,'document_id':document_id,'original_article_id':r['article_id'],'ticker':r['ticker'],
                'source_family':source,'publisher':r['source'],'url':r['url'],'publication_date':pub,
                'published_utc':None if source.startswith('apple') else pd.Timestamp(r['timestamp']).isoformat(),
                'timestamp_precision':'date_only' if source.startswith('apple') else 'publisher_timestamp_only',
                'retrieved_utc':r.get('retrieved_utc') or None,'historical_available_utc':None,'historical_text_revision_verified':False,
                'representation':'title_plus_full_prose' if source.startswith('apple') else 'title_only_no_body' if source.startswith('fnspid') else 'title_plus_provider_summary',
                'title':r['title'],'content':r['content'],'text_sha256':text_hash,'content_characters':len(r['content']),
                'http_sha256':r.get('http_sha256') or None,'record_origin':r.get('record_origin') or 'E4A_preserved_Phase7A_original',
                'strict_PIT_eligible':False,'license_scope':'Apple copyrighted/private research, no public redistribution grant' if source.startswith('apple') else 'FNSPID card CC BY-NC4.0; publisher rights separate' if source.startswith('fnspid') else 'original user-supplied provider summary; redistribution unverified'})
    data=pd.DataFrame(rows);assert data.record_id.is_unique
    data['exact_text_cluster']=data.text_sha256
    data.to_csv(out/'datasets/news_unified.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    data.drop(columns=['title','content']).to_csv(out/'datasets/news_unified_manifest.csv',index=False)
    return data


def views(row):
    return [('title',row.title)] if row.representation=='title_only_no_body' else [('title',row.title),('full',row.title+'\n\n'+row.content)]


def run(out,device):
    data=assemble(out)
    import torch
    from transformers import AutoTokenizer,AutoModelForSequenceClassification
    torch.set_num_threads(2)
    if device=='cuda':
        if not torch.cuda.is_available():raise RuntimeError('CUDA unavailable; no implicit fallback')
        torch.cuda.set_per_process_memory_fraction(.10,device=0)
    location=json.loads((out/'audits/finbert_location.json').read_text());path=Path(location['path'])
    tokenizer=AutoTokenizer.from_pretrained(path,local_files_only=True,trust_remote_code=False)
    model=AutoModelForSequenceClassification.from_pretrained(path,local_files_only=True,trust_remote_code=False).to(device).eval()
    labels={str(v).lower():int(k) for k,v in model.config.id2label.items()}
    assert set(labels)=={'positive','negative','neutral'}
    registry={'model':'ProsusAI/finbert','revision':FINBERT_REV,'device':device,'dtype':'float32','threads':2,'batch_size':8,
        'inference_started_utc':now(),'text_input_only':True,'prices_or_labels_read':False,'GPU_training':False,
        'chunking':'nonoverlapping510 content tokens +CLS/SEP; pool original-token weighted; all tokens consumed',
        'versions':{n:importlib.metadata.version(n) for n in ('torch','transformers','tokenizers','spacy','en-core-web-sm','numpy')},
        'model_files':{p.name:sha(p) for p in path.iterdir() if p.is_file()},'news_sha256':sha(out/'datasets/news_unified.csv.gz')}
    dump(out/'features/model_registry.json',registry)
    cache_path=out/'features/finbert_chunks.jsonl';cache={}
    if cache_path.exists():
        for line in cache_path.read_text().splitlines():
            z=json.loads(line);cache[(z['record_id'],z['source'],z['chunk'])]=z
    lengths={};chunks={};tasks=[]
    for r in data.itertuples():
        for src,text in views(r):
            ids=tokenizer(text,add_special_tokens=False,truncation=False,verbose=False)['input_ids']
            if not ids:raise ValueError('Empty token input')
            parts=[ids[i:i+510] for i in range(0,len(ids),510)];assert sum(map(len,parts))==len(ids)
            lengths[(r.record_id,src)]=len(ids);chunks[(r.record_id,src)]=len(parts)
            for j,part in enumerate(parts):
                key=(r.record_id,src,j);token_sha=hashlib.sha256(np.asarray(part,dtype='<i8').tobytes()).hexdigest()
                if key in cache:
                    if cache[key]['token_sha256']!=token_sha:raise RuntimeError('Cached token version changed')
                else:tasks.append((key,[tokenizer.cls_token_id,*part,tokenizer.sep_token_id],len(part),token_sha))
    tasks.sort(key=lambda x:len(x[1]));start=time.monotonic()
    print('FINBERT articles',len(data),'chunks',len(tasks),'device',device,flush=True)
    with torch.inference_mode(),cache_path.open('a') as handle:
        for begin in range(0,len(tasks),8):
            batch=tasks[begin:begin+8];width=max(len(x[1]) for x in batch)
            ids=torch.full((len(batch),width),tokenizer.pad_token_id,dtype=torch.long,device=device);mask=torch.zeros_like(ids)
            for j,(_,tokens,_,_) in enumerate(batch):ids[j,:len(tokens)]=torch.tensor(tokens,device=device);mask[j,:len(tokens)]=1
            p=torch.softmax(model(input_ids=ids,attention_mask=mask).logits,dim=-1).cpu().numpy()
            for task,pp in zip(batch,p):
                key,_,n,token_sha=task;row={'record_id':key[0],'source':key[1],'chunk':key[2],'tokens':n,'token_sha256':token_sha,
                    'model_revision':FINBERT_REV,**{name:float(pp[idx]) for name,idx in labels.items()}}
                cache[key]=row;handle.write(json.dumps(row)+'\n')
            handle.flush()
            if begin==0 or (begin//8)%20==0 or begin+8>=len(tasks):print('FINBERT',min(begin+8,len(tasks)),'/',len(tasks),'seconds',round(time.monotonic()-start,1),flush=True)
            if device=='cuda':time.sleep(.05)
    if device=='cuda':torch.cuda.synchronize()
    dump(out/'audits/finbert_inference.json',{'status':'PASSED','article_entity_version_records':len(data),'feature_views':len(lengths),
        'chunk_rows':len(cache),'truncated_tokens':0,'seconds':time.monotonic()-start,'GPU_used':device=='cuda',
        'max_allocator_MiB':torch.cuda.max_memory_allocated()/2**20 if device=='cuda' else 0,'completed_utc':now()})
    # Free our GPU context before CPU syntactic parsing. Never touch other processes.
    model.to('cpu');del model
    if device=='cuda':torch.cuda.empty_cache()
    module_path=out/'code/upstream_event_extraction/extractors.py'
    spec=importlib.util.spec_from_file_location('e4b_upstream_events',module_path);mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
    extractor=mod.SpacyExtractor('en_core_web_sm')
    infer_path=out/'code/upstream_infer_apple_public.py';spec2=importlib.util.spec_from_file_location('e4b_original_infer',infer_path)
    # Its only event dependency is satisfied by the pinned upstream package.
    import types
    pkg=types.ModuleType('event_extraction');pkg.__path__=[str(module_path.parent)];sys.modules['event_extraction']=pkg;sys.modules['event_extraction.extractors']=mod
    original=importlib.util.module_from_spec(spec2);spec2.loader.exec_module(original)
    feature_rows=[];quality=[]
    with gzip.open(out/'features/event_records_v1.jsonl.gz','wt') as handle:
        for i,r in enumerate(data.itertuples(),1):
            for src,_ in views(r):
                ev=[]
                for text in ([r.title] if src=='title' else [r.title,r.content]):ev.extend(extractor.extract(text,'Tesla' if r.ticker=='TSLA' else 'Apple'))
                vector,weight,n=original.event_features(ev)
                parts=[cache[(r.record_id,src,j)] for j in range(chunks[(r.record_id,src)])];total=sum(z['tokens'] for z in parts)
                probs={name:sum(z[name]*z['tokens'] for z in parts)/total for name in labels}
                assert abs(sum(probs.values())-1)<1e-5 and all(0<=v<=1 for v in probs.values())
                feature_rows.append({'record_id':r.record_id,'source':src,'text_sha256':r.text_sha256,'publication_date':r.publication_date,
                    'primary_view':src==('title' if r.representation=='title_only_no_body' else 'full'),
                    'finbert_tokens':total,'finbert_chunks':len(parts),'truncated_tokens':0,'event_records':n,'article_weight':weight,
                    **{'sent_'+k:v for k,v in probs.items()},**vector})
                for e in ev:
                    handle.write(json.dumps({'record_id':r.record_id,'source':src,**e})+'\n')
                good=[e for e in ev if e['extraction_status']=='ok']
                quality.append({'record_id':r.record_id,'source':src,'syntactic_records':len(good),
                    'missing_actor_or_object':sum(not e['actor'] or not e['object'] for e in good),
                    'target_role_other_or_unknown':sum(e['target_role'] in ('other','unknown') for e in good),
                    'arguments_over20_words':sum(len(e['actor'].split())>20 or len(e['object'].split())>20 for e in good),
                    'independent_human_gold_available':False,'event_records_are_unique_financial_events':False})
            if i%25==0 or i==len(data):print('SPACY',i,'/',len(data),flush=True)
    pd.DataFrame(feature_rows).to_csv(out/'features/article_features.csv',index=False)
    pd.DataFrame(quality).to_csv(out/'tables/event_extraction_quality_flags.csv',index=False)
    # Join the original Gemini only to its exact original text, never a new page body.
    gem=pd.read_csv(out/'inputs/AAPL_llm_historical_resume.csv',keep_default_na=False)
    gem['text_sha256']=[hashlib.sha256((r.title+'\n\n'+r.content).encode()).hexdigest() for r in gem.itertuples()]
    gem=gem.drop(columns=['title','content']);mapping=data[data.source_family.eq('phase7a_original_summary')][['record_id','original_article_id','text_sha256']]
    merged=gem.merge(mapping,left_on=['article_id','text_sha256'],right_on=['original_article_id','text_sha256'],validate='one_to_one')
    assert len(merged)==36
    merged.to_csv(out/'features/gemini_original36_exact_version_join.csv',index=False)
    pooled=pd.DataFrame(feature_rows).query('primary_view').merge(merged[['record_id','sentiment','event_type','confidence','market_relevance']],on='record_id',how='left',validate='one_to_one')
    pooled.to_csv(out/'features/unified_finbert_events_gemini.csv',index=False)
    dump(out/'features/COMPLETE.json',{'status':'COMPLETE','articles':len(data),'FinBERT_feature_rows':len(feature_rows),'Gemini_exact_version_matches':36,
        'source_program':'upstreamV1','nlp_model':'en_core_web_sm3.8.0','no_human_extraction_accuracy_claim':True,
        'files':{str(p.relative_to(out)):sha(p) for folder in ('features',) for p in (out/folder).glob('*') if p.is_file() and p.name!='COMPLETE.json'}})
    print('FEATURES COMPLETE',len(data),'articles',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT);p.add_argument('--device',choices=['cpu','cuda'],default='cpu');a=p.parse_args()
    try:run(a.out.resolve(),a.device)
    except Exception:
        dump(a.out/'audits/feature_failure.json',{'status':'STOPPED','traceback':traceback.format_exc(),'automatic_retry':False});raise
