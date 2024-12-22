import oracledb
import customtkinter as ctk
from tkinter import messagebox
import os

# Configuration de la connexion à la base de données Oracle
oracledb.init_oracle_client(lib_dir="C:\Program Files\Oracle\instantclient")

host = 'localhost'
port = 1521
service_name = 'XEPDB1'
user = 'system'
password = 'root'

# Créer le Data Source Name (DSN)
dsn = oracledb.makedsn(host=host, port=port, service_name=service_name)
connection = oracledb.connect(user=user, password=password, dsn=dsn)


# Vérification si la base de données est déjà configurée
def is_database_setup():
    return os.path.exists('database_config_done.txt')


def mark_database_as_setup():
    with open('database_config_done.txt', 'w') as f:
        f.write("Database setup completed.")


# Créer les types dans la base de données si nécessaire
def create_type_if_not_exists(cursor, type_name, type_definition):
    try:
        cursor.execute(f"SELECT * FROM user_types WHERE type_name = '{type_name}'")
        if cursor.fetchone() is None:
            cursor.execute(type_definition)
            print(f"Création du type {type_name} réussie.")
        else:
            print(f"Le type {type_name} existe déjà.")
    except oracledb.DatabaseError as e:
        print(f"Erreur lors de la vérification/création du type : {e}")


# Configuration de la base de données (création des types et tables)
def setup_database():
    if is_database_setup():
        print("Base de données déjà configurée.")
        return

    cursor = connection.cursor()

    # Suppression des tables et des types dans le bon ordre
    try:
        cursor.execute("DROP TABLE etudiants_tab PURGE")
    except oracledb.DatabaseError:
        pass  # La table n'existe pas encore

    try:
        cursor.execute("DROP TABLE professeurs_tab PURGE")
    except oracledb.DatabaseError:
        pass

    try:
        cursor.execute("DROP TYPE Etudiant_objet FORCE")
    except oracledb.DatabaseError:
        pass

    try:
        cursor.execute("DROP TYPE Professeur_objet FORCE")
    except oracledb.DatabaseError:
        pass

    try:
        cursor.execute("DROP TYPE Cours_liste FORCE")
    except oracledb.DatabaseError:
        pass

    try:
        cursor.execute("DROP TYPE Cours_objet FORCE")
    except oracledb.DatabaseError:
        pass

    try:
        cursor.execute("DROP TYPE Personne_objet FORCE")
    except oracledb.DatabaseError:
        pass

    # Création des types objets
    create_type_if_not_exists(cursor, "Personne_objet", """
    CREATE OR REPLACE TYPE Personne_objet AS OBJECT (
        nom VARCHAR2(50),
        prenom VARCHAR2(50),
        age NUMBER,
        email VARCHAR2(100),
        MEMBER FUNCTION afficher RETURN VARCHAR2
    ) NOT FINAL
    """)

    create_type_if_not_exists(cursor, "Cours_objet", """
    CREATE OR REPLACE TYPE Cours_objet AS OBJECT (
        code VARCHAR2(10),
        nom VARCHAR2(50),
        note NUMBER
    )
    """)

    create_type_if_not_exists(cursor, "Cours_liste", """
    CREATE OR REPLACE TYPE Cours_liste AS TABLE OF Cours_objet
    """)

    create_type_if_not_exists(cursor, "Etudiant_objet", """
    CREATE OR REPLACE TYPE Etudiant_objet UNDER Personne_objet (
        cours Cours_liste,
        OVERRIDING MEMBER FUNCTION afficher RETURN VARCHAR2,
        MEMBER FUNCTION calculer_moyenne RETURN NUMBER
    )
    """)

    create_type_if_not_exists(cursor, "Professeur_objet", """
    CREATE OR REPLACE TYPE Professeur_objet UNDER Personne_objet (
        departement VARCHAR2(50),
        OVERRIDING MEMBER FUNCTION afficher RETURN VARCHAR2
    )
    """)

    # Création des tables
    cursor.execute("""
    CREATE TABLE etudiants_tab OF Etudiant_objet
    NESTED TABLE cours STORE AS cours_ntab
    """)

    cursor.execute("""
    CREATE TABLE professeurs_tab OF Professeur_objet
    """)

    connection.commit()
    cursor.close()

    mark_database_as_setup()
    print("Base de données configurée avec succès.")


# Ajout d'un étudiant
def ajouter_etudiant(nom, prenom, age, email, cours):
    cursor = connection.cursor()
    cours_liste = [f"Cours_objet('{c[0]}', '{c[1]}', {c[2]})" for c in cours]
    cours_str = f"Cours_liste({', '.join(cours_liste)})"
    cursor.execute(f"""
    INSERT INTO etudiants_tab VALUES (
        Etudiant_objet('{nom}', '{prenom}', {age}, '{email}', {cours_str})
    )
    """)
    connection.commit()
    cursor.close()


# Ajout d'un professeur
def ajouter_professeur(nom, prenom, age, email, departement):
    cursor = connection.cursor()
    cursor.execute(f"""
    INSERT INTO professeurs_tab VALUES (
        Professeur_objet('{nom}', '{prenom}', {age}, '{email}', '{departement}')
    )
    """)
    connection.commit()
    cursor.close()


# Modification d'un étudiant
def modifier_etudiant(email, nom=None, prenom=None, age=None, cours=None):
    cursor = connection.cursor()
    update_clause = []
    if nom:
        update_clause.append(f"nom = '{nom}'")
    if prenom:
        update_clause.append(f"prenom = '{prenom}'")
    if age:
        update_clause.append(f"age = {age}")
    if cours:
        cours_liste = [f"Cours_objet('{c[0]}', '{c[1]}', {c[2]})" for c in cours]
        cours_str = f"Cours_liste({', '.join(cours_liste)})"
        update_clause.append(f"cours = {cours_str}")

    update_str = ", ".join(update_clause)
    cursor.execute(f"UPDATE etudiants_tab SET {update_str} WHERE email = '{email}'")
    connection.commit()
    cursor.close()


# Modification d'un professeur
def modifier_professeur(email, nom=None, prenom=None, age=None, departement=None):
    cursor = connection.cursor()
    update_clause = []
    if nom:
        update_clause.append(f"nom = '{nom}'")
    if prenom:
        update_clause.append(f"prenom = '{prenom}'")
    if age:
        update_clause.append(f"age = {age}")
    if departement:
        update_clause.append(f"departement = '{departement}'")

    update_str = ", ".join(update_clause)
    cursor.execute(f"UPDATE professeurs_tab SET {update_str} WHERE email = '{email}'")
    connection.commit()
    cursor.close()


# Modification d'une note
def modifier_note(email, code_cours, nouvelle_note):
    cursor = connection.cursor()
    cursor.execute("""
    SELECT cours FROM etudiants_tab WHERE email = :email
    """, email=email)
    cours_list = cursor.fetchone()[0]

    for i, cours in enumerate(cours_list):
        if cours.code == code_cours:
            cours_list[i].note = nouvelle_note
            break

    cours_str = f"Cours_liste({', '.join([f'Cours_objet({c.code}, {c.nom}, {c.note})' for c in cours_list])})"

    cursor.execute(f"""
    UPDATE etudiants_tab
    SET cours = {cours_str}
    WHERE email = :email
    """, email=email)
    connection.commit()
    cursor.close()


# Suppression d'une personne
def supprimer_personne(email, table):
    cursor = connection.cursor()
    cursor.execute(f"DELETE FROM {table} WHERE email = :email", email=email)
    connection.commit()
    cursor.close()


# Afficher les informations d'une personne
def afficher_infos(email):
    cursor = connection.cursor()
    cursor.execute("""
    SELECT p.afficher() FROM (
        SELECT * FROM etudiants_tab
        UNION ALL
        SELECT * FROM professeurs_tab
    ) p WHERE p.email = :email
    """, email=email)
    result = cursor.fetchone()
    cursor.close()
    return result[0] if result else "Personne non trouvée"


# Afficher le bulletin d'un étudiant
def afficher_bulletin(email):
    cursor = connection.cursor()
    cursor.execute("""
    SELECT e.afficher(), e.calculer_moyenne()
    FROM etudiants_tab e
    WHERE e.email = :email
    """, email=email)
    result = cursor.fetchone()
    cursor.close()
    return result if result else "Étudiant non trouvé"


# Fonction d'interface utilisateur avec CustomTkinter
def open_gui():
    def ajouter():
        nom = nom_entry.get()
        prenom = prenom_entry.get()
        age = age_entry.get()
        email = email_entry.get()
        if type_personne.get() == 'Étudiant':
            cours = [(code_entry.get(), nom_cours_entry.get(), note_entry.get())]
            ajouter_etudiant(nom, prenom, age, email, cours)
        else:
            departement = departement_entry.get()
            ajouter_professeur(nom, prenom, age, email, departement)
        messagebox.showinfo("Succès", "Ajouté avec succès")

    def modifier():
        email = email_modif_entry.get()
        if type_personne_modif.get() == 'Étudiant':
            cours = [(code_entry_modif.get(), nom_cours_entry_modif.get(), note_entry_modif.get())]
            modifier_etudiant(email, nom_entry_modif.get(), prenom_entry_modif.get(), age_entry_modif.get(), cours)
        else:
            modifier_professeur(email, nom_entry_modif.get(), prenom_entry_modif.get(), age_entry_modif.get(),
                                departement_entry_modif.get())
        messagebox.showinfo("Succès", "Modifié avec succès")

    def supprimer():
        email = email_suppr_entry.get()
        table = 'etudiants_tab' if type_suppr.get() == 'Étudiant' else 'professeurs_tab'
        supprimer_personne(email, table)
        messagebox.showinfo("Succès", "Supprimé avec succès")

    def afficher():
        email = email_affichage_entry.get()
        if type_affichage.get() == 'Informations':
            info = afficher_infos(email)
            resultat_label.config(text=info)
        else:
            info, moyenne = afficher_bulletin(email)
            resultat_label.config(text=f"{info}\nMoyenne: {moyenne}")

    # Fenêtre principale
    root = ctk.CTk()
    root.title("Gestion des étudiants et professeurs")

    # Onglets
    tab_view = ctk.CTkTabview(root)
    tab_view.pack(padx=20, pady=20)

    # Ajouter un étudiant ou professeur
    add_tab = tab_view.add("Ajouter")
    type_personne = ctk.CTkOptionMenu(add_tab, values=["Étudiant", "Professeur"])
    type_personne.pack(pady=10)

    nom_entry = ctk.CTkEntry(add_tab, placeholder_text="Nom")
    nom_entry.pack(pady=5)

    prenom_entry = ctk.CTkEntry(add_tab, placeholder_text="Prénom")
    prenom_entry.pack(pady=5)

    age_entry = ctk.CTkEntry(add_tab, placeholder_text="Âge")
    age_entry.pack(pady=5)

    email_entry = ctk.CTkEntry(add_tab, placeholder_text="Email")
    email_entry.pack(pady=5)

    departement_entry = ctk.CTkEntry(add_tab, placeholder_text="Département")
    departement_entry.pack(pady=5)

    code_entry = ctk.CTkEntry(add_tab, placeholder_text="Code du Cours")
    code_entry.pack(pady=5)

    nom_cours_entry = ctk.CTkEntry(add_tab, placeholder_text="Nom du Cours")
    nom_cours_entry.pack(pady=5)

    note_entry = ctk.CTkEntry(add_tab, placeholder_text="Note")
    note_entry.pack(pady=5)

    # Bouton pour ajouter
    add_button = ctk.CTkButton(add_tab, text="Ajouter", command=ajouter)
    add_button.pack(pady=20)

    # Modifier un étudiant ou professeur
    modif_tab = tab_view.add("Modifier")
    email_modif_entry = ctk.CTkEntry(modif_tab, placeholder_text="Email")
    email_modif_entry.pack(pady=5)

    type_personne_modif = ctk.CTkOptionMenu(modif_tab, values=["Étudiant", "Professeur"])
    type_personne_modif.pack(pady=5)

    nom_entry_modif = ctk.CTkEntry(modif_tab, placeholder_text="Nom")
    nom_entry_modif.pack(pady=5)

    prenom_entry_modif = ctk.CTkEntry(modif_tab, placeholder_text="Prénom")
    prenom_entry_modif.pack(pady=5)

    age_entry_modif = ctk.CTkEntry(modif_tab, placeholder_text="Âge")
    age_entry_modif.pack(pady=5)

    departement_entry_modif = ctk.CTkEntry(modif_tab, placeholder_text="Département")
    departement_entry_modif.pack(pady=5)

    code_entry_modif = ctk.CTkEntry(modif_tab, placeholder_text="Code du Cours")
    code_entry_modif.pack(pady=5)

    nom_cours_entry_modif = ctk.CTkEntry(modif_tab, placeholder_text="Nom du Cours")
    nom_cours_entry_modif.pack(pady=5)

    note_entry_modif = ctk.CTkEntry(modif_tab, placeholder_text="Note")
    note_entry_modif.pack(pady=5)

    modif_button = ctk.CTkButton(modif_tab, text="Modifier", command=modifier)
    modif_button.pack(pady=20)

    # Supprimer une personne
    delete_tab = tab_view.add("Supprimer")
    email_suppr_entry = ctk.CTkEntry(delete_tab, placeholder_text="Email")
    email_suppr_entry.pack(pady=5)

    type_suppr = ctk.CTkOptionMenu(delete_tab, values=["Étudiant", "Professeur"])
    type_suppr.pack(pady=5)

    delete_button = ctk.CTkButton(delete_tab, text="Supprimer", command=supprimer)
    delete_button.pack(pady=20)

    # Afficher les informations ou le bulletin
    affichage_tab = tab_view.add("Afficher")
    email_affichage_entry = ctk.CTkEntry(affichage_tab, placeholder_text="Email")
    email_affichage_entry.pack(pady=5)

    type_affichage = ctk.CTkOptionMenu(affichage_tab, values=["Informations", "Bulletin"])
    type_affichage.pack(pady=5)

    resultat_label = ctk.CTkLabel(affichage_tab, text="")
    resultat_label.pack(pady=5)

    afficher_button = ctk.CTkButton(affichage_tab, text="Afficher", command=afficher)
    afficher_button.pack(pady=20)

    root.mainloop()


# Lancer l'interface graphique
setup_database()
open_gui()
