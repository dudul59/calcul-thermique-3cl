import streamlit as st
import uuid
import pandas as pd

# ==========================================
# 1. CLASSES & MODÈLE DE DONNÉES (BACKEND)
# ==========================================

class Menuiserie:
    def __init__(self, nom, largeur, hauteur, vitrage_type):
        self.id = str(uuid.uuid4())
        self.nom = nom
        self.largeur = largeur
        self.hauteur = hauteur
        self.surface = largeur * hauteur
        self.vitrage_type = vitrage_type
        # Valeurs Ujn simplifiées pour la démo (à enrichir avec la doc 3CL)
        self.u_value = {
            "Simple vitrage": 5.8,
            "Double vitrage ancien": 2.8,
            "Double vitrage récent (VIR)": 1.4,
            "Triple vitrage": 0.8
        }.get(vitrage_type, 2.8)

class Paroi:
    def __init__(self, nom, type_paroi, longueur, hauteur_largeur, orientation, contact, annee_iso, materiau):
        self.id = str(uuid.uuid4())
        self.nom = nom
        self.type_paroi = type_paroi # MUR, PLANCHER, PLAFOND
        self.longueur = longueur
        self.hauteur_largeur = hauteur_largeur # Hauteur pour un mur, Largeur pour sol/plafond
        self.surface_brute = longueur * hauteur_largeur
        self.orientation = orientation
        self.contact = contact # EXT ou LNC (Local Non Chauffé)
        self.menuiseries = []
        
        # Simulation récupération U depuis bibliothèque selon matériaux/année
        # Ici une logique simplifiée pour l'exemple
        u_base = 2.5 # Mur non isolé
        if "Béton" in materiau: u_base = 2.3
        elif "Pierre" in materiau: u_base = 2.8
        elif "Brique" in materiau: u_base = 1.5
        
        # Facteur isolation
        facteur_iso = 1.0
        if annee_iso > 1980: facteur_iso = 0.5
        if annee_iso > 2005: facteur_iso = 0.25
        if annee_iso > 2015: facteur_iso = 0.15
        
        self.u_value = u_base * facteur_iso
        
        # Coefficient b (réduction si local non chauffé)
        self.b_coef = 0.95 if contact == "Local Non Chauffé" else 1.0

    def ajouter_menuiserie(self, menuiserie):
        self.menuiseries.append(menuiserie)

    def get_surface_vitree(self):
        return sum(m.surface for m in self.menuiseries)

    def get_surface_nette(self):
        return self.surface_brute - self.get_surface_vitree()

    def calcul_deperditions(self):
        # 1. Déperdition opaque
        dp_opaque = self.get_surface_nette() * self.u_value * self.b_coef
        # 2. Déperdition vitrée (hérite de l'orientation et b_coef du mur)
        dp_vitree = sum(m.surface * m.u_value * self.b_coef for m in self.menuiseries)
        return dp_opaque + dp_vitree

class Piece:
    def __init__(self, nom, longueur, largeur, hauteur):
        self.id = str(uuid.uuid4())
        self.nom = nom
        self.longueur = longueur
        self.largeur = largeur
        self.hauteur = hauteur
        self.surface_hab = longueur * largeur
        self.volume = self.surface_hab * hauteur
        self.murs = []
        self.planchers = []
        self.plafonds = []

    def ajouter_paroi(self, paroi):
        if paroi.type_paroi == "MUR": self.murs.append(paroi)
        elif paroi.type_paroi == "PLANCHER": self.planchers.append(paroi)
        elif paroi.type_paroi == "PLAFOND": self.plafonds.append(paroi)

class Projet:
    def __init__(self):
        self.pieces = []
        self.altitude = 0
        self.zone_climatique = "H1"
        self.annee_construction = 1990

    def calcul_global_deperditions(self):
        total_watts = 0.0
        details = []
        
        # Déperditions Parois + Vitres
        for piece in self.pieces:
            for mur in piece.murs:
                d = mur.calcul_deperditions()
                total_watts += d
                details.append({"Element": f"{piece.nom} - {mur.nom}", "Type": "Mur+Baies", "Deperdition (W/K)": d})
            for sol in piece.planchers:
                d = sol.calcul_deperditions()
                total_watts += d
                details.append({"Element": f"{piece.nom} - {sol.nom}", "Type": "Plancher", "Deperdition (W/K)": d})
            for plaf in piece.plafonds:
                d = plaf.calcul_deperditions()
                total_watts += d
                details.append({"Element": f"{piece.nom} - {plaf.nom}", "Type": "Plafond", "Deperdition (W/K)": d})

        # Calcul Automatique des Ponts Thermiques
        ponts = self.calcul_ponts_thermiques_auto()
        total_watts += ponts
        details.append({"Element": "Global", "Type": "Ponts Thermiques", "Deperdition (W/K)": ponts})

        return total_watts, details

    def calcul_ponts_thermiques_auto(self):
        # Algorithme simplifié basé sur la saisie
        psi_menuiserie = 0.1
        psi_plancher = 0.35
        psi_plafond = 0.25
        
        pertes_pt = 0.0
        longueur_murs_ext = 0.0

        for piece in self.pieces:
            for mur in piece.murs:
                # PT Menuiseries
                for fen in mur.menuiseries:
                    perimetre = (fen.largeur + fen.hauteur) * 2
                    pertes_pt += perimetre * psi_menuiserie
                
                # PT Liaisons structurelles
                if mur.contact in ["Extérieur", "Local Non Chauffé"]:
                    longueur_murs_ext += mur.longueur

        pertes_pt += longueur_murs_ext * psi_plancher
        pertes_pt += longueur_murs_ext * psi_plafond
        return pertes_pt

# ==========================================
# 2. INTERFACE UTILISATEUR (STREAMLIT)
# ==========================================

st.set_page_config(page_title="Appli 3CL DPE", layout="wide")

# Initialisation de la session (Mémoire de l'app)
if 'projet' not in st.session_state:
    st.session_state.projet = Projet()

# --- SIDEBAR : DONNÉES GÉNÉRALES ---
st.sidebar.header("🏠 Données Générales")
st.session_state.projet.zone_climatique = st.sidebar.selectbox("Zone Climatique", ["H1", "H2", "H3"])
st.session_state.projet.altitude = st.sidebar.number_input("Altitude (m)", 0, 3000, 100)
st.session_state.projet.annee_construction = st.sidebar.number_input("Année de construction", 1800, 2025, 1990)

st.sidebar.subheader("Systèmes")
ventilation = st.sidebar.selectbox("Ventilation", ["Naturelle", "VMC Simple Flux", "VMC Double Flux"])
chauffage_principal = st.sidebar.selectbox("Générateur Chauffage", ["Chaudière Gaz Standard", "Chaudière Condensation", "Pompe à Chaleur", "Électrique Direct"])

# --- PAGE PRINCIPALE : GESTION DES PIÈCES ---
st.title("Calcul Thermique - Méthode 3CL")

# Formulaire d'ajout de pièce
with st.expander("➕ Ajouter une nouvelle pièce", expanded=True):
    c1, c2, c3, c4 = st.columns(4)
    p_nom = c1.text_input("Nom de la pièce", "Salon")
    p_len = c2.number_input("Longueur (m)", 0.1, 50.0, 5.0)
    p_wid = c3.number_input("Largeur (m)", 0.1, 50.0, 4.0)
    p_h = c4.number_input("Hauteur sous plafond (m)", 1.5, 10.0, 2.5)
    
    if st.button("Créer la pièce"):
        nouvelle_piece = Piece(p_nom, p_len, p_wid, p_h)
        st.session_state.projet.pieces.append(nouvelle_piece)
        st.rerun()

st.divider()

# Affichage des pièces existantes
for i, piece in enumerate(st.session_state.projet.pieces):
    st.markdown(f"### 📍 {piece.nom} ({piece.surface_hab:.2f} m² / {piece.volume:.2f} m³)")
    
    # Onglets pour gérer les parois de la pièce
    tab_murs, tab_sols, tab_plafonds = st.tabs(["Murs & Fenêtres", "Planchers bas", "Plafonds"])
    
    # --- GESTION DES MURS ---
    with tab_murs:
        # Formulaire ajout mur
        with st.form(key=f"form_mur_{piece.id}"):
            cols = st.columns(5)
            m_nom = cols[0].text_input("Ref Mur", "Mur Nord")
            m_long = cols[1].number_input("Longueur", value=piece.longueur, key=f"ml_{piece.id}")
            m_haut = cols[2].number_input("Hauteur", value=piece.hauteur, key=f"mh_{piece.id}")
            m_orient = cols[3].selectbox("Orientation", ["Nord", "Sud", "Est", "Ouest"], key=f"mo_{piece.id}")
            m_contact = cols[4].selectbox("Contact", ["Extérieur", "Local Non Chauffé", "Intérieur (Chauffé)"], key=f"mc_{piece.id}")
            
            # Bibliothèque matériaux
            st.markdown("**Caractéristiques Constructives**")
            c_mat, c_iso = st.columns(2)
            mat_choix = c_mat.selectbox("Matériau", ["Parpaing Creux", "Brique", "Pierre", "Béton Banché"], key=f"mmat_{piece.id}")
            iso_annee = c_iso.number_input("Année Isolation (0 si aucune)", 0, 2025, 0, key=f"miso_{piece.id}")
            
            if st.form_submit_button("Ajouter ce Mur"):
                if m_contact == "Intérieur (Chauffé)":
                    st.warning("Les murs intérieurs ne comptent pas dans les déperditions.")
                else:
                    new_mur = Paroi(m_nom, "MUR", m_long, m_haut, m_orient, m_contact, iso_annee, mat_choix)
                    piece.ajouter_paroi(new_mur)
                    st.rerun()

        # Liste des murs de la pièce
        if piece.murs:
            for mur in piece.murs:
                with st.expander(f"🧱 {mur.nom} ({mur.orientation}) - Surf. Brute: {mur.surface_brute} m²", expanded=False):
                    col_info, col_fen = st.columns([1, 2])
                    
                    with col_info:
                        st.write(f"**U:** {mur.u_value:.2f} W/m².K")
                        st.write(f"**Surface Nette:** {mur.get_surface_nette():.2f} m²")
                        if st.button(f"Supprimer {mur.nom}", key=f"del_{mur.id}"):
                             piece.murs.remove(mur)
                             st.rerun()

                    # Sous-section Menuiseries (Nested Form)
                    with col_fen:
                        st.markdown("##### Menuiseries sur ce mur")
                        # Liste des fenêtres existantes
                        for fen in mur.menuiseries:
                             st.info(f"🪟 {fen.nom} - {fen.largeur}x{fen.hauteur}m - {fen.vitrage_type}")

                        # Ajout fenetre
                        c_f1, c_f2, c_f3, c_f4, c_f5 = st.columns(5)
                        f_nom = c_f1.text_input("Nom", "Fenetre 1", key=f"fn_{mur.id}")
                        f_w = c_f2.number_input("L", 0.1, 5.0, 1.0, key=f"fw_{mur.id}")
                        f_h = c_f3.number_input("H", 0.1, 5.0, 1.2, key=f"fh_{mur.id}")
                        f_type = c_f4.selectbox("Type", ["Simple vitrage", "Double vitrage ancien", "Double vitrage récent (VIR)", "Triple vitrage"], key=f"ft_{mur.id}")
                        
                        if c_f5.button("Ajouter", key=f"addf_{mur.id}"):
                            men = Menuiserie(f_nom, f_w, f_h, f_type)
                            if men.surface > mur.get_surface_nette():
                                st.error("Impossible: La fenêtre est plus grande que le mur restant !")
                            else:
                                mur.ajouter_menuiserie(men)
                                st.rerun()

    # --- GESTION PLANCHERS / PLAFONDS (Simplifié pour l'exemple) ---
    with tab_sols:
        if st.button("Ajouter Plancher Bas standard", key=f"add_sol_{piece.id}"):
            sol = Paroi("Sol", "PLANCHER", piece.longueur, piece.largeur, "N/A", "Local Non Chauffé", 1990, "Béton")
            piece.ajouter_paroi(sol)
            st.rerun()
        for sol in piece.planchers:
            st.write(f"- {sol.nom}: {sol.surface_brute} m² (U={sol.u_value})")

    with tab_plafonds:
        if st.button("Ajouter Plafond sous combles", key=f"add_plaf_{piece.id}"):
            plaf = Paroi("Plafond", "PLAFOND", piece.longueur, piece.largeur, "N/A", "Extérieur", 2000, "Placo")
            piece.ajouter_paroi(plaf)
            st.rerun()
        for plaf in piece.plafonds:
            st.write(f"- {plaf.nom}: {plaf.surface_brute} m² (U={plaf.u_value})")

# ==========================================
# 3. RÉSULTATS & CALCULS
# ==========================================

st.header("📊 Résultats de l'étude")

if st.button("Lancer le calcul 3CL"):
    deperditions_totales, details = st.session_state.projet.calcul_global_deperditions()
    
    # Affichage KPIs
    col1, col2, col3 = st.columns(3)
    col1.metric("Déperditions Enveloppe (H)", f"{deperditions_totales:.2f} W/K")
    
    # Estimation Delta T moyen (Int 19°C - Ext Hiver)
    delta_t = 19 - (-5) # Exemple pour zone H1 (-5°C de base)
    puissance = (deperditions_totales * delta_t) / 1000 # kW
    
    col2.metric("Puissance Chauffage Requise (Estimée à -5°C)", f"{puissance:.2f} kW")
    
    # Tableau détaillé
    st.subheader("Détail par poste")
    df = pd.DataFrame(details)
    st.dataframe(df, use_container_width=True)

    # Graphique simple
    if not df.empty:
        st.bar_chart(df, x="Type", y="Deperdition (W/K)")
