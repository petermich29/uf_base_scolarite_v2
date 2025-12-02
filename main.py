
import sys
import database_setup
from sqlalchemy.orm import sessionmaker
from database_setup import engine

# Imports des modules
from fixed_references import import_fixed_references
from metadata_import import import_metadata_to_db
from inscriptions_import import import_inscriptions_to_db
from parcours_niveaux import deduce_parcours_niveaux
from history_import import import_history_from_excel # <-- Nouvelle fonction

# --- Encodage Console Windows ---
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

if __name__ == "__main__":
    print("🚀 Démarrage de l'importation complète...")

    # 1. Initialisation
    database_setup.init_db()
    
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        # 2. Données fixes (Cycles, Années...)
        import_fixed_references(session)

        # 3. Métadonnées (Institutions -> Parcours)
        import_metadata_to_db(session)

        # 4. Inscriptions (Etudiants + Inscriptions)
        import_inscriptions_to_db(session)

        # 5. Déduction Parcours-Niveaux (depuis les relations Inscription)
        deduce_parcours_niveaux(session)

        # 6. Historiques (depuis le fichier Excel source pour avoir les libellés d'époque)
        import_history_from_excel(session)

        print("\n==================================================")
        print("✅  IMPORTATION TERMINÉE AVEC SUCCÈS")
        print("==================================================")

    except Exception as e:
        session.rollback()
        print(f"\n❌ ERREUR FATALE : {e}")
    finally:
        session.close()
