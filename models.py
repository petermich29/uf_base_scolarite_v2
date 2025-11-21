# models.py

from sqlalchemy import (
    Column, Integer, String, Date, Numeric, ForeignKey, 
    UniqueConstraint, Text, Boolean, CheckConstraint 
)
from sqlalchemy.orm import relationship, declarative_base

# Définition de la base déclarative pour SQLAlchemy
Base = declarative_base()

# ===================================================================
# --- TABLES DE RÉFÉRENCE: HIERARCHIE ADMINISTRATIVE ET ACADÉMIQUE ---
# ===================================================================

class Institution(Base):
    __tablename__ = 'institutions'
    __table_args__ = {'extend_existing': True}
    
    # Clés et identifiants
    Institution_id = Column(String(32), primary_key=True, unique=True, nullable=False) 
    
    # Attributs
    Institution_nom = Column(String(255), nullable=False, unique=True)
    Institution_type = Column(String(10), nullable=False)
    Institution_description = Column(Text, nullable=True)
    Institution_abbreviation = Column(String(20), nullable=True) # Ex: UF
    Institution_logo_path = Column(String(255), nullable=True)
    
    # Relations
    composantes = relationship("Composante", back_populates="institution")


class Composante(Base):
    __tablename__ = 'composantes'
    __table_args__ = {'extend_existing': True}
    
    # Clés et identifiants
    Composante_code = Column(String(50), primary_key=True)
    
    # Attributs
    Composante_label = Column(String(100))
    Composante_description = Column(Text, nullable=True) 
    Composante_abbreviation = Column(String(20), nullable=True) # Ex: ENI, FS, FLSH
    Composante_logo_path = Column(String(255), nullable=True)
    
    # Clé étrangère mise à jour
    Institution_id_fk = Column(
        String(32), 
        ForeignKey('institutions.Institution_id'), # Mise à jour de la FK
        nullable=False
    ) 
    
    # Relations
    institution = relationship("Institution", back_populates="composantes")
    mentions = relationship("Mention", backref="composante")
    enseignants_permanents = relationship("Enseignant", back_populates="composante_attachement")

class Domaine(Base):
    __tablename__ = 'domaines'
    __table_args__ = {'extend_existing': True}
    
    # Clés et identifiants
    Domaine_code = Column(String(20), primary_key=True)
    
    # Attributs
    Domaine_label = Column(String(100))
    Domaine_description = Column(Text, nullable=True) 
    
    # Relations
    mentions = relationship("Mention", backref="domaine")

class Mention(Base):
    __tablename__ = 'mentions'
    __table_args__ = (
        # Mise à jour de la contrainte d'unicité
        UniqueConstraint('Mention_code', 'Composante_code_fk', name='unique_mention_code_composante'),
        {'extend_existing': True}
    )
    
    # Clés et identifiants
    Mention_id = Column(String(50), primary_key=True) 
    
    # Attributs
    Mention_code = Column(String(30), nullable=False)
    Mention_label = Column(String(100))
    Mention_description = Column(Text, nullable=True) 
    Mention_abbreviation = Column(String(20), nullable=True) # Ex: MI (Maths Info), SVE (Sciences de la Vie)
    Mention_logo_path = Column(String(255), nullable=True) 
    
    # Clés étrangères mises à jour
    Composante_code_fk = Column(
        String(50), 
        ForeignKey('composantes.Composante_code'), # Mise à jour de la FK
        nullable=False
    )
    Domaine_code_fk = Column(
        String(20), 
        ForeignKey('domaines.Domaine_code'), # Mise à jour de la FK
        nullable=False
    )
    
    # Relations
    parcours = relationship("Parcours", backref="mention")

class Parcours(Base):
    __tablename__ = 'parcours'
    __table_args__ = (
        # Mise à jour de la contrainte d'unicité
        UniqueConstraint('Parcours_code', 'Mention_id_fk', name='unique_parcours_code_mention'),
        {'extend_existing': True}
    )
    
    # Clés et identifiants
    Parcours_id = Column(String(50), primary_key=True)
    
    # Attributs
    Parcours_code = Column(String(20), nullable=False)
    Parcours_label = Column(String(100))
    Parcours_description = Column(Text, nullable=True) 
    Parcours_abbreviation = Column(String(20), nullable=True) # Ex: MISS, BMC, EC
    Parcours_logo_path = Column(String(255), nullable=True)
    Parcours_date_creation = Column(Integer, nullable=True)
    Parcours_date_fin = Column(Integer, nullable=True)

    # Clés étrangères mises à jour
    Mention_id_fk = Column(
        String(50), 
        ForeignKey('mentions.Mention_id'), # Mise à jour de la FK
        nullable=False
    )

    Parcours_type_formation_defaut_fk = Column(
        String(10), 
        ForeignKey('types_formation.TypeFormation_code'), # Mise à jour de la FK
        nullable=False, 
        default='FI' 
    )

    # Relations
    type_formation_defaut = relationship("TypeFormation", back_populates="parcours")
    niveaux_couverts = relationship("ParcoursNiveau", back_populates="parcours_lie")

# -------------------------------------------------------------------
# --- TABLES DE RÉFÉRENCE: STRUCTURE LMD (CYCLE, NIVEAU, SEMESTRE) ---
# -------------------------------------------------------------------

# --- TABLES D'ASSOCIATION ---
class ParcoursNiveau(Base):
    """ Table de liaison N:M entre un Parcours et les Niveaux (L1, M1, etc.) qu'il couvre. """
    __tablename__ = 'parcours_niveaux'
    __table_args__ = (
        # Mise à jour de la contrainte d'unicité
        UniqueConstraint('Parcours_id_fk', 'Niveau_code_fk', name='uq_parcours_niveau_unique'),
        {'extend_existing': True}
    )
    
    # Clés et identifiants
    ParcoursNiveau_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Clés étrangères mises à jour
    Parcours_id_fk = Column(
        String(50), 
        ForeignKey('parcours.Parcours_id'), # Mise à jour de la FK
        nullable=False
    )
    Niveau_code_fk = Column(
        String(10), 
        ForeignKey('niveaux.Niveau_code'), # Mise à jour de la FK
        nullable=False
    )
    
    # Attributs
    ParcoursNiveau_ordre = Column(Integer, nullable=True) 

    # Relations
    parcours_lie = relationship("Parcours", back_populates="niveaux_couverts")
    niveau_lie = relationship("Niveau", back_populates="parcours_associes")

class Cycle(Base):
    __tablename__ = 'cycles'
    __table_args__ = {'extend_existing': True}
    
    # Clés et identifiants
    Cycle_code = Column(String(10), primary_key=True)
    
    # Attributs
    Cycle_label = Column(String(50), unique=True, nullable=False)
    
    # Relations
    niveaux = relationship("Niveau", back_populates="cycle")
    suivi_credits = relationship("SuiviCreditCycle", back_populates="cycle") 

class Niveau(Base):
    __tablename__ = 'niveaux'
    __table_args__ = {'extend_existing': True}
    
    # Clés et identifiants
    Niveau_code = Column(String(10), primary_key=True)
    
    # Attributs
    Niveau_label = Column(String(50)) 
    
    # Clé étrangère mise à jour
    Cycle_code_fk = Column(
        String(10), 
        ForeignKey('cycles.Cycle_code'), # Mise à jour de la FK
        nullable=False
    )
    
    # Relations
    cycle = relationship("Cycle", back_populates="niveaux")
    semestres = relationship("Semestre", back_populates="niveau")
    parcours_associes = relationship("ParcoursNiveau", back_populates="niveau_lie")
    
class Semestre(Base):
    __tablename__ = 'semestres'
    __table_args__ = (
        # Mise à jour de la contrainte d'unicité
        UniqueConstraint('Niveau_code_fk', 'Semestre_numero', name='uq_niveau_numero_semestre'), 
        {'extend_existing': True}
    )
    
    # Clés et identifiants
    Semestre_code = Column(String(10), primary_key=True) # Ex: L1_S01
    
    # Attributs
    Semestre_numero = Column(String(10), nullable=False) # Ex: S01
    
    # Clé étrangère mise à jour
    Niveau_code_fk = Column(
        String(10), 
        ForeignKey('niveaux.Niveau_code'), # Mise à jour de la FK
        nullable=False
    )
    
    # Relations
    niveau = relationship("Niveau", back_populates="semestres")
    inscriptions = relationship("Inscription", back_populates="semestre")
    unites_enseignement = relationship("UniteEnseignement", back_populates="semestre")

# -------------------------------------------------------------------
# --- TABLES DE RÉFÉRENCE: UNITÉS D'ENSEIGNEMENT ET SESSIONS ---
# -------------------------------------------------------------------

class UniteEnseignement(Base):
    __tablename__ = 'unites_enseignement'
    __table_args__ = {'extend_existing': True}
    
    # Clés et identifiants
    UE_id = Column(String(50), primary_key=True)
    
    # Attributs
    UE_code = Column(String(20), unique=True, nullable=False)
    UE_intitule = Column(String(255), nullable=False)
    UE_credit = Column(Integer, nullable=False)
    
    # Clé étrangère mise à jour
    Semestre_code_fk = Column(
        String(10), 
        ForeignKey('semestres.Semestre_code'), # Mise à jour de la FK
        nullable=False
    )
    
    # Relations
    semestre = relationship("Semestre", back_populates="unites_enseignement") 
    elements_constitutifs = relationship("ElementConstitutif", back_populates="unite_enseignement")
    resultats = relationship("ResultatUE", back_populates="unite_enseignement")


class ElementConstitutif(Base):
    __tablename__ = 'elements_constitutifs'
    __table_args__ = {'extend_existing': True}
    
    # Clés et identifiants
    EC_id = Column(String(50), primary_key=True)
    
    # Attributs
    EC_code = Column(String(20), unique=True, nullable=False)
    EC_intitule = Column(String(255), nullable=False)
    EC_coefficient = Column(Integer, default=1, nullable=False)
    
    # Clé étrangère mise à jour
    UE_id_fk = Column(
        String(50), 
        ForeignKey('unites_enseignement.UE_id'), # Mise à jour de la FK
        nullable=False
    )
    
    # Relations
    unite_enseignement = relationship("UniteEnseignement", back_populates="elements_constitutifs")
    notes = relationship("Note", back_populates="element_constitutif")
    volumes_horaires = relationship("VolumeHoraireEC", back_populates="element_constitutif")
    affectations = relationship("AffectationEC", back_populates="element_constitutif")

# ===================================================================
# --- TABLES DE RÉFÉRENCE: SESSIONS D'EXAMEN ---
# ===================================================================
class SessionExamen(Base):
    """ Table conservée pour les sessions d'examen (ex: Normale, Rattrapage) """
    __tablename__ = 'sessions_examen'
    __table_args__ = {'extend_existing': True}
    
    # Clés et identifiants
    SessionExamen_code = Column(String(5), primary_key=True) # Ex: N, R
    
    # Attributs
    SessionExamen_label = Column(String(50), nullable=False, unique=True) # Ex: Normale, Rattrapage
    
    # Relations
    notes_session = relationship("Note", back_populates="session")
    resultats_ue_session = relationship("ResultatUE", back_populates="session")
    resultats_semestre = relationship("ResultatSemestre", backref="session_resultat_semestre")


# -------------------------------------------------------------------
# --- TABLES DE RÉFÉRENCE: TYPE D'INSCRIPTION ---
# -------------------------------------------------------------------

class ModeInscription(Base): 
    __tablename__ = 'modes_inscription' 
    __table_args__ = {'extend_existing': True}
    
    # Clés et identifiants
    ModeInscription_code = Column(String(10), primary_key=True) # Ex: 'CLAS', 'HYB'
    
    # Attributs
    ModeInscription_label = Column(String(50), nullable=False, unique=True)
    ModeInscription_description = Column(Text, nullable=True) 
    
    # Relations
    inscriptions = relationship("Inscription", back_populates="mode_inscription") 

# ===================================================================
# --- TABLES DE RÉFÉRENCE: TYPE DE FORMATION ---
# ===================================================================

class TypeFormation(Base):
    __tablename__ = 'types_formation'
    __table_args__ = {'extend_existing': True}
    
    # Clés et identifiants
    TypeFormation_code = Column(String(10), primary_key=True) # Ex: FI, FC, FOAD
    
    # Attributs
    TypeFormation_label = Column(String(50), nullable=False, unique=True)
    TypeFormation_description = Column(Text, nullable=True)
    
    # Relations
    parcours = relationship("Parcours", back_populates="type_formation_defaut")
    

# ===================================================================
# --- TABLES DE DONNÉES: ÉTUDIANT, INSCRIPTION, RÉSULTATS ---
# ===================================================================

class AnneeUniversitaire(Base):
    __tablename__ = 'annees_universitaires'
    __table_args__ = {'extend_existing': True} 
    
    # Clés et identifiants
    AnneeUniversitaire_annee = Column(String(9), primary_key=True)
    
    # Attributs
    AnneeUniversitaire_description = Column(Text, nullable=True) 
    AnneeUniversitaire_ordre = Column(Integer, unique=True, nullable=False) 
    
    # Relations
    inscriptions = relationship("Inscription", back_populates="annee_univ")
    notes_obtenues = relationship("Note", back_populates="annee_univ")
    resultats_ue = relationship("ResultatUE", back_populates="annee_univ") 
    volumes_horaires_ec = relationship("VolumeHoraireEC", back_populates="annee_univ") 
    affectations_ec = relationship("AffectationEC", back_populates="annee_univ_affectation")


class Etudiant(Base):
    __tablename__ = 'etudiants'
    __table_args__ = (
        {'extend_existing': True} 
    )
    
    # Clés et identifiants
    Etudiant_code = Column(String(50), primary_key=True) 
    
    # Attributs
    Etudiant_numero_inscription = Column(String(100))
    Etudiant_nom = Column(String(100), nullable=False)
    Etudiant_prenoms = Column(String(150))
    Etudiant_sexe = Column(String(20)) 
    Etudiant_naissance_date = Column(Date, nullable=True)
    Etudiant_naissance_lieu = Column(String(100))
    Etudiant_nationalite = Column(String(50))
    Etudiant_bacc_annee = Column(Integer, nullable=True)
    Etudiant_bacc_serie = Column(String(50)) 
    Etudiant_bacc_centre = Column(String(100))
    Etudiant_adresse = Column(String(255))
    Etudiant_telephone = Column(String(50))
    Etudiant_mail = Column(String(100))
    Etudiant_cin = Column(String(100))
    Etudiant_cin_date = Column(Date, nullable=True)
    Etudiant_cin_lieu = Column(String(100))
    Etudiant_photo_profil_path = Column(String(255), nullable=True)
    Etudiant_scan_cin_path = Column(String(255), nullable=True)
    Etudiant_scan_releves_notes_bacc_path = Column(String(255), nullable=True)

    # Relations 
    inscriptions = relationship("Inscription", back_populates="etudiant")
    notes_obtenues = relationship("Note", back_populates="etudiant") 
    credits_cycles = relationship("SuiviCreditCycle", back_populates="etudiant")
    resultats_ue = relationship("ResultatUE", back_populates="etudiant") 
    resultats_semestre = relationship("ResultatSemestre", back_populates="etudiant_resultat")


class Inscription(Base):
    __tablename__ = 'inscriptions'
    __table_args__ = (
        # Mise à jour de la contrainte d'unicité
        UniqueConstraint(
            'Etudiant_code_fk', 
            'AnneeUniversitaire_annee_fk', 
            'Parcours_id_fk', 
            'Semestre_code_fk', 
            name='uq_etudiant_annee_parcours_semestre' 
        ),
        {'extend_existing': True} 
    )
    
    # Clés et identifiants
    Inscription_code = Column(String(100), primary_key=True)
    
    # Clés étrangères mises à jour
    Etudiant_code_fk = Column(
        String(50), 
        ForeignKey('etudiants.Etudiant_code'), # Mise à jour de la FK
        nullable=False
    )
    AnneeUniversitaire_annee_fk = Column(
        String(9), 
        ForeignKey('annees_universitaires.AnneeUniversitaire_annee'), # Mise à jour de la FK
        nullable=False
    )
    Parcours_id_fk = Column(
        String(50), 
        ForeignKey('parcours.Parcours_id'), # Mise à jour de la FK
        nullable=False
    )
    Semestre_code_fk = Column(
        String(10), 
        ForeignKey('semestres.Semestre_code'), # Mise à jour de la FK
        nullable=False
    )
    ModeInscription_code_fk = Column(
        String(10), 
        ForeignKey('modes_inscription.ModeInscription_code'), # Mise à jour de la FK
        nullable=False
    ) 
    
    # Attributs
    Inscription_credit_acquis_semestre = Column(Integer, default=0) 
    Inscription_is_semestre_valide = Column(Boolean, default=False) 
    
    # Relations
    etudiant = relationship("Etudiant", back_populates="inscriptions")
    annee_univ = relationship("AnneeUniversitaire", back_populates="inscriptions") 
    parcours = relationship("Parcours", backref="inscriptions")
    semestre = relationship("Semestre", back_populates="inscriptions")
    mode_inscription = relationship("ModeInscription", back_populates="inscriptions") 


class ResultatSemestre(Base):
    __tablename__ = 'resultats_semestre'
    __table_args__ = (
        # Mise à jour de la contrainte d'unicité
        UniqueConstraint(
            'Etudiant_code_fk', 
            'Semestre_code_fk', 
            'AnneeUniversitaire_annee_fk', 
            'SessionExamen_code_fk', 
            name='uq_resultat_semestre_session'
        ),
    )
    
    # Clés et identifiants
    ResultatSemestre_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Clés Étrangères mises à jour
    Etudiant_code_fk = Column(
        String(50), 
        ForeignKey('etudiants.Etudiant_code'), # Mise à jour de la FK
        nullable=False
    )
    Semestre_code_fk = Column(
        String(50), 
        ForeignKey('semestres.Semestre_code'), # Mise à jour de la FK
        nullable=False
    )
    AnneeUniversitaire_annee_fk = Column(
        String(10), 
        ForeignKey('annees_universitaires.AnneeUniversitaire_annee'), # Mise à jour de la FK
        nullable=False
    )
    SessionExamen_code_fk = Column(
        String(5), 
        ForeignKey('sessions_examen.SessionExamen_code'), # Mise à jour de la FK
        nullable=False
    )
    
    # Attributs
    ResultatSemestre_statut_validation = Column(
        String(5), 
        CheckConstraint("ResultatSemestre_statut_validation IN ('V', 'NV', 'AJ')", name='check_statut_validation'), 
        nullable=False
    )
    ResultatSemestre_credits_acquis = Column(Numeric(4, 1)) 
    ResultatSemestre_moyenne_obtenue = Column(Numeric(4, 2)) 
    
    # Relations
    etudiant_resultat = relationship("Etudiant", back_populates="resultats_semestre")
    semestre = relationship("Semestre")
    session = relationship("SessionExamen", backref="resultats_semestre") 
    annee_univ = relationship("AnneeUniversitaire") 

    def __repr__(self):
        return (f"<ResultatSemestre {self.Etudiant_code_fk} - {self.Semestre_code_fk} "
                f"(Sess: {self.SessionExamen_code_fk}, Moy: {self.ResultatSemestre_moyenne_obtenue}): {self.ResultatSemestre_statut_validation}>") 
    
class ResultatUE(Base):
    __tablename__ = 'resultats_ue'
    __table_args__ = (
        # Mise à jour de la contrainte d'unicité
        UniqueConstraint(
            'Etudiant_code_fk', 
            'UE_id_fk', 
            'AnneeUniversitaire_annee_fk', 
            'SessionExamen_code_fk', 
            name='uq_resultat_ue_unique'
        ),
    )
    
    # Clés et identifiants
    ResultatUE_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Clés Étrangères mises à jour
    Etudiant_code_fk = Column(
        String(50), 
        ForeignKey('etudiants.Etudiant_code'), # Mise à jour de la FK
        nullable=False
    )
    UE_id_fk = Column(
        String(50), 
        ForeignKey('unites_enseignement.UE_id'), # Mise à jour de la FK
        nullable=False
    )
    AnneeUniversitaire_annee_fk = Column(
        String(9), 
        ForeignKey('annees_universitaires.AnneeUniversitaire_annee'), # Mise à jour de la FK
        nullable=False
    )
    SessionExamen_code_fk = Column(
        String(5), 
        ForeignKey('sessions_examen.SessionExamen_code'), # Mise à jour de la FK
        nullable=False
    ) 
    
    # Attributs
    ResultatUE_moyenne = Column(Numeric(4, 2), nullable=False) 
    ResultatUE_is_acquise = Column(Boolean, default=False, nullable=False) 
    ResultatUE_credit_obtenu = Column(Integer, default=0, nullable=False) 

    # Relations
    etudiant = relationship("Etudiant", back_populates="resultats_ue") 
    unite_enseignement = relationship("UniteEnseignement", back_populates="resultats")
    session = relationship("SessionExamen", back_populates="resultats_ue_session") 
    annee_univ = relationship("AnneeUniversitaire", back_populates="resultats_ue")
    
    def __repr__(self):
        return (f"<ResultatUE {self.Etudiant_code_fk} - {self.UE_id_fk} "
                f"(Sess: {self.SessionExamen_code_fk}, Moy: {self.ResultatUE_moyenne}): {self.ResultatUE_is_acquise}>")

class Note(Base):
    __tablename__ = 'notes'
    __table_args__ = (
        # Mise à jour de la contrainte d'unicité
        UniqueConstraint(
            'Etudiant_code_fk', 
            'EC_id_fk', 
            'AnneeUniversitaire_annee_fk',
            'SessionExamen_code_fk',
            name='uq_etudiant_ec_annee_session' 
        ),
        {'extend_existing': True}
    )
    
    # Clés et identifiants
    Note_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Clés Étrangères Composites mises à jour
    Etudiant_code_fk = Column(
        String(50), 
        ForeignKey('etudiants.Etudiant_code'), # Mise à jour de la FK
        nullable=False
    )
    EC_id_fk = Column(
        String(50), 
        ForeignKey('elements_constitutifs.EC_id'), # Mise à jour de la FK
        nullable=False
    )
    AnneeUniversitaire_annee_fk = Column(
        String(9), 
        ForeignKey('annees_universitaires.AnneeUniversitaire_annee'), # Mise à jour de la FK
        nullable=False
    )
    SessionExamen_code_fk = Column(
        String(5), 
        ForeignKey('sessions_examen.SessionExamen_code'), # Mise à jour de la FK
        nullable=False
    )
    
    # Attributs
    Note_valeur = Column(Numeric(5, 2), nullable=False) 

    # Relations
    etudiant = relationship("Etudiant", back_populates="notes_obtenues") 
    element_constitutif = relationship("ElementConstitutif", back_populates="notes")
    annee_univ = relationship("AnneeUniversitaire", back_populates="notes_obtenues")
    session = relationship("SessionExamen", back_populates="notes_session")

    def __repr__(self):
        return (f"<Note {self.Etudiant_code_fk} - {self.EC_id_fk} "
                f"({self.AnneeUniversitaire_annee_fk}, {self.SessionExamen_code_fk}): {self.Note_valeur}>")


class SuiviCreditCycle(Base):
    __tablename__ = 'suivi_credits_cycles'
    __table_args__ = (
        # Mise à jour de la contrainte d'unicité
        UniqueConstraint('Etudiant_code_fk', 'Cycle_code_fk', name='uq_etudiant_cycle_credit'),
        {'extend_existing': True}
    )
    
    # Clés et identifiants
    SuiviCreditCycle_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Clés étrangères mises à jour
    Etudiant_code_fk = Column(
        String(50), 
        ForeignKey('etudiants.Etudiant_code'), # Mise à jour de la FK
        nullable=False
    )
    Cycle_code_fk = Column(
        String(10), 
        ForeignKey('cycles.Cycle_code'), # Mise à jour de la FK
        nullable=False
    )
    
    # Attributs
    SuiviCreditCycle_credit_total_acquis = Column(Integer, default=0, nullable=False)
    SuiviCreditCycle_is_cycle_valide = Column(Boolean, default=False) 
    
    # Relations
    etudiant = relationship("Etudiant", back_populates="credits_cycles") 
    cycle = relationship("Cycle", back_populates="suivi_credits")

# ===================================================================
# --- TABLES DE DONNÉES: ENSEIGNANT ET CHARGE D'ENSEIGNEMENT ---
# ===================================================================

class Enseignant(Base):
    __tablename__ = 'enseignants'
    __table_args__ = (
        UniqueConstraint('Enseignant_cin', name='uq_enseignant_cin', deferrable=True),
        {'extend_existing': True}
    )
    
    # Clés et identifiants
    Enseignant_id = Column(String(50), primary_key=True) 
    Enseignant_matricule = Column(String(50), unique=True, nullable=True) 

    # Attributs
    Enseignant_nom = Column(String(100), nullable=False)
    Enseignant_prenoms = Column(String(150))
    Enseignant_sexe = Column(String(20)) 
    Enseignant_date_naissance = Column(Date, nullable=True)
    Enseignant_grade = Column(String(50))
    Enseignant_statut = Column(
        String(10), 
        CheckConstraint("Enseignant_statut IN ('PERM', 'VAC')", name='check_statut_enseignant'), 
        nullable=False
    )
    
    # Clé étrangère mise à jour
    Composante_code_affectation_fk = Column(
        String(50), 
        ForeignKey('composantes.Composante_code'), # Mise à jour de la FK
        nullable=True
    )
    
    # Attributs
    Enseignant_cin = Column(String(100))
    Enseignant_cin_date = Column(Date, nullable=True)
    Enseignant_cin_lieu = Column(String(100))
    Enseignant_telephone = Column(String(50))
    Enseignant_mail = Column(String(100))
    Enseignant_rib = Column(String(100)) 
    Enseignant_photo_profil_path = Column(String(255), nullable=True)
    Enseignant_scan_cin_path = Column(String(255), nullable=True)

    # Relations
    composante_attachement = relationship("Composante", back_populates="enseignants_permanents")
    charges_enseignement = relationship("AffectationEC", back_populates="enseignant")
    presidences_jury = relationship("Jury", back_populates="enseignant_president")


class TypeEnseignement(Base):
    """ Types de charge: Cours, TD, TP """
    __tablename__ = 'types_enseignement'
    __table_args__ = {'extend_existing': True}
    
    # Clés et identifiants
    TypeEnseignement_code = Column(String(10), primary_key=True) # Ex: C, TD, TP
    
    # Attributs
    TypeEnseignement_label = Column(String(50), unique=True, nullable=False)
    
    # Relations
    volumes_horaires = relationship("VolumeHoraireEC", back_populates="type_enseignement")
    affectations = relationship("AffectationEC", back_populates="type_enseignement")


class VolumeHoraireEC(Base):
    __tablename__ = 'volume_horaire_ec'
    __table_args__ = (
        # Mise à jour de la contrainte d'unicité
        UniqueConstraint(
            'EC_id_fk', 
            'TypeEnseignement_code_fk', 
            'AnneeUniversitaire_annee_fk', 
            name='uq_ec_vh_type_annee'
        ),
        {'extend_existing': True}
    )
    
    # Clés et identifiants
    VolumeHoraireEC_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Clés étrangères mises à jour
    EC_id_fk = Column(
        String(50), 
        ForeignKey('elements_constitutifs.EC_id'), # Mise à jour de la FK
        nullable=False
    )
    TypeEnseignement_code_fk = Column(
        String(10), 
        ForeignKey('types_enseignement.TypeEnseignement_code'), # Mise à jour de la FK
        nullable=False
    )
    AnneeUniversitaire_annee_fk = Column(
        String(9), 
        ForeignKey('annees_universitaires.AnneeUniversitaire_annee'), # Mise à jour de la FK
        nullable=False
    )
    
    # Attributs
    VolumeHoraireEC_volume_heure = Column(Numeric(5, 2), nullable=False) 

    # Relations
    element_constitutif = relationship("ElementConstitutif", back_populates="volumes_horaires")
    type_enseignement = relationship("TypeEnseignement", back_populates="volumes_horaires")
    annee_univ = relationship("AnneeUniversitaire", back_populates="volumes_horaires_ec")


class AffectationEC(Base):
    __tablename__ = 'affectations_ec'
    __table_args__ = (
        # Mise à jour de la contrainte d'unicité
        UniqueConstraint(
            'EC_id_fk', 
            'TypeEnseignement_code_fk', 
            'AnneeUniversitaire_annee_fk', 
            name='uq_affectation_unique'
        ), 
        {'extend_existing': True}
    )
    
    # Clés et identifiants
    AffectationEC_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Clés étrangères mises à jour
    Enseignant_id_fk = Column(
        String(50), 
        ForeignKey('enseignants.Enseignant_id'), # Mise à jour de la FK
        nullable=False
    )
    EC_id_fk = Column(
        String(50), 
        ForeignKey('elements_constitutifs.EC_id'), # Mise à jour de la FK
        nullable=False
    )
    TypeEnseignement_code_fk = Column(
        String(10), 
        ForeignKey('types_enseignement.TypeEnseignement_code'), # Mise à jour de la FK
        nullable=False
    )
    AnneeUniversitaire_annee_fk = Column(
        String(9), 
        ForeignKey('annees_universitaires.AnneeUniversitaire_annee'), # Mise à jour de la FK
        nullable=False
    )
    
    # Attributs
    AffectationEC_volume_heure_effectif = Column(Numeric(5, 2), nullable=True) 

    # Relations
    enseignant = relationship("Enseignant", back_populates="charges_enseignement")
    element_constitutif = relationship("ElementConstitutif", back_populates="affectations")
    type_enseignement = relationship("TypeEnseignement", back_populates="affectations")
    annee_univ_affectation = relationship("AnneeUniversitaire", back_populates="affectations_ec")

# ===================================================================
# --- TABLES DE DONNÉES: GESTION DES JURYS D'EXAMEN (MODIFIÉE) ---
# ===================================================================

class Jury(Base):
    __tablename__ = 'jurys'
    __table_args__ = (
        # Mise à jour de la contrainte d'unicité
        UniqueConstraint('Semestre_code_fk', 'AnneeUniversitaire_annee_fk', name='uq_jury_unique'), 
        {'extend_existing': True}
    )
    
    # Clés et identifiants
    Jury_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Clés Étrangères Composites mises à jour
    Enseignant_id_fk = Column(
        String(50), 
        ForeignKey('enseignants.Enseignant_id'), # Mise à jour de la FK
        nullable=False
    )
    Semestre_code_fk = Column(
        String(10), 
        ForeignKey('semestres.Semestre_code'), # Mise à jour de la FK
        nullable=False
    )
    AnneeUniversitaire_annee_fk = Column(
        String(9), 
        ForeignKey('annees_universitaires.AnneeUniversitaire_annee'), # Mise à jour de la FK
        nullable=False
    )
    
    # Attributs
    Jury_date_nomination = Column(Date, nullable=True) 
    
    # Relations
    enseignant_president = relationship("Enseignant", back_populates="presidences_jury")
    semestre_jury = relationship("Semestre")
    annee_univ_jury = relationship("AnneeUniversitaire")
    
    def __repr__(self):
        return (f"<Jury Sémestre {self.Semestre_code_fk} ({self.AnneeUniversitaire_annee_fk}) "
                f"présidé par {self.Enseignant_id_fk}>")