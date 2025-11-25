import sys
import database_setup

# Import des modules séparés
from fixed_references import import_fixed_references
from metadata_import import import_metadata_to_db
from inscriptions_import import import_inscriptions_to_db
from parcours_niveaux import deduce_parcours_niveaux  # si cette fonction est publique

from sqlalchemy.orm import sessionmaker
from database_setup import engine

# --- SOLUTION CRITIQUE POUR L'ENCODAGE WINDOWS ---
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    print("Encodage de sortie forcé en UTF-8.")
except Exception:
    pass


if __name__ == "__main__":
    # 1. Initialisation BDD et tables
    database_setup.init_db()

    # 2. Création de session SQLAlchemy
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    # 3. Importation des données fixes
    import_fixed_references(session)

    # 4. Importation métadonnées académiques
    import_metadata_to_db(session)

    # 5. Importation étudiants + inscriptions
    import_inscriptions_to_db(session)

    # 6. Déduction des niveaux/parcours si nécessaire
    deduce_parcours_niveaux(session)

    print("\nProcessus d'initialisation et d'importation terminé.")
