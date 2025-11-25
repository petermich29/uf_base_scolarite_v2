import pandas as pd
import sys
from tqdm import tqdm
from sqlalchemy.orm import Session
from datetime import datetime, date
import pandas as pd
import numpy as np

import config
from models import (
    Institution, Composante, Domaine, Mention, Parcours, TypeFormation
)
from fixed_references import _generate_id

def safe_string(s):
    if s is None or not isinstance(s, str):
        return s
    return s.strip()


# ----------------------------
# 1. Import Institutions
# ----------------------------
def _import_institutions(session: Session):
    print("\n--- Importation Institutions ---")
    df = pd.read_excel(config.INSTITUTION_FILE_PATH)
    df.columns = df.columns.str.lower().str.replace(" ", "_")
    df = df.where(pd.notnull(df), None)

    if "institution_code" not in df.columns:
        print("❌ Colonne institution_code absente.")
        return {}

    df = df.drop_duplicates(subset=["institution_code"]).dropna(subset=["institution_code"])

    mapping = {}
    counter = 0

    for _, row in tqdm(df.iterrows(), total=len(df), desc="Institutions"):
        counter += 1
        inst_code = safe_string(row["institution_code"])
        inst_id = _generate_id("INST", counter)
        mapping[inst_code] = inst_id

        session.merge(Institution(
            Institution_id=inst_id,
            Institution_code=inst_code,
            Institution_nom=safe_string(row.get("institution_nom")),
            Institution_type=safe_string(row.get("institution_type")),
            Institution_description=safe_string(row.get("institution_description")),
            Institution_abbreviation=safe_string(row.get("institution_abbreviation")),
            Institution_logo_path=None
        ))

    session.commit()
    return mapping


# ----------------------------
# 2. Load Metadata
# ----------------------------
def _load_and_clean_metadata():
    try:
        df = pd.read_excel(config.METADATA_FILE_PATH)
    except Exception as e:
        print(f"❌ ERREUR lecture metadata : {e}")
        return None

    df.columns = df.columns.str.lower().str.replace(" ", "_")
    df = df.where(pd.notnull(df), None)

    cols = ["institution_code", "composante_code", "domaine_code",
            "mention_code", "parcours_code", "typeformation_code"]

    for c in cols:
        if c in df.columns:
            df[c] = df[c].astype(str).apply(safe_string)
            df[c] = df[c].replace(["None", "nan", ""], None)

    return df


# ----------------------------
# 3. Import Composantes
# ----------------------------
def _import_composantes(session: Session, df, inst_map):
    print("\n--- Importation Composantes ---")
    dfc = df[["composante_code", "composante_label",
              "institution_code", "composante_abbreviation"]].drop_duplicates()

    mapping = {}
    counter = 0

    for _, row in tqdm(dfc.iterrows(), total=len(dfc), desc="Composantes"):

        inst_id_fk = inst_map.get(row["institution_code"])
        if not inst_id_fk:
            print(f"⚠️ Institution inconnue pour composante {row['composante_code']}")
            continue

        counter += 1
        comp_id = _generate_id("COMP", counter)
        mapping[row["composante_code"]] = comp_id

        session.merge(Composante(
            Composante_id=comp_id,
            Composante_code=row["composante_code"],
            Composante_label=safe_string(row["composante_label"]),
            Composante_abbreviation=safe_string(row["composante_abbreviation"]),
            Institution_id_fk=inst_id_fk,
        ))

    session.commit()
    return mapping


# ----------------------------
# 4. Import Domaines
# ----------------------------
def _import_domaines(session: Session, df):
    print("\n--- Importation Domaines ---")
    dfd = df[["domaine_code", "domaine_label"]].drop_duplicates()

    mapping = {}
    counter = 0

    for _, row in tqdm(dfd.iterrows(), total=len(dfd), desc="Domaines"):
        dom_code = row["domaine_code"]

        # Vérifier si le domaine existe déjà
        existing = session.query(Domaine).filter_by(Domaine_code=dom_code).first()

        if existing:
            # Mise à jour éventuelle
            existing.Domaine_label = safe_string(row["domaine_label"])
            mapping[dom_code] = existing.Domaine_id
            continue

        # Sinon → insertion
        counter += 1
        doma_id = _generate_id("DOMA", counter)
        mapping[dom_code] = doma_id

        new_dom = Domaine(
            Domaine_id=doma_id,
            Domaine_code=dom_code,
            Domaine_label=safe_string(row["domaine_label"]),
        )
        session.add(new_dom)

    session.commit()
    return mapping


# ----------------------------
# 5. Import Mentions
# ----------------------------
def _import_mentions(session: Session, df, comp_map, doma_map):
    print("\n--- Importation Mentions ---")
    dfm = df[[
        "mention_code", "mention_label",
        "composante_code", "domaine_code",
        "mention_abbreviation"
    ]].drop_duplicates()

    mapping = {}
    counter = 0

    for _, row in tqdm(dfm.iterrows(), total=len(dfm), desc="Mentions"):
        ment_code = row["mention_code"]
        comp_fk = comp_map.get(row["composante_code"])
        doma_fk = doma_map.get(row["domaine_code"])

        if not comp_fk or not doma_fk:
            print(f"⚠️ Composante/Domaine introuvable pour mention {ment_code}")
            continue

        # Vérifier si la mention existe déjà
        existing = (
            session.query(Mention)
            .filter_by(Mention_code=ment_code, Composante_id_fk=comp_fk)
            .first()
        )

        if existing:
            # Mise à jour
            existing.Mention_label = safe_string(row["mention_label"])
            existing.Mention_abbreviation = safe_string(row["mention_abbreviation"])
            existing.Domaine_id_fk = doma_fk
            mapping[ment_code] = existing.Mention_id
            continue

        # Sinon insertion
        counter += 1
        ment_id = _generate_id("MENT", counter)
        mapping[ment_code] = ment_id

        new_mention = Mention(
            Mention_id=ment_id,
            Mention_code=ment_code,
            Mention_label=row["mention_label"],
            Mention_abbreviation=row["mention_abbreviation"],
            Composante_id_fk=comp_fk,
            Domaine_id_fk=doma_fk,
        )
        session.add(new_mention)

    session.commit()
    return mapping


# ----------------------------
# 6. Import Parcours
# ----------------------------
def _clean_date(value):
    """
    Convertit nan, NaT, None, "nan", "" en None.
    Convertit les vraies dates en type date Python.
    """
    if value is None:
        return None
    if isinstance(value, float) and np.isnan(value):
        return None
    if isinstance(value, str) and value.strip().lower() in ["nan", "", "none"]:
        return None

    try:
        d = pd.to_datetime(value, errors="coerce")
        if pd.isna(d):
            return None
        return d.date()
    except:
        return None


def _import_parcours(session: Session, df, ment_map):
    print("\n--- Importation Parcours ---")
    dfp = df[[
        "parcours_code", "parcours_label", "mention_code",
        "date_creation", "date_fin", "typeformation_code",
        "parcours_abbreviation"
    ]].drop_duplicates()

    # Mapping TypeFormation
    t_map = {c: i for c, i in session.query(TypeFormation.TypeFormation_code,
                                           TypeFormation.TypeFormation_id).all()}

    mapping = {}
    counter = 0

    for _, row in tqdm(dfp.iterrows(), total=len(dfp), desc="Parcours"):
        ment_fk = ment_map.get(row["mention_code"])
        if not ment_fk:
            print(f"⚠️ Mention inconnue pour parcours {row['parcours_code']}")
            continue

        # Nettoyage des dates
        date_creation = _clean_date(row.get("date_creation"))
        date_fin = _clean_date(row.get("date_fin"))

        # Vérifier si le parcours existe déjà
        existing = session.query(Parcours).filter_by(
            Parcours_code=row["parcours_code"],
            Mention_id_fk=ment_fk
        ).first()

        if existing:
            # Mise à jour seulement
            existing.Parcours_label = row["parcours_label"]
            existing.Parcours_abbreviation = row["parcours_abbreviation"]
            existing.Parcours_type_formation_defaut_id_fk = t_map.get(row["typeformation_code"])
            existing.Parcours_date_creation = date_creation
            existing.Parcours_date_fin = date_fin

            mapping[row["parcours_code"]] = existing.Parcours_id
            continue

        # Insertion nouvelle
        counter += 1
        parc_id = _generate_id("PARC", counter)
        mapping[row["parcours_code"]] = parc_id

        session.add(Parcours(
            Parcours_id=parc_id,
            Parcours_code=row["parcours_code"],
            Parcours_label=row["parcours_label"],
            Parcours_abbreviation=row["parcours_abbreviation"],
            Mention_id_fk=ment_fk,
            Parcours_type_formation_defaut_id_fk=t_map.get(row["typeformation_code"]),
            Parcours_date_creation=date_creation,
            Parcours_date_fin=date_fin
        ))

    session.commit()
    return mapping


# ----------------------------
# ORCHESTRATEUR
# ----------------------------
def import_metadata_to_db(session: Session):

    inst_map = _import_institutions(session)
    df = _load_and_clean_metadata()
    if df is None:
        return

    comp_map = _import_composantes(session, df, inst_map)
    doma_map = _import_domaines(session, df)
    ment_map = _import_mentions(session, df, comp_map, doma_map)
    _import_parcours(session, df, ment_map)

    print("✅ Importation métadonnées terminée.")
