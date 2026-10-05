"""Reviewed import from Prospero's Study: inspect, review, then import."""
from fastapi import APIRouter, Request

from companion.imports import study
from companion.models import StudyCharacter, StudyImport, StudyWorkspace

router = APIRouter(prefix='/api/import/study')


def db(request: Request):
    return request.app.state.database


@router.get('')
def list_imports(request: Request):
    return {'imports': study.imports(db(request))}


@router.post('/inspect')
def inspect(request: Request, body: StudyWorkspace):
    return study.inspect(db(request), body.path)


@router.post('/review')
def review(request: Request, body: StudyCharacter):
    return study.review(db(request), body.path, body.character_id)


@router.post('')
def run_import(request: Request, body: StudyImport):
    return study.run(db(request), body)
