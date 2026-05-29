from typing import Sequence
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..models.persona import Persona
from ..views.persona import PersonaCreate, PersonaUpdate
from .errors import PersonaNotFoundError, EmailAlreadyExistsError

from sqlalchemy import or_, text, func

from sqlalchemy import or_
import csv
from io import StringIO

def create_persona(db: Session, payload: PersonaCreate) -> Persona:
    """Create a Persona ensuring unique email."""
    # Optimistic check; DB unique constraint is the final guard
    if db.query(Persona).filter(Persona.email == payload.email).first():
        raise EmailAlreadyExistsError()
    obj = Persona(
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        phone=payload.phone,
        birth_date=payload.birth_date,
        is_active=payload.is_active,
        notes=payload.notes,
    )
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        # Catch race conditions on unique email
        raise EmailAlreadyExistsError() from e
    db.refresh(obj)
    return obj


def list_personas(db: Session, skip: int = 0, limit: int = 100) -> Sequence[Persona]:
    """Return paginated list of Personas."""
    return db.query(Persona).offset(skip).limit(limit).all()


def get_persona(db: Session, persona_id: int) -> Persona:
    """Return Persona by ID or raise if not found."""
    obj = db.query(Persona).filter(Persona.id == persona_id).first()
    if not obj:
        raise PersonaNotFoundError()
    return obj


def update_persona(db: Session, persona_id: int, payload: PersonaUpdate) -> Persona:
    """Update Persona partially, enforcing unique email."""
    obj = db.query(Persona).filter(Persona.id == persona_id).first()
    if not obj:
        raise PersonaNotFoundError()

    data = payload.model_dump(exclude_unset=True)
    if "email" in data and data["email"] != obj.email:
        if db.query(Persona).filter(Persona.email == data["email"], Persona.id != persona_id).first():
            raise EmailAlreadyExistsError()

    for field, value in data.items():
        setattr(obj, field, value)

    db.add(obj)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise EmailAlreadyExistsError() from e
    db.refresh(obj)
    return obj


def delete_persona(db: Session, persona_id: int) -> None:
    """Delete Persona by ID or raise if not found."""
    obj = db.query(Persona).filter(Persona.id == persona_id).first()
    if not obj:
        raise PersonaNotFoundError()
    db.delete(obj)
    db.commit()

from faker import Faker
import random

fake = Faker("es_CO")

def poblar_personas(db, cantidad):

    for _ in range(cantidad):

        persona = Persona(
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=f"{fake.user_name()}@{random.choice(['gmail.com','outlook.com','hotmail.com'])}",
            phone=fake.phone_number(),
            birth_date=fake.date_of_birth(),
            is_active=random.choice([True, False]),
            notes=fake.text(max_nb_chars=100)
        )

        db.add(persona)

    db.commit()

    return {
    "message": f"{cantidad} personas creadas correctamente"
}

def reset_personas(db: Session) -> dict:
    """Elimina todos los registros de la tabla personas."""
    deleted_count = db.query(Persona).count()
    db.query(Persona).delete()
    db.commit()
    return {
        "message": "Base de datos limpiada. Se eliminaron todos los registros.",
        "deleted_count": deleted_count
    }

def estadisticas_dominios(db: Session) -> dict:
    """Retorna cuántas personas hay por dominio de correo."""
    from sqlalchemy import func
    resultados = db.query(
        func.substring_index(Persona.email, '@', -1).label("dominio"),
        func.count(Persona.id).label("cantidad")
    ).group_by("dominio").all()
    
    return {row.dominio: row.cantidad for row in resultados} 

def buscar_personas(
    db: Session,
    termino: str
):
    """
Busca personas cuyo nombre,
apellido o correo contenga
el término ingresado.
"""

    return db.query(Persona).filter(
        or_(
            Persona.first_name.ilike(f"%{termino}%"),
            Persona.last_name.ilike(f"%{termino}%"),
            Persona.email.ilike(f"%{termino}%")
        )
    ).all()


def reporte_activos(db: Session):
    """Retorna usuarios activos con proyección reducida."""
     # Filtra solo los usuarios donde is_active es True
    resultados = db.query(Persona).filter(Persona.is_active == True).all()
    # Si no hay usuarios activos, retorna lista vacía
    if not resultados:
        return []
    # Retorna solo los campos necesarios (proyección)
    # No se retorna toda la información del usuario, solo id, email, phone e is_active
    return [
        {
            "id": p.id,
            "email": p.email,
            "phone": p.phone,
            "is_active": p.is_active
        }
        for p in resultados
    ]

def estadisticas_edad(db: Session):
    """Calcula edad promedio, mínima y máxima."""
    from sqlalchemy import func
    from datetime import date
    hoy = date.today()
    
    # TIMESTAMPDIFF calcula la diferencia en años entre birth_date y la fecha actual
    # AVG calcula el promedio, MIN el mínimo y MAX el máximo
    resultado = db.query(
        func.avg(func.timestampdiff(text('YEAR'), Persona.birth_date, func.curdate())).label("promedio"),
        func.min(func.timestampdiff(text('YEAR'), Persona.birth_date, func.curdate())).label("minima"),
        func.max(func.timestampdiff(text('YEAR'), Persona.birth_date, func.curdate())).label("maxima"),
    ).filter(
        func.timestampdiff(text('YEAR'), Persona.birth_date, func.curdate()) > 0
    ).one()
    # round() redondea el promedio para retornar un número entero
    return {
        "edad_promedio": round(resultado.promedio) if resultado.promedio else 0,
        "edad_minima": resultado.minima or 0,
        "edad_maxima": resultado.maxima or 0
    }

def exportar_personas_csv(db: Session):
    """
    Exporta todas las personas en formato CSV.
    """

    personas = db.query(Persona).all()

    output = StringIO()

    writer = csv.writer(output)

    # Encabezados
    writer.writerow([
        "id",
        "first_name",
        "last_name",
        "email",
        "phone",
        "birth_date",
        "is_active",
        "notes",
        "created_at"
    ])

    # Datos
    for persona in personas:
        writer.writerow([
            persona.id,
            persona.first_name,
            persona.last_name,
            persona.email,
            persona.phone,
            persona.birth_date,
            persona.is_active,
            persona.notes,
            persona.created_at
        ])

    output.seek(0)

    return output

def bulk_desactivar(db: Session, ids: list[int]) -> dict:
    """Desactiva masivamente personas por lista de IDs."""
    # Busca cuáles IDs existen en la base de datos
    existentes = db.query(Persona).filter(Persona.id.in_(ids)).all()
    ids_existentes = [p.id for p in existentes]
    
    # Los que no existen son los que están en ids pero no en ids_existentes
    ids_no_encontrados = [i for i in ids if i not in ids_existentes]
    
    # Desactiva los que sí existen
    for persona in existentes:
        persona.is_active = False
    
    db.commit()
    
    return {
        "message": "Operación completada.",
        "desactivados": ids_existentes,
        "no_encontrados": ids_no_encontrados,
        "total_desactivados": len(ids_existentes)
    }

def cumpleanios_por_mes(db: Session, mes: int):
    """Retorna personas que cumplen años en el mes especificado."""
    from sqlalchemy import func
    return db.query(Persona).filter(
        func.month(Persona.birth_date) == mes
    ).all()