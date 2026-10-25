#!/bin/bash
# Déploiement de madagroupe.com.
#
# Lancé par /home/mada/deploy_madagroupe.sh (hors dépôt), lui-même appelé par
# GitHub Actions (.github/workflows/ci.yml) via une clé SSH restreinte. Le
# lanceur a déjà mis le code à jour (git reset sur origin/main).
set -euo pipefail

APP_DIR=/home/mada/apps/gestion_immobiliere
cd "$APP_DIR"

echo "--- Début du déploiement : $(date) ---"
git log --oneline -1

source venv/bin/activate
pip install --disable-pip-version-check -r requirements.txt

# Les migrations se génèrent en local et se commitent ; ici on ne fait que
# les appliquer. Penser à un dump avant une migration risquée.
python manage.py migrate --noinput

# Le CSS Tailwind (theme/static/css/dist/) est compilé et commité : pas de
# build npm sur le serveur.
python manage.py collectstatic --noinput

# gunicorn tourne sous svc-madagroupe : seul un restart via sudo est possible
# (sudoers : NOPASSWD pour « systemctl restart madagroupe »).
sudo -n systemctl restart madagroupe

for _ in 1 2 3 4 5 6 7 8 9 10; do
    systemctl is-active --quiet madagroupe && break
    sleep 2
done
if ! systemctl is-active --quiet madagroupe; then
    echo "madagroupe ne tourne pas après le redémarrage" >&2
    systemctl status madagroupe --no-pager -n 20 >&2 || true
    exit 1
fi

echo "--- Déploiement terminé ---"
