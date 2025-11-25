# import_data.py

import pandas as pd
import sys
import logging
from tqdm import tqdm
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, DataError
from datetime import date 
from datetime import datetime
import numpy as np
import os

# Assurez-vous que config.py et database_setup.py sont bien configurés
import config
import database_setup
from models import (
    Institution, Composante, Domaine, Mention, Parcours, 
    AnneeUniversitaire, Etudiant, Inscription,
    # CLASSES LMD & MODE INSCRIPTION
    Cycle, Niveau, Semestre, ModeInscription, SessionExamen,
    TypeFormation, ParcoursNiveau,
    # AJOUT POTENTIEL des nouvelles classes
    Enseignant, Jury
)

# Configuration du logging
logging.basicConfig(filename='import_errors.log', 
                    filemode='w', 
                    encoding='utf-8',
                    level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def safe_string(s):
    """Assure le nettoyage des chaînes de caractères."""
    if s is None or not isinstance(s, str):
        return s
    
    s = str(s).strip()
    return s


# ----------------------------------------------------------------------
# GÉNÉRATION ET IMPORTATION DES DONNÉES DE RÉFÉRENCE FIXES
# ----------------------------------------------------------------------

def _generate_annee_data(start_year: int = 2021, end_year: int = 2026) -> list:
    """
    Génère les données des années universitaires avec leur ordre chronologique.
    """
    annee_list = []
    
    # Ordre commence à 0 pour 2021-2022
    for i in range(end_year - start_year + 1):
        annee_start = start_year + i
        annee_end = annee_start + 1
        annee_str = f"{annee_start}-{annee_end}"
        
        annee_list.append({
            'annee': annee_str,
            'ordre_annee': i, # 0, 1, 2, 3, 4, 5...
            'description': f"Année académique {annee_str}"
        })
    return annee_list

import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func
# Les imports de vos modèles (Cycle, Niveau, Semestre, etc.) et database_setup sont supposés exister

# --- Fonction d'aide pour la génération d'ID ---
# Le compteur global pour l'incrémentation peut être initialisé si nécessaire, 
# mais ici, nous générons l'ID en ligne pour chaque bloc.

def _generate_id(prefix: str, index: int) -> str:
    """
    Génère un ID de la forme PREFIX_XXX, où XXX est index formaté 
    avec une longueur spécifique à chaque entité (normalisation).
    """
    length_map = {
        'INST': 4, 'DOMA': 2, 'COMP': 4, 'MENT': 6, 'PARC': 7, 
        'CYCL': 1, 'NIVE': 2, 'SEME': 2, 'SESS': 1, 'TYPE': 2, 
        'ANNE': 4, 'MODE': 3,
    }

    if prefix not in length_map:
        raise ValueError(f"Préfixe d'ID '{prefix}' non reconnu ou non configuré pour la longueur.")

    format_length = length_map[prefix]
    
    # 🚨 CORRECTION CI-DESSOUS 🚨
    if format_length == 1:
        # Pour une longueur de 1, le formatage standard ':d' est suffisant et plus sûr.
        formatted_index = f"{index:d}"
    else:
        # Pour les longueurs > 1, nous utilisons le remplissage de zéro standard.
        format_spec = f"0{format_length}d" 
        formatted_index = format(index, format_spec)
    # 🚨 FIN DE LA CORRECTION 🚨

    # Vérification de débordement (ID généré > longueur max)
    if len(formatted_index) > format_length:
        raise OverflowError(f"Le compteur d'index ({index}) est trop grand pour la longueur d'ID de {format_length} chiffres pour le préfixe '{prefix}'.")

    return f"{prefix}_{formatted_index}"

def import_fixed_references(session: Session, start_year: int = 2021, end_year: int = 2026):
    """
    Insère les données de référence fixes (Cycles, Niveaux, Semestres, Types Inscription, 
    Sessions, Types Formation, ANNEES UNIVERSITAIRES) en utilisant les nouveaux schémas d'ID.
    """
    print("\n--- 1. Importation des Données de Référence Fixes (LMD, Types & Années Univ.) ---")
    
    # --- 1. Cycles (Préfixe: CYCL, Longueur ID: 1) ---
    print("1. Cycles...")
    cycles_data = [
        {'code': 'L', 'label': 'Licence'}, 
        {'code': 'M', 'label': 'Master'}, 
        {'code': 'D', 'label': 'Doctorat'}
    ]
    for i, data in enumerate(cycles_data, 1):
        session.merge(Cycle(
            Cycle_id=_generate_id('CYCL', i),
            Cycle_code=data['code'],
            Cycle_label=data['label']
        ))
    
    # --- 2. Niveaux et Semestres (Préfixes: NIVE - 2, SEME - 2) ---
    print("2. Niveaux et Semestres...")
    niveau_semestre_map = {
        'L1': ('L', ['S01', 'S02']), 'L2': ('L', ['S03', 'S04']), 'L3': ('L', ['S05', 'S06']), 
        'M1': ('M', ['S07', 'S08']), 'M2': ('M', ['S09', 'S10']), 
        'D1': ('D', ['S11', 'S12']), 'D2': ('D', ['S13', 'S14']), 'D3': ('D', ['S15', 'S16']),
    }
    
    # Dictionnaire temporaire pour mapper les codes de cycle aux IDs générés
    cycle_code_to_id = {data['code']: _generate_id('CYCL', i) for i, data in enumerate(cycles_data, 1)}
    
    niveau_counter = 0
    semestre_counter = 0
    
    for niv_code, (cycle_code, sem_list) in niveau_semestre_map.items():
        niveau_counter += 1
        niv_id = _generate_id('NIVE', niveau_counter)
        cycle_id = cycle_code_to_id.get(cycle_code)
        
        session.merge(Niveau(
            Niveau_id=niv_id,
            Niveau_code=niv_code, # Ex: L1
            Niveau_label=niv_code,
            Cycle_id_fk=cycle_id 
        ))
        
        for sem_num in sem_list:
            semestre_counter += 1
            sem_code_complet = f"{niv_code}_{sem_num}" # Ex: L1_S01
            
            session.merge(Semestre(
                Semestre_id=_generate_id('SEME', semestre_counter),
                Semestre_code=sem_code_complet,
                Semestre_numero=sem_num, # Ex: S01
                Niveau_id_fk=niv_id
            ))

    # --- 3. Modes Inscription (Préfixe: MODE) ---
    print("3. Modes Inscription...")
    modes_inscription_data = [{'code': 'CLAS', 'label': 'Classique'}, {'code': 'HYB', 'label': 'Hybride'}]
    for i, data in enumerate(modes_inscription_data, 1):
        session.merge(ModeInscription(
            ModeInscription_id=_generate_id('MODE', i),
            ModeInscription_code=data['code'],
            ModeInscription_label=data['label']
        ))
        
    # --- 4. Insertion des Sessions d'Examen (Préfixe: SESS, Longueur ID: 1) ---
    print("4. Sessions d'Examen...")
    session_examen_data = [{'code_session': 'N', 'label': 'Normale'}, {'code_session': 'R', 'label': 'Rattrapage'}]
    for i, sess in enumerate(session_examen_data, 1):
        session.merge(SessionExamen(
            SessionExamen_id=_generate_id('SESS', i),
            SessionExamen_code=sess['code_session'],
            SessionExamen_label=sess['label']
        ))

    # --- 5. Insertion des Types de Formation (Préfixe: TYPE, Longueur ID: 2) ---
    print("5. Types de Formation...")
    types_formation_data = [
        {'code': 'FI', 'label': 'Formation Initiale', 'description': 'Formation classique à temps plein.'},
        {'code': 'FC', 'label': 'Formation Continue', 'description': 'Formation destinée aux professionnels en activité.'},
        {'code': 'FOAD', 'label': 'Formation à Distance', 'description': 'Formation ouverte à distance.'},
    ]
    for i, data in enumerate(types_formation_data, 1):
        session.merge(TypeFormation(
            TypeFormation_id=_generate_id('TYPE', i),
            TypeFormation_code=data['code'],
            TypeFormation_label=data['label'],
            TypeFormation_description=data['description']
        ))
        
    # --- 6. Insertion des Années Universitaires (Préfixe: ANNE, Longueur ID: 4) ---
    print("6. Années Universitaires (ANNE)...")
    annees_data = _generate_annee_data(start_year=start_year, end_year=end_year)
    for i, data in enumerate(annees_data, 1):
        session.merge(AnneeUniversitaire(
            AnneeUniversitaire_id=_generate_id('ANNE', i), 
            AnneeUniversitaire_annee=data['annee'], 
            AnneeUniversitaire_ordre=data['ordre_annee'],
            AnneeUniversitaire_description=data['description']
        ))
        
    session.commit()
    print("✅ Données de Référence LMD, Types, Sessions et Années Universitaires insérées avec les nouveaux ID.")
# ----------------------------------------------------------------------
# FONCTIONS D'IMPORTATION UNITAIRE DE LA STRUCTURE ACADÉMIQUE
# ----------------------------------------------------------------------
# --- 1. Importation des Institutions (ID généré INST_XXXX) ---

def _import_institutions(session: Session) -> dict:
    """Charge et importe la table Institution en générant les IDs (INST_XXXX)."""
    print("\n--- Importation des Institutions (INST) ---")
    institution_code_to_id = {}
    try:
        df_inst = pd.read_excel(config.INSTITUTION_FILE_PATH)
        df_inst.columns = df_inst.columns.str.lower().str.replace(' ', '_')
        df_inst = df_inst.where(pd.notnull(df_inst), None)
        
        key_code = 'institution_code'
        if key_code not in df_inst.columns:
            print(f"❌ Colonne '{key_code}' manquante. Impossible de lire la source Institutions.", file=sys.stderr)
            return {}
            
        df_inst_clean = df_inst.drop_duplicates(subset=[key_code]).dropna(subset=[key_code])
        
        inst_counter = 0
        for _, row in tqdm(df_inst_clean.iterrows(), total=len(df_inst_clean), desc="Institutions"):
            inst_counter += 1
            inst_code = safe_string(row[key_code])
            inst_id = _generate_id('INST', inst_counter) # ID INST_XXXX
            institution_code_to_id[inst_code] = inst_id 
            
            logo_path = None 

            session.merge(Institution(
                Institution_id=inst_id, 
                Institution_code=inst_code, 
                Institution_nom=safe_string(row['institution_nom']),
                Institution_type=safe_string(row['institution_type']),
                Institution_description=safe_string(row['institution_description']) if 'institution_description' in row else None,
                Institution_abbreviation=safe_string(row['institution_abbreviation']) if 'institution_abbreviation' in row else None,
                Institution_logo_path=logo_path 
            ))
        
        session.commit()
        print(f"✅ Importation des Institutions terminée ({inst_counter} lignes) et commitée.")
        return institution_code_to_id
        
    except Exception as e:
        print(f"❌ ERREUR: Impossible de lire ou d'importer le fichier Institutions. {e}", file=sys.stderr)
        session.rollback()
        return {}


# --- 2. Chargement des Métadonnées Académiques (inchangé) ---

def _load_and_clean_metadata():
    """Charge et nettoie le fichier de métadonnées académiques."""
    try:
        df = pd.read_excel(config.METADATA_FILE_PATH)
        df.columns = df.columns.str.lower().str.replace(' ', '_')
        print(f"Fichier de métadonnées académiques chargé. {len(df)} lignes trouvées.")
        
        cols_to_clean = [
            'institution_code', 'composante_code', 'domaine_code', 
            'mention_code', 'parcours_code', 'typeformation_code' 
        ]
        
        for col in cols_to_clean:
            if col in df.columns:
                # 1. Convertir en string et appliquer safe_string
                df[col] = df[col].astype(str).apply(safe_string)
                
                # 2. 🚨 Gérer explicitement les chaînes indiquant une valeur manquante 🚨
                #    Nous ciblons 'None', 'nan', et les strings vides.
                df[col] = df[col].replace(['None', 'none', 'nan', ''], None) 
                
        # 3. Assurer que les valeurs manquantes (y compris celles remplacées ci-dessus) sont bien des None/NULL
        df = df.where(pd.notnull(df), None)
        
        return df
        
    except Exception as e:
        print(f"❌ ERREUR: Impossible de lire le fichier de métadonnées académiques. {e}", file=sys.stderr)
        return None

# --- 3. Importation des Composantes (ID généré COMP_XXXX) ---

def _import_composantes(session: Session, df: pd.DataFrame, inst_map: dict) -> dict:
    """Importe les Composantes (dépend d'Institution) avec ID généré (COMP_XXXX)."""
    print("\n--- Importation des Composantes (COMP) ---")
    composante_code_to_id = {}
    
    cols_comp = ['composante_code', 'composante_label', 'institution_code', 'composante_abbreviation']
    if not all(col in df.columns for col in cols_comp):
        print(f"Colonnes de Composante manquantes dans les métadonnées. Attendu: {cols_comp}")
        return {}
        
    df_composantes = df[cols_comp].drop_duplicates(
        subset=['composante_code']).dropna(subset=['composante_code', 'institution_code'])
    
    comp_counter = 0
    for _, row in tqdm(df_composantes.iterrows(), total=len(df_composantes), desc="Composantes"):
        comp_code = row['composante_code']
        inst_code = row['institution_code']
        
        inst_id_fk = inst_map.get(inst_code)
        if not inst_id_fk:
             print(f"⚠️ Institution code {inst_code} non trouvé pour Composante {comp_code}. Ligne ignorée/problématique.")
             continue

        comp_counter += 1
        comp_id = _generate_id('COMP', comp_counter) # ID COMP_XXXX
        composante_code_to_id[comp_code] = comp_id
        
        session.merge(Composante(
            Composante_id=comp_id, 
            Composante_code=comp_code, 
            Composante_label=safe_string(row['composante_label']),
            Composante_abbreviation=safe_string(row['composante_abbreviation']),
            Institution_id_fk=inst_id_fk,
        ))
    
    print(f"✅ {comp_counter} Composantes en attente de commit.")
    return composante_code_to_id

# --- 4. Importation des Domaines (ID généré DOMA_XX) ---

def _import_domaines(session: Session, df: pd.DataFrame) -> dict:
    """Importe les Domaines avec ID généré (DOMA_XX)."""
    print("\n--- Importation des Domaines (DOMA) ---")
    domaine_code_to_id = {}
    
    cols_doma = ['domaine_code', 'domaine_label']
    if not all(col in df.columns for col in cols_doma):
          print(f"Colonnes de Domaine manquantes dans les métadonnées. Attendu: {cols_doma}")
          return {}
          
    df_domaines = df[cols_doma].drop_duplicates(subset=['domaine_code']).dropna(subset=['domaine_code'])
    
    doma_counter = 0
    for _, row in tqdm(df_domaines.iterrows(), total=len(df_domaines), desc="Domaines"):
        doma_code = row['domaine_code']
        doma_counter += 1
        doma_id = _generate_id('DOMA', doma_counter) # ID DOMA_XX
        domaine_code_to_id[doma_code] = doma_id
        
        session.merge(Domaine(
            Domaine_id=doma_id, 
            Domaine_code=doma_code, 
            Domaine_label=safe_string(row['domaine_label'])
        ))
        
    print(f"✅ {doma_counter} Domaines en attente de commit.")
    return domaine_code_to_id

# --- 5. Importation des Mentions (ID généré MENT_XXXXXX) ---

def _import_mentions(session: Session, df: pd.DataFrame, comp_map: dict, doma_map: dict) -> dict:
    """Importe les Mentions (dépend de Composante et Domaine) avec ID généré (MENT_XXXXXX)."""
    print("\n--- Importation des Mentions (MENT) ---")
    mention_code_to_id = {}

    cols_ment = ['mention_code', 'mention_label', 'composante_code', 'domaine_code', 'mention_abbreviation']
    if not all(col in df.columns for col in cols_ment):
          print(f"Colonnes de Mention manquantes dans les métadonnées. Attendu: {cols_ment}")
          return {}
          
    df_mentions_source = df[cols_ment].drop_duplicates(
        subset=['mention_code']).dropna(subset=['composante_code', 'domaine_code', 'mention_code'])
    
    ment_counter = 0
    for _, row in tqdm(df_mentions_source.iterrows(), total=len(df_mentions_source), desc="Mentions"):
        ment_code = safe_string(row['mention_code'])
        comp_code = row['composante_code']
        doma_code = row['domaine_code']

        comp_id_fk = comp_map.get(comp_code)
        doma_id_fk = doma_map.get(doma_code)
        
        if not comp_id_fk:
             print(f"⚠️ Composante code {comp_code} non trouvé pour Mention {ment_code}. Ligne ignorée.")
             continue
        if not doma_id_fk:
             print(f"⚠️ Domaine code {doma_code} non trouvé pour Mention {ment_code}. Ligne ignorée.")
             continue
        
        ment_counter += 1
        ment_id = _generate_id('MENT', ment_counter) # ID MENT_XXXXXX
        
        mention_code_to_id[ment_code] = ment_id # Stockage du mapping (code -> ID généré)
        
        session.merge(Mention(
            Mention_id=ment_id, 
            Mention_code=ment_code, 
            Mention_label=safe_string(row['mention_label']),
            Mention_abbreviation=safe_string(row['mention_abbreviation']),
            Composante_id_fk=comp_id_fk,
            Domaine_id_fk=doma_id_fk
        ))
        
    print(f"✅ {ment_counter} Mentions en attente de commit.")
    return mention_code_to_id

# --- 6. Importation des Parcours (ID généré PARC_XXXXXXX) ---

def _import_parcours(session: Session, df: pd.DataFrame, ment_map_code_to_id: dict):
    """Importe les Parcours (dépend de Mention) avec ID généré (PARC_XXXXXXX)."""
    print("\n--- Importation des Parcours (PARC) ---")
    
    # 1. 🚨 Récupération du mapping Type Formation (CODE -> ID) 🚨
    # Ceci nécessite que la table 'types_formation' ait été remplie par import_fixed_references
    try:
        mapping_result = session.query(
            TypeFormation.TypeFormation_code, 
            TypeFormation.TypeFormation_id
        ).all()
        # Création du dictionnaire {code: id}
        type_formation_map = {code: id_ for code, id_ in mapping_result}
        
        if not type_formation_map:
             print("❌ ERREUR: La table TypesFormation est vide. L'importation des parcours ne peut pas continuer.")
             return
             
    except Exception as e:
        print(f"❌ ERREUR lors de la récupération du mapping TypeFormation: {e}")
        return
        
    # Colonnes nécessaires à l'importation
    cols_parc = ['parcours_code', 'parcours_label', 'mention_code', 'date_creation', 'date_fin', 'typeformation_code', 'parcours_abbreviation']
    if not all(col in df.columns for col in cols_parc):
          print(f"Colonnes de Parcours manquantes dans les métadonnées. Attendu: {cols_parc}")
          return
          
    # Nettoyage pour garder uniquement les lignes uniques et non nulles sur les clés principales
    df_parcours = df[cols_parc].drop_duplicates(
        subset=['parcours_code']).dropna(subset=['mention_code', 'parcours_code'])

    parc_counter = 0
    for _, row in tqdm(df_parcours.iterrows(), total=len(df_parcours), desc="Parcours"):
        
        parc_code = safe_string(row['parcours_code'])
        ment_code_fk = safe_string(row['mention_code']) 

        # 2. Résolution de la clé étrangère Mention_id_fk via le mapping code -> ID
        ment_id_fk = ment_map_code_to_id.get(ment_code_fk)
        
        if not ment_id_fk:
             print(f"⚠️ Mention code {ment_code_fk} non trouvé pour Parcours {parc_code}. Ligne ignorée.")
             continue

        # Génération d'ID
        parc_counter += 1
        parc_id = _generate_id('PARC', parc_counter) # ID PARC_XXXXXXX

        # Conversion des dates
        date_creation_val = int(row['date_creation']) if pd.notna(row['date_creation']) and row['date_creation'] is not None else None
        date_fin_val = int(row['date_fin']) if pd.notna(row['date_fin']) and row['date_fin'] is not None else None
        
        # 3. Récupération et résolution du Type Formation
        type_formation_code = row['typeformation_code']
        
        if type_formation_code is None:
            # Si le code est manquant dans le fichier (devient NULL en DB)
            type_formation_id_fk = None 
        else:
            # Conversion du CODE ('FI', 'FC', ...) en ID technique ('TYPE_01', 'TYPE_02', ...)
            type_formation_id_fk = type_formation_map.get(type_formation_code)
            
            if type_formation_id_fk is None:
                # Gérer le cas où un code existe mais n'est pas dans la table de référence
                print(f"⚠️ Type Formation code {type_formation_code} non trouvé dans la table de référence. NULL sera utilisé (si permis).")


        session.merge(Parcours(
            Parcours_id=parc_id, 
            Parcours_code=parc_code,
            Parcours_label=safe_string(row['parcours_label']),
            Parcours_abbreviation=safe_string(row['parcours_abbreviation']),
            Mention_id_fk=ment_id_fk, 
            # 4. Utilisation de l'ID technique
            Parcours_type_formation_defaut_id_fk=type_formation_id_fk,
            Parcours_date_creation=date_creation_val,
            Parcours_date_fin=date_fin_val
        ))
        
    print(f"✅ {parc_counter} Parcours en attente de commit.")


# --- 7. Orchestrateur Principal (inchangé) ---

def import_metadata_to_db(session: Session):
    """
    Orchestre l'importation de la structure académique.
    """
    print(f"\n--- 2. Démarrage de l'importation des métadonnées ---")

    try:
        # 1. Importe et commit les Institutions
        inst_map = _import_institutions(session)
        if not inst_map:
            return

        # 2. Chargement et nettoyage des données
        df_metadata = _load_and_clean_metadata()
        if df_metadata is None:
            return
        
        # 3. Importation des tables générant des IDs et des mappings
        comp_map = _import_composantes(session, df_metadata, inst_map) 
        doma_map = _import_domaines(session, df_metadata) 
        
        # 4. Importation de Mention (code -> ID généré)
        ment_map_code_to_id = _import_mentions(session, df_metadata, comp_map, doma_map) 

        # 5. Importation des Parcours (utilise ment_map_code_to_id)
        if ment_map_code_to_id:
            _import_parcours(session, df_metadata, ment_map_code_to_id) 

        # 6. Commit final
        session.commit() 
        print("\n✅ Importation des métadonnées académiques (Composante, Domaine, Mention, Parcours) terminée avec succès.")

    except Exception as e:
        session.rollback()
        print(f"\n❌ ERREUR D'IMPORTATION (Métadonnées): {e}", file=sys.stderr)
        
# ----------------------------------------------------------------------
# FONCTIONS D'IMPORTATION UNITAIRE DES INSCRIPTIONS
# ----------------------------------------------------------------------

def _load_and_clean_inscriptions():
    """
    Charge, nettoie et enrichit le fichier d'inscriptions.
    Standardise les codes académiques (Semestre, Mode) pour la résolution des FK.
    """
    try:
        df = pd.read_excel(config.INSCRIPTION_FILE_PATH)
        # Convertir les noms de colonnes en minuscules avec underscores
        df.columns = df.columns.str.lower().str.replace(' ', '_')
        print(f"Fichier XLSX d'inscriptions chargé. {len(df)} lignes trouvées.")
        
        # --- 1. Gestion des Dates ---
        date_cols = ['etudiant_naissance_date', 'etudiant_cin_date']
        for col in date_cols:
            if col in df.columns:
                # Convertir en objet date Python (YYYY-MM-DD), 'coerce' pour mettre NaT si invalide
                df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True).dt.date
            
        # --- 2. Standardisation des Codes et Remplacement des Valeurs Manquantes ---
        
        # Remplacement des NaN/NaT par la valeur Python None
        df = df.where(pd.notnull(df), None)
        
        # Définition des colonnes contenant des codes à standardiser pour les FK
        # Note : 'type_formation' est retiré de la liste si elle n'est plus pertinente
        cols_to_standardize = [
            'parcours_code', 'niveau_code', 'semestre_numero', 
            'modeinscription_label', 
            'institution_code', 'composante_code', 'domaine_code', 
            'mention_abbreviation', 'etudiant_id', 'anneeuniversitaire_annee'
        ]
        
        for col in cols_to_standardize:
            if col in df.columns:
                # 2.1. Convertir en string (pour les codes) et appliquer safe_string
                df[col] = df[col].astype(str).apply(safe_string)
                
                # 2.2. Nettoyage crucial des chaînes littérales de valeur manquante
                df[col] = df[col].replace(['None', 'none', 'nan', ''], None)
                
        # --- 3. Création du Code Semestre (Format SXX) ---
        
        df['code_semestre_cle'] = None 
        
        if 'semestre_numero' in df.columns:
             
            def create_semestre_code_simple(sem_num):
                """Formate le numéro du semestre en SXX (ex: 1 -> S01)."""
                if sem_num:
                    try:
                        # Gérer S1, S01 ou 1.0 -> S01
                        sem_num_str = str(sem_num).upper().replace('S', '')
                        sem_num_int = int(float(sem_num_str))
                        return f"S{sem_num_int:02d}"
                    except:
                        return None
                return None
            
            df['code_semestre_cle'] = df['semestre_numero'].apply(create_semestre_code_simple)
            
        # --- 4. Standardisation du Code Mode Inscription (CLAS et HYB uniquement) ---
        
        source_col = None
        if 'modeinscription_label' in df.columns:
            source_col = 'modeinscription_label'
            
        df['code_mode_inscription'] = 'CLAS' # Valeur par défaut : CLAS
        
        if source_col:
            # 4.1. Application de la standardisation
            df.loc[:, 'code_mode_inscription'] = df[source_col].astype(str).str.upper()
            
            # 4.2. Remplacement par les codes courts (CLAS et HYB seulement)
            df.loc[:, 'code_mode_inscription'] = df['code_mode_inscription'].replace({ 
                 'CLASSIQUE': 'CLAS', 
                 'HYBRIDE': 'HYB',
                 # Toutes les autres valeurs sont mappées sur CLAS
                 'A DISTANCE': 'CLAS', 'FOAD': 'CLAS', # S'assurer qu'aucune autre valeur ne passe
                 'NAN': 'CLAS', 'NONE': 'CLAS', '': 'CLAS', np.nan: 'CLAS', 'NAT': 'CLAS' 
            })
            
            # 4.3. S'assurer que seules CLAS ou HYB restent
            df['code_mode_inscription'] = df['code_mode_inscription'].apply(
                lambda x: 'CLAS' if pd.isna(x) or x not in ['CLAS', 'HYB'] else x
            )
        
        # Finaliser le remplacement des NaN/NaT par None (après enrichissement des codes)
        df = df.where(pd.notnull(df), None)
        
        return df
        
    except Exception as e:
        print(f"❌ ERREUR: Impossible de lire ou de nettoyer le fichier d'inscriptions. {e}", file=sys.stderr)
        return None

def _import_etudiants(session: Session, df: pd.DataFrame):
    """
    Importe les Étudiants en garantissant l'unicité des personnes.
    Utilise session.merge pour la gestion de l'idempotence (insert ou update).
    """
    print("\n--- Importation des Étudiants (Ligne par Ligne) ---")
    
    # --- 1. Préparation du DataFrame : Isoler les étudiants uniques ---
    df_etudiants = df.drop_duplicates(
        subset=['etudiant_id'], 
        keep='first'
    ).dropna(
        subset=['etudiant_id', 'etudiant_nom']
    )
    
    total_etudiants = len(df_etudiants)
    etudiant_errors = 0
    
    # --- 2. Itération et Insertion/Mise à jour ---
    for index, row in tqdm(df_etudiants.iterrows(), total=total_etudiants, desc="Import Etudiants"):
        # L'ID unique de l'étudiant (ex: ETU2022_xxxxx)
        etudiant_pk_value = safe_string(row.get('etudiant_id', f"ERR_ID_{index}")) 
        
        try:
            # Conversion robuste des champs numériques/dates
            bacc_annee_val = int(row['etudiant_bacc_annee']) if pd.notna(row.get('etudiant_bacc_annee')) else None
            
            # Les colonnes de date sont déjà nettoyées en objets date ou None par _load_and_clean_inscriptions
            naissance_date_val = row.get('etudiant_naissance_date') if isinstance(row.get('etudiant_naissance_date'), date) else None
            cin_date_val = row.get('etudiant_cin_date') if isinstance(row.get('etudiant_cin_date'), date) else None
            
            # Utilisation de session.merge() pour l'idempotence
            session.merge(Etudiant(
                # Clé primaire/unique pour la DB. Si c'est l'ID technique, il doit être fourni.
                Etudiant_id=etudiant_pk_value, 
                
                # Le code d'inscription (qui n'est plus la clé unique, mais une information)
                Etudiant_numero_inscription=safe_string(row.get('etudiant_numero_inscription')),
                
                # Informations Personnelles
                Etudiant_nom=safe_string(row['etudiant_nom']), 
                Etudiant_prenoms=safe_string(row['etudiant_prenoms']),
                Etudiant_sexe=safe_string(row.get('etudiant_sexe', 'A')), # Valeur par défaut 'A' pour Autre
                Etudiant_naissance_date=naissance_date_val, 
                Etudiant_naissance_lieu=safe_string(row.get('etudiant_naissance_lieu')),
                Etudiant_nationalite=safe_string(row.get('etudiant_nationalite', 'Malagasy')), # Défaut si manquant
                
                # Informations BACC
                Etudiant_bacc_annee=bacc_annee_val,
                Etudiant_bacc_numero=safe_string(row.get('etudiant_bacc_numero')),
                Etudiant_bacc_serie=safe_string(row.get('etudiant_bacc_serie')), 
                Etudiant_bacc_centre=safe_string(row.get('etudiant_bacc_centre')),
                Etudiant_bacc_mention=safe_string(row.get('etudiant_bacc_mention')),
                
                # Contacts et CIN
                Etudiant_telephone=safe_string(row.get('etudiant_telephone')), 
                Etudiant_mail=safe_string(row.get('etudiant_mail')),
                Etudiant_cin=safe_string(row.get('etudiant_cin')), 
                Etudiant_cin_date=cin_date_val, 
                Etudiant_cin_lieu=safe_string(row.get('etudiant_cin_lieu'))
            ))
            
            # Commit individuel pour isoler les erreurs
            session.commit()
            
        except Exception as e:
            session.rollback()
            etudiant_errors += 1
            e_msg = str(e.orig).lower() if hasattr(e, 'orig') and e.orig else str(e)
            
            # Affichage de l'erreur
            print(f"❌ [ETUDIANT] Ligne Excel {row.name} ({etudiant_pk_value}) - ERREUR: {e_msg.splitlines()[0]}")
            # logging.error(f"ETUDIANT: {etudiant_pk_value} | Erreur: {e_msg} | LIGNE_EXCEL_IDX: {row.name}")
            
    print(f"\n✅ Insertion des étudiants terminée. {etudiant_errors} erreur(s) individuelle(s) détectée(s).")


def _import_inscriptions_details(
    session: Session, 
    df: pd.DataFrame, 
    parc_map_code_to_id: dict,
    sem_map_code_to_id: dict,
    annee_map_annee_to_id: dict,
    mode_map_code_to_id: dict
):
    """Importe les Inscriptions en résolvant les codes en IDs techniques (FK) et en utilisant Inscription_code comme PK."""
    print("\n--- Importation des Inscriptions Détaillées ---")
    
    # Filtre les lignes qui n'ont pas les codes essentiels pour la FK (Semestre standardisé)
    df_inscriptions = df.dropna(subset=['etudiant_id', 'code_semestre_cle', 'parcours_code', 'anneeuniversitaire_annee'])
    
    errors_fk, errors_uq, errors_data, errors_other = 0, 0, 0, 0
    inscriptions_count = 0
    
    for index, row in tqdm(df_inscriptions.iterrows(), total=len(df_inscriptions), desc="Import Inscriptions"):
        
        # Le code d'inscription est la clé primaire dans la nouvelle structure
        # On génère un code robuste si la colonne 'inscription_code' n'est pas présente dans le DF
        inscription_code = safe_string(row.get('inscription_code', f"INSC_{safe_string(row['etudiant_id'])}_{index}") )
        
        try:
            # 1. Résolution des Clés Étrangères (Codes -> IDs)
            
            # Etudiant ID (Clé primaire Etudiant dans la DB)
            etudiant_id_fk = safe_string(row['etudiant_id']) 

            # Semestre ID (utilise la clé SXX)
            semestre_code = safe_string(row['code_semestre_cle']) 
            semestre_id_fk = sem_map_code_to_id.get(semestre_code)
            
            # Année Universitaire ID
            annee_annee = str(row['anneeuniversitaire_annee'])
            annee_id_fk = annee_map_annee_to_id.get(annee_annee)
            
            # Parcours ID
            parcours_code = safe_string(row['parcours_code'])
            parcours_id_fk = parc_map_code_to_id.get(parcours_code)
            
            # Mode Inscription ID (utilise le code standardisé CLAS/HYB)
            mode_code = safe_string(row['code_mode_inscription'])
            mode_id_fk = mode_map_code_to_id.get(mode_code)
            
            # Vérification des IDs critiques (obligatoires NOT NULL)
            if not all([etudiant_id_fk, semestre_id_fk, annee_id_fk, parcours_id_fk]):
                 raise ValueError(f"FK manquante pour Inscription {inscription_code}. Codes: E={etudiant_id_fk}, S={semestre_code}, A={annee_annee}, P={parcours_code}")
                
            # 2. Création de l'objet Inscription avec les IDs
            session.merge(Inscription(
                # Utilise le code comme clé primaire
                Inscription_code=inscription_code, 
                Etudiant_id_fk=etudiant_id_fk, 
                Parcours_id_fk=parcours_id_fk, 
                Semestre_id_fk=semestre_id_fk, 
                AnneeUniversitaire_id_fk=annee_id_fk, 
                ModeInscription_id_fk=mode_id_fk, 
                
                # Ajout du nouveau champ date d'inscription
                Inscription_date=datetime.now().date(), 
            ))
            
            inscriptions_count += 1
            
            # Commit par lot
            if inscriptions_count % 500 == 0:
                session.commit()
                
        # 3. Gestion des Erreurs
        except (ValueError, DataError) as e:
            session.rollback()
            errors_data += 1
            # print(f"❌ [DATA/FK] Inscription {inscription_code} : {e}")
        except IntegrityError as e:
            session.rollback()
            e_msg = str(e.orig).lower()
            if "violates foreign key constraint" in e_msg: errors_fk += 1
            elif "violates unique constraint" in e_msg or "violates not null constraint" in e_msg: errors_uq += 1
            else: errors_other += 1
        except Exception as e:
            session.rollback()
            errors_other += 1
            
    # Commit final
    try:
        session.commit()
        print("\n✅ Importation des inscriptions terminée.")
        print(f"Total des lignes traitées: {len(df_inscriptions)}")
        print(f"Total des insertions réussies: {inscriptions_count - errors_fk - errors_uq - errors_data - errors_other}")
        print(f"--- Récapitulatif des erreurs d'insertion ---")
        print(f"Erreurs Clé Étrangère (FK): {errors_fk}")
        print(f"Erreurs Unicité/Not Null (UQ): {errors_uq}")
        print(f"Erreurs Format de Données: {errors_data}")
        print(f"Autres erreurs: {errors_other}")
    except Exception as e:
        session.rollback()
        print(f"\n❌ ERREUR CRITIQUE PENDANT LE COMMIT FINAL: {e}", file=sys.stderr)

# --- Fonctions utilitaires de Mapping (Doivent être définies) ---

def _get_parcours_mapping(session: Session) -> dict:
    """Récupère le mapping CODE -> ID pour Parcours."""
    # Assurez-vous que le modèle Parcours est importé
    mapping = session.query(Parcours.Parcours_code, Parcours.Parcours_id).all()
    return {code: id_ for code, id_ in mapping}

def _get_semestre_mapping(session: Session) -> dict:
    """Récupère le mapping CODE_SEMESTRE_SIMPLE -> ID (ex: S01 -> SEME_01)."""
    # 🚨 CORRECTION : Remplacer 'Semestre_code_simple' par l'attribut réel (Ex: Semestre_code)
    mapping = session.query(Semestre.Semestre_numero, Semestre.Semestre_id).all() 
    return {code: id_ for code, id_ in mapping}

def _get_annee_mapping(session: Session) -> dict:
    """Récupère le mapping ANNEE_ACADÉMIQUE -> ID (ex: 2024 -> ANNE_2024)."""
    # Assurez-vous que le modèle AnneeUniversitaire est importé
    mapping = session.query(AnneeUniversitaire.AnneeUniversitaire_annee, AnneeUniversitaire.AnneeUniversitaire_id).all()
    # AnneeUniversitaire_annee est un entier dans le modèle, mais un string dans le mapping
    return {str(annee): id_ for annee, id_ in mapping}

def _get_mode_mapping(session: Session) -> dict:
    """Récupère le mapping CODE -> ID pour ModeInscription (ex: CLAS -> MODE_01)."""
    # 🚨 CORRECTION: Utiliser ModeInscription.ModeInscription_code au lieu de ModeInscription_label
    mapping = session.query(ModeInscription.ModeInscription_code, ModeInscription.ModeInscription_id).all()
    
    # Le mapping retourné doit être en majuscules pour correspondre au nettoyage du DataFrame
    return {code.upper(): id_ for code, id_ in mapping}

def _get_type_formation_mapping(session: Session) -> dict:
    """Récupère le mapping CODE -> ID pour TypeFormation (ex: FI -> TYPE_01)."""
    # Assurez-vous que le modèle TypeFormation est importé
    mapping = session.query(TypeFormation.TypeFormation_code, TypeFormation.TypeFormation_id).all()
    return {code: id_ for code, id_ in mapping}


# --- Orchestrateur Principal ---

def _import_inscriptions_details(
    session: Session, 
    df: pd.DataFrame, 
    parc_map_code_to_id: dict,
    sem_map_code_to_id: dict,
    annee_map_annee_to_id: dict,
    mode_map_code_to_id: dict
):
    """Importe les Inscriptions en résolvant les codes en IDs techniques (FK) et en utilisant Inscription_code comme PK."""
    print("\n--- Importation des Inscriptions Détaillées ---")
    
    # Filtre les lignes qui n'ont pas les codes essentiels pour la FK
    df_inscriptions = df.dropna(subset=['etudiant_id', 'code_semestre_cle', 'parcours_code', 'anneeuniversitaire_annee', 'inscription_code']) # 🚨 Ajout de 'inscription_code'
    
    errors_fk, errors_uq, errors_data, errors_other = 0, 0, 0, 0
    inscriptions_count = 0
    
    for index, row in tqdm(df_inscriptions.iterrows(), total=len(df_inscriptions), desc="Import Inscriptions"):
        
        # 🚨 CHANGEMENT : Utilisation directe de la colonne existante (après standardisation et dropna) 🚨
        inscription_code = safe_string(row['inscription_code'])
        
        try:
            # 1. Résolution des Clés Étrangères (Codes -> IDs)
            
            etudiant_id_fk = safe_string(row['etudiant_id']) 
            
            # Semestre ID
            semestre_code = safe_string(row['code_semestre_cle']) 
            semestre_id_fk = sem_map_code_to_id.get(semestre_code)
            
            # Année Universitaire ID
            annee_annee = str(row['anneeuniversitaire_annee'])
            annee_id_fk = annee_map_annee_to_id.get(annee_annee)
            
            # Parcours ID
            parcours_code = safe_string(row['parcours_code'])
            parcours_id_fk = parc_map_code_to_id.get(parcours_code)
            
            # Mode Inscription ID (nullable=True)
            mode_code = safe_string(row.get('code_mode_inscription'))
            mode_id_fk = mode_map_code_to_id.get(mode_code) 
            
            # Affichage des IDs résolus pour le débogage (AJOUT TEMPORAIRE)
            #print(f"DEBUG: Inscription={inscription_code} -> Etudiant_ID={etudiant_id_fk}, Semestre_ID={semestre_id_fk}, Annee_ID={annee_id_fk}, Parcours_ID={parcours_id_fk}")

            # Vérification des IDs critiques (obligatoires NOT NULL)
            missing_fks = []
            if not etudiant_id_fk: missing_fks.append('Etudiant')
            if not semestre_id_fk: missing_fks.append('Semestre')
            if not annee_id_fk: missing_fks.append('AnneeUniversitaire')
            if not parcours_id_fk: missing_fks.append('Parcours')

            if missing_fks:
                # On ne vérifie plus 'inscription_code' ici car il est filtré par df.dropna
                raise ValueError(
                    f"FK(s) manquante(s) pour Inscription {inscription_code} ({', '.join(missing_fks)}). "
                    f"Codes: E={etudiant_id_fk} ({safe_string(row['etudiant_id'])}), S={semestre_id_fk} ({semestre_code}), "
                    f"A={annee_id_fk} ({annee_annee}), P={parcours_id_fk} ({parcours_code})"
                )

            # 2. Création de l'objet Inscription avec les IDs
            session.merge(Inscription(
                # Utilise la valeur du fichier comme clé primaire
                Inscription_code=inscription_code, 
                Etudiant_id_fk=etudiant_id_fk, 
                Parcours_id_fk=parcours_id_fk, 
                Semestre_id_fk=semestre_id_fk, 
                AnneeUniversitaire_id_fk=annee_id_fk, 
                ModeInscription_id_fk=mode_id_fk, 
                
                Inscription_date=datetime.now().date(), 
            ))
            
            inscriptions_count += 1
            
            # Commit par lot
            if inscriptions_count % 500 == 0:
                session.commit()
                
        # 3. Gestion des Erreurs (maintenue)
        except (ValueError, DataError) as e:
            session.rollback()
            errors_data += 1
            print(f"❌ [DATA/FK] Inscription {inscription_code} : {e}")
        except IntegrityError as e:
            session.rollback()
            e_msg = str(e.orig).lower()
            if "violates foreign key constraint" in e_msg: errors_fk += 1
            elif "violates unique constraint" in e_msg or "violates not null constraint" in e_msg: errors_uq += 1
            else: errors_other += 1
        except Exception as e:
            session.rollback()
            errors_other += 1
            
    # Commit final
    try:
        session.commit()
        print("\n✅ Importation des inscriptions terminée.")
        print(f"Total des lignes traitées: {len(df_inscriptions)}")
        print(f"Total des insertions réussies: {inscriptions_count - errors_fk - errors_uq - errors_data - errors_other}")
        print(f"--- Récapitulatif des erreurs d'insertion ---")
        print(f"Erreurs Clé Étrangère (FK): {errors_fk}")
        print(f"Erreurs Unicité/Not Null (UQ): {errors_uq}")
        print(f"Erreurs Format de Données: {errors_data}")
        print(f"Autres erreurs: {errors_other}")
    except Exception as e:
        session.rollback()
        print(f"\n❌ ERREUR CRITIQUE PENDANT LE COMMIT FINAL: {e}", file=sys.stderr)

def import_inscriptions_to_db(session: Session):
    """
    Orchestre l'importation des données des étudiants et des inscriptions.
    Récupère les mappings nécessaires pour résoudre les clés étrangères.
    """
    print(f"\n--- 3. Démarrage de l'importation des inscriptions et étudiants ---")
    
    # 1. Chargement et Nettoyage des données
    # Assurez-vous que _load_and_clean_inscriptions() a été corrigée précédemment (sans type_formation)
    df_inscriptions = _load_and_clean_inscriptions() 
    
    if df_inscriptions is None:
        print("❌ Importation des inscriptions annulée.")
        return
        
    try:
        # 2. Récupération de tous les mappings de la DB
        print("🔗 Récupération des mappings de clés étrangères...")
        parc_map = _get_parcours_mapping(session)
        sem_map = _get_semestre_mapping(session)
        annee_map = _get_annee_mapping(session)
        mode_map = _get_mode_mapping(session)

        # Vérification minimale de la présence des mappings
        if not (parc_map and sem_map and annee_map):
            print("❌ ERREUR: Au moins un mapping essentiel (Parcours, Semestre, Année) est vide. Les références fixes n'ont peut-être pas été importées.")
            return

        # 3. Importation des Étudiants 
        _import_etudiants(session, df_inscriptions)

        # 4. Importation des Inscriptions Détaillées (toutes les FK nécessaires)
        _import_inscriptions_details(
            session, 
            df_inscriptions,
            parc_map,
            sem_map,
            annee_map,
            mode_map
        )

    except Exception as e:
        print(f"\n❌ ERREUR dans l'orchestrateur d'inscriptions : {e}", file=sys.stderr)
        session.rollback()

# ----------------------------------------------------------------------
# FONCTION DE DÉDUCTION DES LIAISONS PARCOURS <-> NIVEAU
# ----------------------------------------------------------------------

def _deduce_parcours_niveaux(session: Session):
    """
    Déduit et importe les liaisons Parcours <-> Niveau à partir 
    des inscriptions existantes. Utilise les noms d'attributs vérifiés.
    """
    print("\n--- 4. Déduction et Insertion des Liaisons Parcours <-> Niveau ---")
    
    # Dictionnaire pour trier les niveaux académiques (L1, M1, etc.)
    NIVEAU_ORDRE = {'L1': 1, 'L2': 2, 'L3': 3, 'M1': 4, 'M2': 5, 'D1': 6, 'D2': 7, 'D3': 8}
    
    try:
        # 1. Requête SQLAchemy (Inchangement de la requête)
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
        
        print(f"Trouvé {len(results)} paires uniques (Parcours, Niveau) à déduire.")

        if not results:
            print("Aucune paire Parcours/Niveau déduite des inscriptions. Importation ignorée.")
            return

        # 2. Préparation pour le tri et l'insertion
        records_to_insert = []
        parcours_niveaux_map = {}
        
        # Grouper les niveaux par parcours (stocke un set de (code, id))
        for parcours_id, niveau_id, niveau_code in results:
            if parcours_id not in parcours_niveaux_map:
                parcours_niveaux_map[parcours_id] = set()
            parcours_niveaux_map[parcours_id].add((niveau_code, niveau_id))

        # 3. Traitement, Tri et Insertion
        for parcours_id, niveaux_set in parcours_niveaux_map.items():
            niveaux_list = list(niveaux_set)
            
            # Tri des niveaux: la clé de tri est le CODE (premier élément du tuple)
            niveaux_list.sort(key=lambda item: NIVEAU_ORDRE.get(item[0], 99))
            
            for index, (niv_code, niv_id) in enumerate(niveaux_list):
                
                # 🚨 CORRECTION DÉFINITIVE : Génération d'un ID unique basé sur la clé composite
                pn_id = f"PN_{parcours_id}_{niv_id}" 
                
                records_to_insert.append(ParcoursNiveau(
                    # Clé Primaire (CP)
                    ParcoursNiveau_id=pn_id, 
                    
                    # Clés Étrangères (FK)
                    Parcours_id_fk=parcours_id,
                    Niveau_id_fk=niv_id, 
                    
                    # Attribut d'Ordre
                    ParcoursNiveau_ordre=index + 1 
                ))

        # 4. Insertion en lot
        session.bulk_save_objects(records_to_insert)
        session.commit()
        print(f"✅ Insertion de {len(records_to_insert)} liaisons ParcoursNiveau terminée.")

    except Exception as e:
        session.rollback()
        print(f"\n❌ ERREUR lors de la déduction des ParcoursNiveaux: {e}", file=sys.stderr)
        logging.error(f"DEDUCTION_PN: Erreur fatale lors de la déduction. Détail: {e}")


# ----------------------------------------------------------------------
# BLOC PRINCIPAL ET ORCHESTRATEUR GLOBAL MIS À JOUR
# ----------------------------------------------------------------------

def import_all_data():
    """
    Orchestre l'ensemble des étapes d'importation.
    """
    print("=====================================================")
    print("🚀 DÉMARRAGE DU PROCESSUS D'IMPORTATION DE DONNÉES 🚀")
    print("=====================================================")
    
    session = database_setup.get_session() 
    
    try:
        # 1. Importation des références fixes (Cycles, Niveaux, Semestres, Années)
        import_fixed_references(session)
        
        # 2. Importation de la structure académique (Institutions, Composantes, etc.)
        import_metadata_to_db(session) 
        
        # 3. Importation des étudiants et des inscriptions
        import_inscriptions_to_db(session)
        
        # 4. 🆕 DÉDUCTION ET INSERTION DE LA STRUCTURE TRANSVERSALE
        _deduce_parcours_niveaux(session)
        
        # Un commit final si tout s'est bien passé dans les orchestrateurs
        session.commit() # Les sous-fonctions ont géré les commits nécessaires

        print("\n=====================================================")
        print("✅ IMPORTATION GLOBALE TERMINÉE (Vérifiez les logs d'erreurs)")
        print("=====================================================")

    except Exception as e:
        session.rollback()
        print(f"\n❌ ERREUR FATALE dans l'orchestrateur principal: {e}", file=sys.stderr)
    finally:
        session.close()