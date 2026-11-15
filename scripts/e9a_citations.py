"""Resolve bibliography against retained DOI metadata and documented primary pages."""
import json,csv
from pathlib import Path

def main(out):
 if (out/'MANUSCRIPT_VERSION.json').exists() and __import__('json').loads((out/'MANUSCRIPT_VERSION.json').read_text()).get('stage')=='E9b':
  from e9b_citations import main as current; return current(out)
 records=json.loads((out/'literature/verified_doi_records.json').read_text())
 for r in records:
  if r['id']=='R18':
   r.update(title='A Simple Sequentially Rejective Multiple Test Procedure',authors=[{'given':'Sture','family':'Holm'}],venue='Scandinavian Journal of Statistics',volume='6',issue='2',pages='65–70',doi='',url='https://www.jstor.org/stable/4615733',status='PRIMARY_ISSUE_VERIFIED_DOI_NOT_CLAIMED',resolution='JSTOR issue i412579 verifies author, title and pages. Candidate DOI 10.2307/4615733 did not resolve; stable identifier is not asserted to be a DOI.',primary_verification_url='https://www.jstor.org/stable/i412579')
  if r['id']=='R27':
   r.update(title='XGBoost: A Scalable Tree Boosting System',status='DOI_AND_AUTHOR_PRIMARY_PAGE_VERIFIED',resolution='Crossref short title XGBoost; arXiv author record verifies full title/authors and explicitly links the same ACM DOI.',primary_verification_url='https://arxiv.org/abs/1603.02754')
 extra=[
 ('R07','FinBERT: Financial Sentiment Analysis with Pre-trained Language Models',2019,'Dogu Araci','arXiv preprint arXiv:1908.10063','10.48550/arXiv.1908.10063','https://arxiv.org/abs/1908.10063'),
 ('R14','On Calibration of Modern Neural Networks',2017,'Chuan Guo; Geoff Pleiss; Yu Sun; Kilian Q. Weinberger','Proceedings of Machine Learning Research 70, 1321–1330','','https://proceedings.mlr.press/v70/guo17a.html'),
 ('R15','On Over-fitting in Model Selection and Subsequent Selection Bias in Performance Evaluation',2010,'Gavin C. Cawley; Nicola L. C. Talbot','Journal of Machine Learning Research 11(70), 2079–2107','','https://www.jmlr.org/papers/v11/cawley10a.html'),
 ('R26','Mamba: Linear-Time Sequence Modeling with Selective State Spaces',2023,'Albert Gu; Tri Dao','arXiv:2312.00752; author preprint, version 2 dated 2024-05-31','10.48550/arXiv.2312.00752','https://arxiv.org/abs/2312.00752'),
 ('R28','LightGBM: A Highly Efficient Gradient Boosting Decision Tree',2017,'Guolin Ke; Qi Meng; Thomas Finley; Taifeng Wang; Wei Chen; Weidong Ma; Qiwei Ye; Tie-Yan Liu','Advances in Neural Information Processing Systems 30','','https://proceedings.neurips.cc/paper_files/paper/2017/hash/6449f44a102fde848669bdd9eb6b76fa-Abstract.html'),
 ('R30','FinMultiTime: A Four-Modal Bilingual Dataset for Financial Time-Series Analysis',2025,'Wenyan Xu; Dawei Xiang; Yue Liu; Xiyu Wang; Yanxiang Ma; Liang Zhang; Shu Hu; Chang Xu; Jiaheng Zhang','arXiv:2506.05019; version 2 dated 2025-09-11; under review, not treated as peer-reviewed evidence','10.48550/arXiv.2506.05019','https://arxiv.org/abs/2506.05019')]
 for id,title,year,authors,venue,doi,url in extra:
  records.append(dict(id=id,title=title,year_cited=year,authors=[{'literal':a} for a in authors.split('; ')],venue=venue,doi=doi,url=url,status='PRIMARY_RECORD_VERIFIED',checked_date='2026-11-14',primary_verification_url=url,reading_scope='Primary author/publisher record and abstract; no claim of full-text systematic review',raw_HTTP_body_retained=False))
 records.sort(key=lambda r:r['id'])
 assert len(records)==32
 (out/'literature/citation_catalog.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
 lines=[];rows=[]
 for r in records:
  author='; '.join(a.get('literal',a.get('family','')+', '+a.get('given','')) for a in r['authors'])
  detail=r.get('venue','')
  if r.get('volume'):detail+=' '+r['volume']+('('+r['issue']+')' if r.get('issue') else '')
  if r.get('pages'):detail+=', '+r['pages']
  link=('https://doi.org/'+r['doi']) if r.get('doi') else r['url']
  lines.append(f"[{r['id']}] {author} ({r['year_cited']}). {r['title']}. {detail}. {link}")
  rows.append(dict(reference_id=r['id'],year=r['year_cited'],citation_title=r['title'],DOI=r.get('doi',''),primary_url=r.get('primary_verification_url',r['url']),status=r['status'],checked_date='2026-11-14',scope=r.get('reading_scope',''),notes=r.get('resolution','')))
 (out/'literature/REFERENCES.md').write_text('\n\n'.join(lines)+'\n')
 with (out/'literature/citation_audit.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)
