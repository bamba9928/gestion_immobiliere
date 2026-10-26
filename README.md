Cordialement,                                                                                                                        2025

Mouhamadou Bamba Dieng
Développeur Full Stack Python / Django / Javascript / html / css / tailwind / PostgreSQL / Administration Serveur etc...
Créateur de la plateforme MADA IMMO

Téléphone : +221 77 249 05 30
Email : bigrip2016@outlook.com
GitHub : https://github.com/bamba9928

MADA IMMO 🏢
MADA IMMO est une application web de gestion immobilière permettant de centraliser la gestion des biens, locataires, loyers et interventions techniques sur une seule plateforme.
Real estate / property management web app built with Django.

Fonctionnalités principales

- 👇 Gestion des biens immobiliers
  - Création / modification / suppression de biens
  - Suivi des logements disponibles ou occupés
  - Détails par bien (adresse, loyer, charges, type, etc.)

- 🧑‍💼 Gestion des locataires
  - Fiche locataire (coordonnées, historique)
  - Association locataire ↔ bien
  - Historique des contrats de location

- 💰 Gestion des loyers
  - Génération automatique des loyers (mensuelle)
  - Liste des loyers en attente / payés
  - Marquage d’un loyer comme payé
  - Génération et téléchargement de quittances de loyer (PDF)

- 🛠️ Gestion des interventions / maintenance
  - Suivi des interventions techniques sur les biens
  - Statut des interventions (en attente, en cours, résolu)
📑 Conformité et comptabilité
  - Guide intégré des bonnes pratiques comptables pour la gestion locative
  - Rappels sur les quittances, la traçabilité des dépôts de garantie et les contrôles périodiques

- 📊 Tableau de bord (Dashboard)
  - Vue synthétique des loyers à encaisser
  - Suivi des retards de paiement
  - Liste rapide des derniers biens, loyers et interventions

- 🔐 Authentification et sécurité
  - Connexion protégée (/login)
  - Accès au tableau de bord uniquement pour les utilisateurs authentifiés

Stack technique

- Backend : Django (Python)
- Frontend : Django Templates + Tailwind CSS
- JS progressif : HTMX (actions dynamiques sans rechargement complet)
- PDF : Génération de quittances (ex. via WeasyPrint ou équivalent)
- Base de données : SQLite / PostgreSQL (au choix selon config)

Structure (exemple simplifié)

mada_immo/
├─ manage.py
├─ requirements.txt
├─ mada_immo/           # Config du projet Django
└─ core/                # App principale (biens, loyers, locataires, dashboard, etc.)
   ├─ models.py
   ├─ views.py
   ├─ urls.py
   ├─ templates/
   │  ├─ base.html
   │  ├─ dashboard.html
   │  ├─ biens/
   │  ├─ loyers/
   │  └─ interventions/
   └─ static/

## Vérification des secrets avant commit

Le hook `.githooks/pre-commit` lance Gitleaks sur les modifications indexées et
bloque le commit s'il y trouve un secret (clé, jeton, mot de passe). À activer
une fois par clone, Gitleaks étant installé (`winget install gitleaks` sous
Windows) :

```bash
git config core.hooksPath .githooks
```

Faux positif vérifié : ajouter l'empreinte affichée dans `.gitleaksignore`.
