# Planification de la génération des loyers

La commande `python manage.py generer_loyers` peut être exécutée manuellement, mais elle est pensée pour être automatisée afin de :

- créer les échéances de loyer à l’avance,
- actualiser le statut `RETARD` pour les loyers non payés.

## Planification via cron (serveur classique Linux)

1. Activer l’environnement virtuel (si nécessaire) et utiliser des chemins absolus.

2. Ajouter une entrée à la crontab pour exécuter la commande le **1er de chaque mois à 06h00** :

   ```cron
   0 6 1 * * /chemin/vers/venv/bin/python /chemin/vers/projet/manage.py generer_loyers --verbosity 1 >> /var/log/generer_loyers.log 2>&1
