"""Transparent, fully offline retrieval engine (TF-IDF + grounded extractive answer).
It is NOT a generative LLM and does not call an external service.
"""
from __future__ import annotations
import re
import unicodedata
from pathlib import Path
from typing import Iterable
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

STOP={"de","la","el","los","las","en","un","una","para","por","con","es","se","que","y","a","o","del","al","su","sus","cual","cuales","como","cuanto","cuantos","donde","cuando","tener","tiene","tienen","debe","deben","puede","pueden","de","mi","me","yo","son","hay","sobre","este","esta","estas","estos","mas","si","no","ser","sean","corresponde","corresponden"}

def normalize(text:str)->str:
    text=unicodedata.normalize('NFD',text.lower())
    text=''.join(c for c in text if unicodedata.category(c)!='Mn')
    return re.sub(r'[^a-z0-9 ]',' ',text)

ALIASES={"paga":"pago","pagar":"pago","pagos":"pago","solicitan":"solicitud","solicitar":"solicitud","solicita":"solicitud","solicitarlas":"solicitud","entregar":"presentar","entrega":"presentar","entrego":"presentar","presentacion":"presentar","dias":"dias","viatico":"viaticos","criticos":"critico","sospechosa":"sospechoso"}

def tokens(text:str)->list[str]:
    words=[ALIASES.get(w,w) for w in normalize(text).split() if len(w)>2 and w not in STOP]
    return [w for w in words if w not in STOP]

def question_tokens(question:str)->list[str]:
    q=tokens(question)
    if 'solicitud' in q and 'tiempo' in q:q.extend(['anticipacion','dias'])
    if 'viaticos' in q and 'plazo' in q:q.extend(['presentar','comprobantes'])
    return q

class Retriever:
    def __init__(self, folder:Path):
        self.folder=Path(folder)
        self.sections:list[dict]=[]
        self.files:list[dict]=[]
        self.vectorizer=None
        self.matrix=None
        self.vocabulary=set()
        self.reload()

    def reload(self):
        sections=[];files=[]
        for file in sorted(self.folder.glob('*.md')):
            body=file.read_text(encoding='utf-8')
            title=next((r.lstrip('#').strip() for r in body.splitlines() if r.startswith('# ')),file.stem)
            lines=body.splitlines()
            heading='General';buffer=[]
            def flush():
                text=' '.join(buffer).strip()
                if text:
                    sections.append({'id':f'DOC-{len(sections)+1:03d}','file':file.name,'title':title,'section':heading,'text':text,'words':len(text.split())})
            for line in lines[1:]:
                if line.startswith('## '):
                    flush();heading=line[3:].strip();buffer=[]
                elif line.strip():buffer.append(line.strip())
            flush()
            files.append({'file':file.name,'title':title,'section_count':sum(s['file']==file.name for s in sections),'words':len(body.split()),'tag':'Política' if 'politica' in file.name else 'Procedimiento'})
        self.sections=sections;self.files=files
        self.vocabulary=set(w for sec in sections for w in tokens(sec["title"]+" "+sec["section"]+" "+sec["text"]))
        if sections:
            self.vectorizer=TfidfVectorizer(preprocessor=normalize,tokenizer=tokens,token_pattern=None,ngram_range=(1,2),sublinear_tf=True)
            self.matrix=self.vectorizer.fit_transform([x['title']+' '+x['section']+' '+x['text'] for x in sections])
        else: self.vectorizer=None;self.matrix=None

    def search(self,question:str,limit:int=4)->list[dict]:
        if not question.strip() or self.vectorizer is None:return []
        qwords=set(question_tokens(question))
        if not qwords or len(qwords & self.vocabulary)/len(qwords)<0.5:return []
        vector=self.vectorizer.transform([' '.join(question_tokens(question))])
        cos=cosine_similarity(vector,self.matrix)[0]
        scores=[]
        for idx,sec in enumerate(self.sections):
            sectionwords=set(tokens(sec['section']))
            overlap=len(qwords & sectionwords)/max(1,len(qwords))
            fullwords=set(tokens(sec['text']))
            textual=len(qwords & fullwords)/max(1,len(qwords))
            score=float(cos[idx])*.70 + overlap*.24 + textual*.06
            scores.append((idx,score))
        ranked=sorted(scores,key=lambda x:x[1],reverse=True)[:limit]
        return [{**self.sections[i],'score':round(score,3)} for i,score in ranked if score>0.08]

    def answer(self,question:str)->dict:
        matches=self.search(question,4)
        if not matches or matches[0]['score']<0.08:
            return {'question':question,'status':'insufficient_evidence','answer':'No encontré evidencia suficiente en los documentos disponibles para responder con confianza. Intenta reformular tu pregunta o consulta al área responsable.','confidence':0,'sources':[]}
        best=matches[0]
        sentences=re.split(r'(?<=[.!?])\s+',best['text'])
        q=set(question_tokens(question))
        def relevance(sentence:str)->float:
            words=set(tokens(sentence))
            overlap=sum(2 if len(w)>5 else 1 for w in words & q)
            return overlap / max(6,len(words)**0.35)
        ranked=sorted(sentences,key=relevance,reverse=True)
        answer=ranked[0]
        if len(answer)<55 and len(ranked)>1:answer+=' '+ranked[1]
        # Explicit evidence and URL-free references (document ID/section); no fabricated facts.
        return {'question':question,'status':'answered','answer':answer,'confidence':round(min(0.98,max(0.3,best['score']*1.5)),2),
         'sources':[{'id':m['id'],'title':m['title'],'section':m['section'],'file':m['file'],'score':m['score'],'excerpt':m['text'][:270]} for m in matches[:3]]}
