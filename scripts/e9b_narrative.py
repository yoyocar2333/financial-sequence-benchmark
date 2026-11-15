"""Deterministic narrative accounting; editorial evidence is distinct from scientific tests."""
import argparse,json,re
from pathlib import Path

PATTERNS={
 'claim_denial':r'\bwe do not claim\b',
 'failed_establishment':r'\b(?:does|do) not (?:establish|demonstrate|identify|imply|certify|claim|provide|prove)\b',
 'nonconfirmation_or_equivalence':r'\bnot (?:independently (?:confirmed|validated)|a causal|an independently|a newly preregistered|a representative|certified|equivalent to|proof of|a new financial|a claim of|a registered|a confirmed|a guarantee|an equivalence)\b',
 'inability_disclaimer':r'\b(?:cannot|can not) (?:identify|establish|claim|support|certify|supply|replace|turn|be substituted|be safely)\b',
 'nonexecution':r'\b(?:not|never) (?:executed|trained|obtained|registered|fitted|run)\b',
 'administrative_status':r'\bE8b remains NOT_READY\b',
 'no_new_or_confirmation':r'\bno (?:new financial|new neural|independent confirmation|historical analyst)\b'
}

def body(text):
 text=text.split('# Abstract',1)[1];text=re.split(r'# (?:Appendix A\.|Supplementary Material|References)',text,maxsplit=1)[0]
 return '\n'.join(l for l in text.splitlines() if not l.startswith(('#','|','![')))
def count(text):
 x=body(text);sentences=[s.strip() for s in re.split(r'(?<=[.!?])\s+(?=[A-Z])',x) if s.strip()];matches=[]
 for sentence in sentences:
  families=[k for k,p in PATTERNS.items() if re.search(p,sentence,re.I)]
  if families:matches.append(dict(sentence=sentence,families=families))
 return dict(English_body_whitespace_words=len(x.split()),matched_defensive_sentences=len(matches),negation_tokens=len(re.findall(r'\b(?:not|cannot|never)\b',x,re.I)),matches=matches)

def main(out):
 before=(out/'baseline/PAPER_DRAFT.md').read_text();after=(out/'PAPER_DRAFT.md').read_text();a=count(before);b=count(after)
 evidence=dict(scope='English Abstract through Conclusion/Integrity; tables, headings, images, bibliography, appendices and Chinese abstract excluded',method='Fixed phrase-family detector, not a claim to classify every negation or to judge scientific validity',patterns=PATTERNS,before=a,after=b,defensive_sentence_reduction=a['matched_defensive_sentences']-b['matched_defensive_sentences'],negation_token_reduction=a['negation_tokens']-b['negation_tokens'])
 (out/'audits/narrative_counts.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
 pairs=[
 ('We do not claim to invent','The study makes three contributions.','以三項完成的比較與診斷取代方法發明的否定聲明；新穎性範圍留在相關研究定位'),
 ('No new neural early-fusion model is claimed','The accounting study fixes T51 as P.','Methods直接說明凍結價格預測與F來源；神經樣本gate及擬合紀錄移至補充方法'),
 ('This does not causally quantify','The original technical-feature comparison shows','保留QQQ對照及完整效果；因果與容量限制整合至Limitations'),
 ('not the standard error of a market effect','Complexity changes also matter.','結果以寬度與穩定性為主；seed的統計單位在Methods集中解釋'),
 ('arithmetic, not a causal decomposition','For price forecast p, fundamental forecast f','以可核對的損失恆等式、raw/calibrated對照及分箱餘項補足機制分析'),
 ('A significant exception must be retained','Ranking supplies complementary evidence.','直接方向顯著差異保留數字、家族與F-only端點，改用實際比較的解釋'),
 ('It must not be suppressed','The secondary hierarchical S-versus-P benefit remains','完整保留次要p=.028、延遲敏感度與同狀態排序；刪除反覆的寫作防衛'),
 ('No cross-stage aggregate p-value','The principal label compares','以明確標籤與cohort表統一可比性；執行沿革移至S1'),
 ('E8b remains NOT_READY','The financial prototype covers','正文呈現實際歷史證據缺口；E8b行政閘門狀態留在Gap Register'),
 ('This draft has been checked computationally','The market population consists','技術文件與人工／同儕審查紀錄移至補充檢查，正文僅保留推論限制'),
 ('The E7a document is a frozen candidate protocol','For future work, the most informative comparison','凍結／登錄行政沿革移S6；正文提出由結果支持的具體比較'),
 ('The contribution is an evidence-linked audit','The experiments show why the source','結論改為回答表示、收縮、初始化與新聞訊號的實際結果')]
 def para(text,needle):
  found=[p for p in text.split('\n\n') if needle in p]
  assert found,(needle,'missing passage')
  return found[0]
 blocks=['# E9b：論述修訂前後對照','\n## 可重算的文字計數',f"固定規則辨識的防禦句：**{a['matched_defensive_sentences']} → {b['matched_defensive_sentences']}**，減少 **{evidence['defensive_sentence_reduction']}** 句。not／cannot／never token：**{a['negation_tokens']} → {b['negation_tokens']}**。此為明示規則的文字指標；負面實驗結論仍保留，不能把所有否定詞一律當作缺點。",'範圍與逐句匹配見 `audits/narrative_counts.json`。排除中摘、表格、圖像、標題、References及附錄，以免新增引用或移動工程紀錄扭曲對照。']
 for i,(old,new,reason) in enumerate(pairs,1):
  p=para(before,old);q=para(after,new)
  blocks.extend([f'\n## {i}. {reason}','**E9a 原段落**\n\n> '+p.replace('\n','\n> '),'**E9b 修訂段落**\n\n> '+q.replace('\n','\n> ')])
 blocks.append('\n## 保留而非刪除的必要限制\n\n2024–2025重複探索、兩股及季度更新依賴、原H1/H3校正結果、新聞次要顯著與時間敏感度、原直接方向F-only結果、PIT歷史版本缺口及2026誠信揭露均保留。新增C6的正向結果、冷啟動位置與block120敏感性一併呈現。原始效果量、p-value及CI無改寫。')
 (out/'BEFORE_AFTER_NARRATIVE_AUDIT.md').write_text('\n\n'.join(blocks)+'\n');print('Narrative',a['matched_defensive_sentences'],'->',b['matched_defensive_sentences'],'negations',a['negation_tokens'],'->',b['negation_tokens'])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)
