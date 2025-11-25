from sqlalchemy.orm import Session
from models import Inscription, Semestre, Niveau, ParcoursNiveau

# Ordre académique
ORDRE = {'L1': 1, 'L2': 2, 'L3': 3, 'M1': 4, 'M2': 5}

def deduce_parcours_niveaux(session: Session):
    print("\n--- Déduction Parcours <-> Niveaux ---")

    results = (
        session.query(
            Inscription.Parcours_id_fk,
            Niveau.Niveau_id,
            Niveau.Niveau_code
        )
        .join(Semestre, Inscription.Semestre_id_fk == Semestre.Semestre_id)
        .join(Niveau, Semestre.Niveau_id_fk == Niveau.Niveau_id)
        .distinct()
        .all()
    )

    grouped = {}
    for parc_id, niv_id, niv_code in results:
        grouped.setdefault(parc_id, []).append((niv_code, niv_id))

    inserts = []

    for parc_id, niveaux in grouped.items():
        niveaux.sort(key=lambda x: ORDRE.get(x[0], 999))

        for i, (code, niv_id) in enumerate(niveaux, start=1):
            inserts.append(ParcoursNiveau(
                ParcoursNiveau_id=f"PN_{parc_id}_{niv_id}",
                Parcours_id_fk=parc_id,
                Niveau_id_fk=niv_id,
                ParcoursNiveau_ordre=i
            ))

    session.bulk_save_objects(inserts)
    session.commit()

    print(f"✅ {len(inserts)} liaisons Parcours-Niveaux insérées.")
