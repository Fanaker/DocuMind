import os,tempfile
from pathlib import Path
from app.retrieval import Retriever
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)

def test_index_and_grounded_answer():
    r=client.post('/api/ask',json={'question':'¿Cuántos días de vacaciones corresponden al año?'})
    assert r.status_code==200
    data=r.json()
    assert data['status']=='answered'
    assert '30 días' in data['answer']
    assert data['sources'][0]['file']=='politica_vacaciones.md'

def test_unknown_question_abstains():
    a=client.post('/api/ask',json={'question':'¿Cuál es el precio del bitcoin de ayer?'}).json()
    assert a['status']=='insufficient_evidence'
    assert a['sources']==[]

def test_knowledge_dashboard_and_evaluation():
    data=client.get('/api/overview').json()
    assert data['metrics']['docs']>=6
    assert data['metrics']['evaluated']==6
    assert data['metrics']['passed']>=4

def test_document_upload_and_validation(tmp_path, monkeypatch):
    from app import main
    backup=main.engine
    monkeypatch.setattr(main,'FOLDER',tmp_path)
    monkeypatch.setattr(main,'engine',Retriever(tmp_path))
    try:
        r=client.post('/api/documents/upload',files={'file':('manual_extra.txt',b'El sistema usa cifrado de respaldo para archivos locales.','text/plain')})
        assert r.status_code==201 and main.engine.files[0]['title']=='Manual Extra'
        assert client.post('/api/documents/upload',files={'file':('virus.exe',b'a','text/plain')}).status_code==415
        assert client.post('/api/documents/upload',files={'file':('manual_extra.txt',b'a','text/plain')}).status_code==409
    finally:
        monkeypatch.setattr(main,'engine',backup)

def test_health_and_query_validation():
    assert client.get('/health').status_code==200
    assert client.post('/api/ask',json={'question':'?'}).status_code==422
