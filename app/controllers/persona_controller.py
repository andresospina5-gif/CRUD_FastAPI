from typing import List
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database import get_db
from ..views.persona import PersonaCreate, PersonaUpdate, PersonaRead, PoblarRequest
from ..services import persona_service
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/personas", tags=["personas"])


@router.get("", response_model=List[PersonaRead])
def list_personas(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    return persona_service.list_personas(db, skip=skip, limit=limit)

@router.post("", response_model=PersonaRead, status_code=status.HTTP_201_CREATED)
def create_persona(persona_in: PersonaCreate, db: Session = Depends(get_db)):
    return persona_service.create_persona(db, persona_in)

@router.post("/poblar")
def poblar_personas(payload: PoblarRequest, db: Session = Depends(get_db)):
    return persona_service.poblar_personas(db, payload.cantidad)

@router.delete("/reset", status_code=status.HTTP_200_OK)
def reset_personas(db: Session = Depends(get_db)):
    return persona_service.reset_personas(db)

@router.get("/reporte/activos")
def reporte_activos(db: Session = Depends(get_db)):
    return persona_service.reporte_activos(db)

@router.get("/estadisticas/edad")
def estadisticas_edad(db: Session = Depends(get_db)):
    return persona_service.estadisticas_edad(db)

@router.get("/estadisticas/dominios")
def estadisticas_dominios(db: Session = Depends(get_db)):
    return persona_service.estadisticas_dominios(db)

@router.get("/exportar/csv")
def exportar_personas_csv(db: Session = Depends(get_db)):
    output = persona_service.exportar_personas_csv(db)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=personas.csv"}
    )

class BulkDesactivarRequest(BaseModel):
    ids: list[int]

@router.patch("/bulk/desactivar")
def bulk_desactivar(payload: BulkDesactivarRequest, db: Session = Depends(get_db)):
    if len(payload.ids) == 0 or len(payload.ids) > 100:
        raise HTTPException(status_code=400, detail="La lista debe tener entre 1 y 100 IDs.")
    return persona_service.bulk_desactivar(db, payload.ids)


@router.get("/buscar/{termino}", response_model=list[PersonaRead])
def buscar_personas(termino: str, db: Session = Depends(get_db)):
    return persona_service.buscar_personas(db, termino)

@router.get("/cumpleanios/mes/{numero_mes}")
def cumpleanios_por_mes(numero_mes: str, db: Session = Depends(get_db)):
    try:
        mes = int(numero_mes)
    except ValueError:
        raise HTTPException(status_code=400, detail="El mes debe ser un entero entre 1 y 12.")
    if mes < 1 or mes > 12:
        raise HTTPException(status_code=400, detail="El mes debe ser un entero entre 1 y 12.")
    return persona_service.cumpleanios_por_mes(db, mes)


@router.get("/{persona_id}", response_model=PersonaRead)
def get_persona(persona_id: int, db: Session = Depends(get_db)):
    return persona_service.get_persona(db, persona_id)

@router.put("/{persona_id}", response_model=PersonaRead)
def update_persona(persona_id: int, persona_in: PersonaUpdate, db: Session = Depends(get_db)):
    return persona_service.update_persona(db, persona_id, persona_in)

@router.delete("/{persona_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_persona(persona_id: int, db: Session = Depends(get_db)):
    persona_service.delete_persona(db, persona_id)
    return None 
