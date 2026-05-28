from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..views.persona import PersonaCreate, PersonaUpdate, PersonaRead, PoblarRequest
from ..services import persona_service
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/personas", tags=["personas"])


@router.post("", response_model=PersonaRead, status_code=status.HTTP_201_CREATED)
def create_persona(persona_in: PersonaCreate, db: Session = Depends(get_db)):
    """Create a new Persona delegating to service layer."""
    # Let domain errors bubble up to global handlers
    return persona_service.create_persona(db, persona_in)


@router.get("", response_model=List[PersonaRead])
def list_personas(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """List Personas with pagination via service layer."""
    return persona_service.list_personas(db, skip=skip, limit=limit)


@router.get("/{persona_id}", response_model=PersonaRead)
def get_persona(persona_id: int, db: Session = Depends(get_db)):
    """Retrieve a Persona by ID via service layer."""
    return persona_service.get_persona(db, persona_id)


@router.put("/{persona_id}", response_model=PersonaRead)
def update_persona(persona_id: int, persona_in: PersonaUpdate, db: Session = Depends(get_db)):
    """Update an existing Persona (partial) via service layer."""
    return persona_service.update_persona(db, persona_id, persona_in)

@router.post("/poblar")
def poblar_personas(
    cantidad: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    return persona_service.poblar_personas(db, cantidad)

# IMPORTANTE: estas rutas deben ir antes de /{persona_id}
# para que FastAPI no las interprete como un ID numérico

@router.get("/reporte/activos")
def reporte_activos(db: Session = Depends(get_db)):
    """
    Retorna usuarios activos con proyección reducida.
    Solo se retornan id, email, phone e is_active para cada usuario activo.
    Filtra únicamente usuarios donde is_active = True.
    """
    return persona_service.reporte_activos(db)

@router.get("/estadisticas/edad")
def estadisticas_edad(db: Session = Depends(get_db)):
    """
    Retorna edad promedio, mínima y máxima.
    Retorna edad promedio, mínima y máxima de todos los registros.
    Usa TIMESTAMPDIFF de MySQL para calcular la edad exacta.
    """
    return persona_service.estadisticas_edad(db)

@router.delete("/reset", status_code=status.HTTP_200_OK)
def reset_personas(db: Session = Depends(get_db)):
    """Elimina todos los registros de la tabla personas."""
    return persona_service.reset_personas(db)

@router.get("/estadisticas/dominios")
def estadisticas_dominios(db: Session = Depends(get_db)):
    """Retorna cuántas personas hay por dominio de correo."""
    return persona_service.estadisticas_dominios(db)

from pydantic import BaseModel

class BulkDesactivarRequest(BaseModel):
    ids: list[int]

@router.patch("/bulk/desactivar")
def bulk_desactivar(payload: BulkDesactivarRequest, db: Session = Depends(get_db)):
    """Desactiva masivamente personas por lista de IDs."""
    if len(payload.ids) == 0 or len(payload.ids) > 100:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="La lista debe tener entre 1 y 100 IDs.")
    return persona_service.bulk_desactivar(db, payload.ids)

@router.delete("/{persona_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_persona(persona_id: int, db: Session = Depends(get_db)):
    """Delete a Persona by ID via service layer."""
    persona_service.delete_persona(db, persona_id)
    return None

@router.post("/poblar")
def poblar_personas(
    payload: PoblarRequest,
    db: Session = Depends(get_db)
):

    return persona_service.poblar_personas(
        db,
        payload.cantidad
    )

@router.get(
    "/buscar/{termino}",
    response_model=list[PersonaRead],
    summary="Buscar personas",
    description="Busca coincidencias por nombre, apellido o correo"
)
def buscar_personas(
    termino: str,
    db: Session = Depends(get_db)
):

    return persona_service.buscar_personas(
        db,
        termino
    )

@router.get("/exportar/csv")
def exportar_personas_csv(
    db: Session = Depends(get_db)
):
    """
    Exporta todas las personas en CSV descargable.
    """

    output = persona_service.exportar_personas_csv(db)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=personas.csv"
        }
    )