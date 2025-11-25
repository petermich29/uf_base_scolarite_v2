import pandas as pd
from sqlalchemy.orm import Session
from models import (
    Cycle, Niveau, Semestre, ModeInscription,
    SessionExamen, TypeFormation, AnneeUniversitaire
)

# -------------------------------
# Génération des ID
# -------------------------------
def _generate_id(prefix: str, index: int) -> str:
    length_map = {
        'INST': 4, 'DOMA': 2, 'COMP': 4, 'MENT': 6, 'PARC': 7,
        'CYCL': 1, 'NIVE': 2, 'SEME': 2, 'SESS': 1,
        'TYPE': 2, 'ANNE': 4, 'MODE': 3,
    }

    format_length = length_map[prefix]
    if format_length == 1:
        formatted = f"{index:d}"
    else:
        formatted = format(index, f"0{format_length}d")

    return f"{prefix}_{formatted}"

# -------------------------------
# Génération années universitaires
# -------------------------------
def _generate_annee_data(start_year: int, end_year: int) -> list:
    out = []
    for i in range(end_year - start_year + 1):
        start = start_year + i
        out.append({
            "annee": f"{start}-{start+1}",
            "ordre_annee": i,
            "description": f"Année académique {start}-{start+1}"
        })
    return out

# -------------------------------
# Importation des références fixes
# -------------------------------
def import_fixed_references(session: Session, start_year=2021, end_year=2026):
    print("\n--- Importation des données fixes ---")

    # 1. Cycles
    cycles = [('L', 'Licence'), ('M', 'Master'), ('D', 'Doctorat')]
    for i, (code, label) in enumerate(cycles, start=1):
        session.merge(Cycle(
            Cycle_id=_generate_id("CYCL", i),
            Cycle_code=code,
            Cycle_label=label
        ))

    # 2. Niveaux + semestres
    niveau_sem_map = {
        'L1': ('L', ['S01', 'S02']),
        'L2': ('L', ['S03', 'S04']),
        'L3': ('L', ['S05', 'S06']),
        'M1': ('M', ['S07', 'S08']),
        'M2': ('M', ['S09', 'S10'])
    }

    niv_i = sem_i = 0
    cycle_map = {c: _generate_id("CYCL", i) for i, (c, _) in enumerate(cycles, start=1)}

    for niv_code, (cyc, semestres) in niveau_sem_map.items():
        niv_i += 1
        niv_id = _generate_id("NIVE", niv_i)
        session.merge(Niveau(
            Niveau_id=niv_id,
            Niveau_code=niv_code,
            Niveau_label=niv_code,
            Cycle_id_fk=cycle_map[cyc]
        ))

        for s in semestres:
            sem_i += 1
            session.merge(Semestre(
                Semestre_id=_generate_id("SEME", sem_i),
                Semestre_code=f"{niv_code}_{s}",
                Semestre_numero=s,
                Niveau_id_fk=niv_id
            ))

    # 3. Mode inscription
    modes = [('CLAS', 'Classique'), ('HYB', 'Hybride')]
    for i, (code, label) in enumerate(modes, start=1):
        session.merge(ModeInscription(
            ModeInscription_id=_generate_id("MODE", i),
            ModeInscription_code=code,
            ModeInscription_label=label
        ))

    # 4. Sessions examen
    sessions = [('N', 'Normale'), ('R', 'Rattrapage')]
    for i, (c, lab) in enumerate(sessions, start=1):
        session.merge(SessionExamen(
            SessionExamen_id=_generate_id("SESS", i),
            SessionExamen_code=c,
            SessionExamen_label=lab
        ))

    # 5. Types formation
    formations = [
        ('FI', 'Formation Initiale', 'Formation classique à temps plein'),
        ('FC', 'Formation Continue', 'Pour professionnels'),
    ]
    for i, (c, l, d) in enumerate(formations, start=1):
        session.merge(TypeFormation(
            TypeFormation_id=_generate_id("TYPE", i),
            TypeFormation_code=c,
            TypeFormation_label=l,
            TypeFormation_description=d
        ))

    # 6. Années universitaires
    for i, a in enumerate(_generate_annee_data(start_year, end_year), start=1):
        session.merge(AnneeUniversitaire(
            AnneeUniversitaire_id=_generate_id("ANNE", i),
            AnneeUniversitaire_annee=a["annee"],
            AnneeUniversitaire_ordre=a["ordre_annee"],
            AnneeUniversitaire_description=a["description"]
        ))

    session.commit()
    print("✅ Données fixes importées.")
