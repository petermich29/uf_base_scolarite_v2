import pandas as pd
import sys
from sqlalchemy.orm import Session
from tqdm import tqdm

import config
from models import (
    AnneeUniversitaire, Institution, Composante, Mention, Parcours,
    InstitutionHistorique, ComposanteHistorique, MentionHistorique, ParcoursHistorique
)
from metadata_import import safe_string

def _load_excel_distinct(columns_needed):
    """
    Charge le fichier Excel en ne gardant que les colonnes nécessaires (incluant l'année)
    et retourne un DataFrame nettoyé.
    """
    try:
        df_empty = pd.read_excel(config.INSCRIPTION_FILE_PATH, nrows=0)
        file_cols = [c.lower().replace(' ', '_') for c in df_empty.columns]
        
        cols_to_load = [col for col in columns_needed if col in file_cols]
        
        # Ajout de la colonne année qui est toujours nécessaire
        if 'anneeuniversitaire_annee' not in cols_to_load and 'anneeuniversitaire_annee' in file_cols:
            cols_to_load.append('anneeuniversitaire_annee')

        print(f"   📊 Colonnes chargées pour l'historique : {cols_to_load}")

        df = pd.read_excel(config.INSCRIPTION_FILE_PATH, usecols=lambda x: x.lower().replace(' ', '_') in cols_to_load)
        df.columns = df.columns.str.lower().str.replace(' ', '_')
        
        df = df.where(pd.notnull(df), None)
        return df
    except Exception as e:
        print(f"⚠️ Impossible de lire le fichier Excel pour l'historique : {e}")
        return None

def _get_mappings(session: Session):
    """
    Récupère les mappings ID (Code -> ID) et les objets canoniques (Code -> Objet ORM)
    pour les lookups de libellés.
    """
    return {
        # Mappings IDs (Code -> ID)
        'ANNE_ID': {a.AnneeUniversitaire_annee: a.AnneeUniversitaire_id for a in session.query(AnneeUniversitaire).all()},
        'INST_ID': {i.Institution_code: i.Institution_id for i in session.query(Institution).all()},
        'COMP_ID': {c.Composante_code: c.Composante_id for c in session.query(Composante).all()},
        'MENT_ID': {m.Mention_code: m.Mention_id for m in session.query(Mention).all()},
        'PARC_ID': {p.Parcours_code: p.Parcours_id for p in session.query(Parcours).all()},

        # Mappings Objets (Code -> Objet) pour récupérer le label canonique (lookup en base)
        'INST_OBJ': {i.Institution_code: i for i in session.query(Institution).all()},
        'COMP_OBJ': {c.Composante_code: c for c in session.query(Composante).all()},
        'MENT_OBJ': {m.Mention_code: m for m in session.query(Mention).all()},
        'PARC_OBJ': {p.Parcours_code: p for p in session.query(Parcours).all()},
    }


def import_history_from_excel(session: Session):
    """
    Importe les données historiques en se basant sur le fichier Excel d'inscription.
    Utilise les libellés des tables de référence canoniques (les plus récents) 
    pour les Composantes, Mentions et Parcours (où le label historique manque dans la source).
    """
    print("\n--- 5. Importation des Historiques (Lookup des labels en Base) ---")
    
    # 1. Configuration des colonnes nécessaires pour charger le DataFrame
    cols_to_load_for_df = [
        'institution_code', 'institution_nom', 
        'composante_code', 
        'mention_abbreviation', 
        'parcours_code' 
    ]

    df = _load_excel_distinct(cols_to_load_for_df)
    if df is None or df.empty:
        print("⚠️ Fichier vide ou illisible pour l'historique.")
        return

    # 2. Préparation du DataFrame : Génération des codes
    # Le code de la mention est une concaténation
    df['mention_code'] = df.apply(
        lambda row: f"{safe_string(row['composante_code'])}_{safe_string(row['mention_abbreviation'])}" 
                    if safe_string(row['composante_code']) and safe_string(row['mention_abbreviation'])
                    else None, 
        axis=1
    )

    # 3. Mappings (incluant les objets canoniques pour le lookup de label)
    print("   🔄 Chargement des références depuis la base de données...")
    maps = _get_mappings(session)

    # 4. Définition des entités à traiter
    # Ajout de 'canonical_label_attr' pour cibler le bon champ dans models.py
    entities_config = [
        {
            'type': 'INST', 'code_col': 'institution_code', 
            'map_id': 'INST_ID', 'map_obj': 'INST_OBJ', 
            'orm_class': InstitutionHistorique, 'fk_field': 'Institution_id_fk', 
            'label_field': 'Institution_nom_historique', 'code_hist_field': 'Institution_code_historique',
            'label_source_col': 'institution_nom', # Priorité Excel
            'canonical_label_attr': 'Institution_nom' # Fallback DB
        },
        {
            'type': 'COMP', 'code_col': 'composante_code', 
            'map_id': 'COMP_ID', 'map_obj': 'COMP_OBJ', 
            'orm_class': ComposanteHistorique, 'fk_field': 'Composante_id_fk', 
            'label_field': 'Composante_label_historique', 'code_hist_field': 'Composante_code_historique',
            'label_source_col': None, 
            'canonical_label_attr': 'Composante_label' # <-- CORRECTION : Nom exact dans models.py
        },
        {
            'type': 'MENT', 'code_col': 'mention_code', 
            'map_id': 'MENT_ID', 'map_obj': 'MENT_OBJ', 
            'orm_class': MentionHistorique, 'fk_field': 'Mention_id_fk', 
            'label_field': 'Mention_label_historique', 'code_hist_field': 'Mention_code_historique',
            'label_source_col': None,
            'canonical_label_attr': 'Mention_label' # <-- CORRECTION : Nom exact dans models.py
        },
        {
            'type': 'PARC', 'code_col': 'parcours_code', 
            'map_id': 'PARC_ID', 'map_obj': 'PARC_OBJ', 
            'orm_class': ParcoursHistorique, 'fk_field': 'Parcours_id_fk', 
            'label_field': 'Parcours_label_historique', 'code_hist_field': 'Parcours_code_historique',
            'label_source_col': None,
            'canonical_label_attr': 'Parcours_label' # <-- CORRECTION : Nom exact dans models.py
        }
    ]

    # 5. Boucle de traitement par entité
    for ent in entities_config:
        print(f"   ↳ Traitement historique : {ent['type']}...")
        
        code_col = ent['code_col']
        
        # Sélection des colonnes nécessaires pour le regroupement
        cols_group = ['anneeuniversitaire_annee', code_col]
        
        # On ajoute la colonne du label source si elle est définie
        cols_select = cols_group[:]
        if ent['label_source_col']:
            cols_select.append(ent['label_source_col'])
        
        # Nettoyage
        sub_df = df[cols_select].drop_duplicates(subset=cols_group).dropna(subset=cols_group)

        count = 0
        updated = 0
        
        for _, row in tqdm(sub_df.iterrows(), total=len(sub_df), desc=f"   {ent['type']}-Histo"):
            annee_val = str(row['anneeuniversitaire_annee'])
            code_val = safe_string(row[code_col])
            
            # 1. Résolution des IDs (doit exister dans les tables de référence)
            annee_id = maps['ANNE_ID'].get(annee_val)
            entity_id = maps[ent['map_id']].get(code_val)
            
            if annee_id and entity_id:
                
                label_val = "NON_DEFINI" # Valeur par défaut
                
                # A. Essai via Excel (si configuré et présent)
                if ent['label_source_col'] and ent['label_source_col'] in row:
                    val_excel = safe_string(row[ent['label_source_col']])
                    if val_excel:
                        label_val = val_excel
                
                # B. Essai via DB (Lookup sur l'objet canonique) si Excel a échoué ou n'est pas configuré
                if label_val == "NON_DEFINI" or label_val is None:
                    canonical_obj = maps[ent['map_obj']].get(code_val)
                    if canonical_obj:
                        # On récupère l'attribut spécifique défini dans la config
                        target_attr = ent.get('canonical_label_attr')
                        db_label = getattr(canonical_obj, target_attr, None)
                        if db_label:
                            label_val = db_label
                    else:
                        label_val = f"{ent['type']}_CODE_INCONNU_EN_BASE"

                # 3. Création objet historique
                hist_obj = ent['orm_class'](
                    AnneeUniversitaire_id_fk=annee_id,
                    **{
                        ent['fk_field']: entity_id,
                        ent['label_field']: label_val,
                        ent['code_hist_field']: code_val
                    }
                )
                session.merge(hist_obj)
                count += 1
        
        session.commit()
        print(f"      ✅ {count} entrées insérées/mises à jour pour {ent['type']}.")

    print("\n--- ❗ Note Importation Historique ---")
    print("✅ Les libellés historiques manquants ont été récupérés depuis les tables de référence actuelles.")
    print("✅ Fin de l'importation des historiques.")