import pandas as pd
import numpy as np
from tqdm import tqdm
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, DataError


from models import (
    Etudiant, Inscription,
    Parcours, Semestre, AnneeUniversitaire, ModeInscription
)
from metadata_import import safe_string

def _clean_date(value):
    """Convertit les NaT, nan, None, '' en None. Retourne date python si valide."""
    if value is None:
        return None
    if isinstance(value, float) and np.isnan(value):
        return None
    if isinstance(value, str) and value.strip().lower() in ["nan", "nat", "", "none"]:
        return None

    try:
        d = pd.to_datetime(value, errors="coerce")
        if pd.isna(d):
            return None
        return d.date()
    except:
        return None

# ----------------------------
# Load + clean Excel
# ----------------------------
def _load_and_clean_inscriptions():
    import config

    try:
        df = pd.read_excel(config.INSCRIPTION_FILE_PATH)
    except:
        print("❌ ERREUR lecture fichier inscriptions.")
        return None

    df.columns = df.columns.str.lower().str.replace(" ", "_")
    df = df.where(pd.notnull(df), None)

    # Dates
    for c in ["etudiant_naissance_date", "etudiant_cin_date"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce", dayfirst=True).dt.date

    # Standardisation codes
    cols = [
        "parcours_code", "niveau_code", "semestre_numero",
        "modeinscription_label", "institution_code",
        "composante_code", "domaine_code",
        "mention_abbreviation", "etudiant_id",
        "anneeuniversitaire_annee"
    ]
    for c in cols:
        if c in df.columns:
            df[c] = df[c].astype(str).apply(safe_string)
            df[c] = df[c].replace(["None", "nan", ""], None)

    # Semestre SXX
    def fmt_sem(s):
        if not s:
            return None
        try:
            return f"S{int(float(str(s).replace('S', ''))):02d}"
        except:
            return None

    df["code_semestre_cle"] = df["semestre_numero"].apply(fmt_sem)

    # Mode inscription
    df["code_mode_inscription"] = df["modeinscription_label"].astype(str).str.upper().replace({
        "CLASSIQUE": "CLAS",
        "HYBRIDE": "HYB",
        "NAN": "CLAS",
        None: "CLAS"
    })

    return df


# ----------------------------
# Import Etudiants
# ----------------------------
def _import_etudiants(session: Session, df: pd.DataFrame):
    print("\n--- Importation Étudiants ---")

    dfe = df.drop_duplicates(subset=["etudiant_id"]).dropna(subset=["etudiant_id"])

    for _, row in tqdm(dfe.iterrows(), total=len(dfe), desc="Étudiants"):
        
        # --- CORRECTION APPLIQUÉE ICI ---
        # Si la date est NaT (valeur manquante de Pandas), on la remplace par None
        
        naissance_date = _clean_date(row["etudiant_naissance_date"])
        cin_date = row.get("etudiant_cin_date")
        
        # Vérifiez si NaT est présent pour Etudiant_naissance_date (après _clean_date)
        # et Etudiant_cin_date (avant ou après nettoyage si c'est une date brute)
        
        naissance_date_val = None if pd.isna(naissance_date) else naissance_date
        cin_date_val = None if pd.isna(cin_date) else cin_date
        
        # Le champ Etudiant_bacc_annee, même si numérique, est sécurisé contre NaN
        bacc_annee_val = row.get("etudiant_bacc_annee")
        if pd.isna(bacc_annee_val):
             bacc_annee_val = None # Assurer la conversion de NaN en None pour les chiffres aussi.

        try:
            session.merge(Etudiant(
                Etudiant_id=safe_string(row["etudiant_id"]),
                Etudiant_numero_inscription=safe_string(row.get("etudiant_numero_inscription")),
                Etudiant_nom=safe_string(row["etudiant_nom"]),
                Etudiant_prenoms=safe_string(row.get("etudiant_prenoms")),
                Etudiant_sexe=safe_string(row.get("etudiant_sexe", "A")),
                
                # --- UTILISATION DES VALEURS CORRIGÉES ---
                Etudiant_naissance_date = naissance_date_val,
                
                Etudiant_naissance_lieu=safe_string(row.get("etudiant_naissance_lieu")),
                Etudiant_nationalite=safe_string(row.get("etudiant_nationalite")),
                
                # Correction pour Etudiant_bacc_annee
                Etudiant_bacc_annee=bacc_annee_val, 
                
                Etudiant_bacc_numero=safe_string(row.get("etudiant_bacc_numero")),
                Etudiant_bacc_serie=safe_string(row.get("etudiant_bacc_serie")),
                Etudiant_bacc_centre=safe_string(row.get("etudiant_bacc_centre")),
                Etudiant_bacc_mention=safe_string(row.get("etudiant_bacc_mention")),
                Etudiant_telephone=safe_string(row.get("etudiant_telephone")),
                Etudiant_mail=safe_string(row.get("etudiant_mail")),
                Etudiant_cin=safe_string(row.get("etudiant_cin")),
                
                # --- UTILISATION DES VALEURS CORRIGÉES ---
                Etudiant_cin_date=cin_date_val, 
                
                Etudiant_cin_lieu=safe_string(row.get("etudiant_cin_lieu"))
            ))

            session.commit()

        except Exception as e:
            session.rollback()
            print(f"❌ [ETUDIANT] Erreur d'insertion pour l'étudiant {row['etudiant_id']}: {e}")
            # Si vous utilisez tqdm, vous pouvez ajouter une gestion des erreurs plus détaillée ici.

    print("✅ Étudiants importés.")

# ----------------------------
# Mapping helpers
# ----------------------------
def _get_parcours_mapping(session):
    return {c: i for c, i in session.query(Parcours.Parcours_code, Parcours.Parcours_id)}

def _get_semestre_mapping(session):
    return {s.Semestre_numero: s.Semestre_id for s in session.query(Semestre).all()}

def _get_annee_mapping(session):
    return {a.AnneeUniversitaire_annee: a.AnneeUniversitaire_id for a in session.query(AnneeUniversitaire).all()}

def _get_mode_mapping(session):
    return {m.ModeInscription_code.upper(): m.ModeInscription_id for m in session.query(ModeInscription).all()}


# ----------------------------
# Import inscriptions
# ----------------------------
def _import_inscriptions_details(session, df, parc_map, sem_map, annee_map, mode_map):
    print("\n--- Importation Inscriptions ---")

    df = df.dropna(subset=["etudiant_id", "code_semestre_cle",
                           "parcours_code", "anneeuniversitaire_annee",
                           "inscription_code"])

    count = 0

    for _, row in tqdm(df.iterrows(), total=len(df), desc="Inscriptions"):

        session.merge(Inscription(
            Inscription_id=row["inscription_code"],
            Etudiant_id_fk=row["etudiant_id"],
            Parcours_id_fk=parc_map.get(row["parcours_code"]),
            Semestre_id_fk=sem_map.get(row["code_semestre_cle"]),
            AnneeUniversitaire_id_fk=annee_map.get(str(row["anneeuniversitaire_annee"])),
            ModeInscription_id_fk=mode_map.get(row["code_mode_inscription"]),
            Inscription_date=datetime.now().date()
        ))

        count += 1
        if count % 300 == 0:
            session.commit()

    session.commit()
    print("✅ Inscriptions importées.")


# ----------------------------
# ORCHESTRATEUR
# ----------------------------
def import_inscriptions_to_db(session: Session):
    df = _load_and_clean_inscriptions()
    if df is None:
        print("❌ Impossible de charger les inscriptions")
        return

    print("🔗 Récupération des mappings...")
    parc = _get_parcours_mapping(session)
    sem = _get_semestre_mapping(session)
    ann = _get_annee_mapping(session)
    mode = _get_mode_mapping(session)

    _import_etudiants(session, df)
    _import_inscriptions_details(session, df, parc, sem, ann, mode)

    print("✅ Importation Étudiants + Inscriptions terminée.")
