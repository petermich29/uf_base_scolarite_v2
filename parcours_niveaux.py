from sqlalchemy.orm import Session
from tqdm import tqdm
from models import Inscription, Semestre, Niveau, ParcoursNiveau

# Ordre académique pour déterminer le champ "ordre"
ORDRE = {
    'L1': 1, 'L2': 2, 'L3': 3, 
    'M1': 4, 'M2': 5, 
    'D1': 6, 'D2': 7, 'D3': 8
}

def deduce_parcours_niveaux(session: Session):
    """
    Déduit les liaisons Parcours <-> Niveau <-> Année à partir des inscriptions existantes.
    Cette fonction remplit la table de jointure `parcours_niveaux` qui définit
    quels niveaux (L1, L2...) sont ouverts pour un parcours donné lors d'une année donnée.
    """
    print("\n--- Déduction Parcours <-> Niveaux (Basé sur les inscriptions réelles) ---")

    # 1. On interroge la BDD pour trouver quelles combinaisons existent réellement
    # Jointure : Inscription -> Semestre -> Niveau
    # IMPORTANT : On récupère aussi l'ANNEE car la relation ParcoursNiveau est historisée par année dans vos models.
    results = (
        session.query(
            Inscription.Parcours_id_fk,            # ID du parcours
            Niveau.Niveau_id,                      # ID du niveau
            Niveau.Niveau_code,                    # Code (ex: L1) pour le tri
            Inscription.AnneeUniversitaire_id_fk   # ID de l'année
        )
        .join(Semestre, Inscription.Semestre_id_fk == Semestre.Semestre_id)
        .join(Niveau, Semestre.Niveau_id_fk == Niveau.Niveau_id)
        .distinct() # On évite les doublons bruts
        .all()
    )

    if not results:
        print("⚠️ Aucune inscription trouvée. Impossible de déduire les niveaux des parcours.")
        return

    # 2. Groupement des résultats par (Parcours, Année)
    # Dictionnaire : {(parcours_id, annee_id): [(code_niv, id_niv), ...]}
    grouped = {}
    for parc_id, niv_id, niv_code, annee_id in results:
        key = (parc_id, annee_id)
        if key not in grouped:
            grouped[key] = []
        
        # On ajoute le niveau s'il n'est pas déjà dans la liste pour ce groupe
        # (Ex: Un étudiant en S1 et un autre en S2 rapportent tous les deux 'L1', on ne le veut qu'une fois)
        if (niv_code, niv_id) not in grouped[key]:
            grouped[key].append((niv_code, niv_id))

    # 3. Traitement et Insertion
    count = 0
    
    # On itère sur chaque couple (Parcours, Année)
    for (parc_id, annee_id), niveaux_list in tqdm(grouped.items(), desc="   Calcul Niveaux"):
        
        # Tri des niveaux selon l'ordre académique (L1 < L2 < M1...)
        niveaux_list.sort(key=lambda x: ORDRE.get(x[0], 999))

        for i, (code, niv_id) in enumerate(niveaux_list, start=1):
            
            # ID unique composite : PN_Parcours_Niveau_Annee
            # Nécessaire car la table ParcoursNiveau inclut l'année dans sa PK/Constraint
            pn_id = f"PN_{parc_id}_{niv_id}_{annee_id}"

            # Création de l'objet ORM
            # Utilisation de merge() : Si l'entrée existe déjà, elle est mise à jour (évite les erreurs de doublons)
            pn_obj = ParcoursNiveau(
                ParcoursNiveau_id=pn_id,
                Parcours_id_fk=parc_id,
                Niveau_id_fk=niv_id,
                AnneeUniversitaire_id_fk=annee_id, # Champ requis par votre modèle actuel
                ParcoursNiveau_ordre=i
            )
            
            session.merge(pn_obj)
            count += 1

    session.commit()
    print(f"✅ {count} relations Parcours-Niveau (par année) déduites et insérées.")