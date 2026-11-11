"""DocuMind API: upload, index, retrieve, cite and abstain when unsupported."""
from __future__ import annotations
import os
from pathlib import Path
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from .retrieval import Retriever

ROOT=Path(__file__).resolve().parents[1]
FOLDER=Path(os.getenv('DOCUMIND_KNOWLEDGE',str(ROOT/'knowledge')))
FOLDER.mkdir(parents=True,exist_ok=True)
app=FastAPI(title='DocuMind Document Assistant',version='1.0.0')
engine=Retriever(FOLDER)

EVAL=[
 ('¿Cuántos días de vacaciones corresponden al año?','30 días','politica_vacaciones.md'),
 ('¿Con cuánto tiempo se solicitan vacaciones?','15 días','politica_vacaciones.md'),
 ('¿Cuándo se paga a los proveedores?','30 días','gestion_proveedores.md'),
 ('¿Qué hago si detecto un inicio de sesión sospechoso?','seguridad@','seguridad_accesos.md'),
 ('¿Cuál es el tiempo de primera respuesta para incidentes críticos?','30 minutos','mesa_ayuda.md'),
 ('¿En qué plazo debo entregar mis viáticos?','5 días hábiles','politica_viaticos.md'),
]

def evaluation():
    results=[]
    for q,keyword,file in EVAL:
        a=engine.answer(q)
        ok=(keyword.lower() in a['answer'].lower() and bool(a['sources']) and a['sources'][0]['file']==file)
        results.append({'question':q,'expected':keyword,'passed':ok,'source':file,'confidence':a['confidence']})
    return results

@app.get('/')
def index():return FileResponse(ROOT/'web'/'index.html')
@app.get('/assets/{name}')
def assets(name:str):
    if name not in ('app.css','app.js'):raise HTTPException(404)
    return FileResponse(ROOT/'web'/name)

@app.get('/health')
def health():return {'status':'ok','documents':len(engine.files),'sections':len(engine.sections)}

@app.get('/api/overview')
def overview():
    ev=evaluation()
    example=engine.answer('¿Cuántos días de vacaciones corresponden al año?')
    return {'documents':engine.files,'sections':len(engine.sections),'example':example,'evaluation':ev,
       'metrics':{'docs':len(engine.files),'sections':len(engine.sections),'evaluated':len(ev),'passed':sum(x['passed'] for x in ev)},
       'suggested':['¿Cuántos días de vacaciones corresponden?', '¿Cómo se registra un proveedor nuevo?', '¿Qué hacer ante un acceso sospechoso?', '¿Cuál es el SLA de incidentes críticos?'],
       'activity':[{'title':'Base de conocimiento indexada','detail':f'{len(engine.files)} archivos procesados','time':'Hoy, 09:40'},
                   {'title':'Evaluación offline completada','detail':f'{sum(x["passed"] for x in ev)}/{len(ev)} consultas verificadas','time':'Hoy, 09:32'},
                   {'title':'Documentos de ejemplo cargados','detail':'Políticas internas ficticias','time':'Ayer, 17:15'}]}

class Question(BaseModel):
    question:str=Field(min_length=3,max_length=500)

@app.post('/api/ask')
def ask(q:Question):return engine.answer(q.question)

@app.get('/api/documents')
def documents():return {'documents':engine.files,'sections':engine.sections}

@app.get('/api/evaluation')
def evaluate():return {'results':evaluation()}

@app.post('/api/documents/upload',status_code=201)
async def upload_document(file:UploadFile=File(...)):
    filename=Path(file.filename or '').name
    if not filename.lower().endswith(('.md','.txt')):raise HTTPException(415,'Solo Markdown o TXT')
    if not filename or filename.startswith('.'):raise HTTPException(422,'Nombre inválido')
    content=await file.read(1024*1024+1)
    if len(content)>1024*1024:raise HTTPException(413,'Tamaño máximo 1 MB')
    try: text=content.decode('utf-8')
    except UnicodeError:raise HTTPException(422,'Solo UTF-8')
    if not text.strip():raise HTTPException(422,'Documento vacío')
    if filename.lower().endswith('.txt'):
        filename=Path(filename).stem+'.md'
        text=f'# {Path(filename).stem.replace("_", " ").title()}\n\n## Contenido\n'+text
    dest=FOLDER/filename
    if dest.exists():raise HTTPException(409,'Ya existe un documento con este nombre')
    dest.write_text(text,encoding='utf-8')
    engine.reload()
    return {'status':'indexed','file':filename,'sections':len(engine.sections)}
