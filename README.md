# garmin-mcp

Serveur MCP (Model Context Protocol) qui expose tes données Garmin Connect
(activités, sommeil, fréquence cardiaque, stress, Body Battery, composition
corporelle, training readiness...) comme outils utilisables par Claude ou tout
autre client MCP.

Basé sur [`python-garminconnect`](https://github.com/cyberjunky/python-garminconnect)
(librairie non-officielle qui utilise l'API interne de Garmin Connect via
email/mot de passe).

## Installation

```bash
git clone https://github.com/cobroux/garmin-mcp
cd garmin-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Configuration

Le serveur a besoin de tes identifiants Garmin Connect pour la première
connexion. Ils ne sont utilisés qu'une fois : la session est ensuite mise en
cache sur disque (par défaut `~/.garmin_mcp_tokens`) et réutilisée tant
qu'elle reste valide.

Copie `.env.example` en `.env` et remplis :

```bash
cp .env.example .env
```

```
GARMIN_EMAIL=ton-email@example.com
GARMIN_PASSWORD=ton-mot-de-passe
```

> ⚠️ Ces identifiants Garmin restent en clair dans `.env` / dans la config de
> ton client MCP. Ne commit jamais ce fichier (il est dans `.gitignore`).
> Les comptes avec MFA activée ne sont pas supportés par ce flux automatique.

## Lancer avec Docker

Pas besoin d'installer Python ni les dépendances : construis l'image une fois,
puis lance-la avec une seule commande. Le volume `garmin-mcp-data` conserve le
token de session entre deux lancements (pas de nouveau login à chaque fois).

```bash
docker build -t garmin-mcp .

docker run --rm -i \
  -e GARMIN_EMAIL="ton-email@example.com" \
  -e GARMIN_PASSWORD="ton-mot-de-passe" \
  -v garmin-mcp-data:/data \
  garmin-mcp
```

Une fois le token mis en cache dans le volume, tu peux relancer sans les
variables d'environnement :

```bash
docker run --rm -i -v garmin-mcp-data:/data garmin-mcp
```

### Config Claude Desktop / Claude Code avec Docker

```json
{
  "mcpServers": {
    "garmin": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-e", "GARMIN_EMAIL",
        "-e", "GARMIN_PASSWORD",
        "-v", "garmin-mcp-data:/data",
        "garmin-mcp"
      ],
      "env": {
        "GARMIN_EMAIL": "ton-email@example.com",
        "GARMIN_PASSWORD": "ton-mot-de-passe"
      }
    }
  }
}
```

## Héberger le serveur pour l'utiliser dans claude.ai (web)

Pour ajouter ce serveur comme "Custom Connector" dans claude.ai (site web,
sans rien installer sur ta machine), il doit tourner en continu quelque part
sur internet, avec une vraie authentification OAuth. Le serveur intègre un
mini serveur d'autorisation OAuth 2.1 mono-utilisateur : une seule personne
peut s'y connecter, protégée par un mot de passe d'application que tu choisis
(`MCP_APP_PASSWORD`, différent de ton mot de passe Garmin).

⚠️ Cette page de login (`/login`) est accessible publiquement — quiconque
connaît `MCP_APP_PASSWORD` peut relier un compte claude.ai à tes données
Garmin. Choisis un mot de passe fort et garde-le secret. Les tokens émis
vivent en mémoire : un redéploiement/redémarrage du serveur invalide les
connexions actives (il suffira de reconnecter le connector sur claude.ai).

### Déploiement sur Railway

1. Sur [railway.app](https://railway.app), crée un nouveau projet →
   **Deploy from GitHub repo** → sélectionne `cobroux/garmin-mcp`. Railway
   détecte le `Dockerfile` automatiquement.
2. Dans les settings du service → **Networking** → **Generate Domain** pour
   obtenir une URL publique, par ex.
   `https://garmin-mcp-production-xxxx.up.railway.app`.
3. Dans **Variables**, ajoute :
   ```
   GARMIN_EMAIL=ton-email@example.com
   GARMIN_PASSWORD=ton-mot-de-passe-garmin
   MCP_APP_PASSWORD=choisis-un-mot-de-passe-fort-different
   MCP_PUBLIC_URL=https://garmin-mcp-production-xxxx.up.railway.app
   ```
   (remplace par l'URL générée à l'étape 2, sans slash final)
4. Redéploie (Railway le fait généralement automatiquement après l'ajout de
   variables). Vérifie que ça tourne :
   ```bash
   curl https://garmin-mcp-production-xxxx.up.railway.app/health
   # {"status":"ok"}
   ```
5. *(Optionnel mais recommandé)* Attache un **Volume** Railway monté sur
   `/data` pour que le token de session Garmin survive aux redémarrages du
   service (sinon il se reconnecte simplement avec `GARMIN_EMAIL`/
   `GARMIN_PASSWORD` à chaque cold start, ce qui reste fonctionnel).

### Ajouter le connector dans claude.ai

1. Sur claude.ai → **Settings** → **Connectors** → **Add custom connector**.
2. Entre l'URL : `https://garmin-mcp-production-xxxx.up.railway.app/mcp`.
3. claude.ai te redirige vers la page `/login` du serveur : entre le
   `MCP_APP_PASSWORD` défini plus haut.
4. Une fois autorisé, les outils Garmin apparaissent dans tes conversations
   claude.ai.

## Utilisation avec Claude Desktop / Claude Code (sans Docker)

Ajoute à ta config MCP (`claude_desktop_config.json` ou équivalent) :

```json
{
  "mcpServers": {
    "garmin": {
      "command": "/chemin/vers/garmin-mcp/.venv/bin/garmin-mcp",
      "env": {
        "GARMIN_EMAIL": "ton-email@example.com",
        "GARMIN_PASSWORD": "ton-mot-de-passe"
      }
    }
  }
}
```

Ou en local avec la CLI MCP pour tester :

```bash
mcp dev src/garmin_mcp/server.py
```

## Outils disponibles

| Outil | Description |
|---|---|
| `get_user_profile` | Profil utilisateur Garmin |
| `get_activities` | Liste des activités récentes |
| `get_activity_details` | Détails d'une activité (par id) |
| `get_daily_summary` | Résumé journalier (pas, calories, distance...) |
| `get_steps` | Pas sur une date donnée |
| `get_sleep` | Données de sommeil |
| `get_heart_rate` | Fréquence cardiaque |
| `get_stress` | Niveau de stress |
| `get_body_battery` | Body Battery |
| `get_body_composition` | Poids, masse grasse, IMC sur une période |
| `get_training_readiness` | Score de training readiness |
| `get_race_predictions` | Temps de course prédits (5K/10K/semi/marathon) |

Toutes les dates sont au format `YYYY-MM-DD` et sont optionnelles (défaut :
aujourd'hui).

## API REST multi-utilisateur (pour un backend applicatif)

En plus du serveur MCP ci-dessus (pensé pour un client comme Claude, un seul
compte Garmin via `GARMIN_EMAIL`/`GARMIN_PASSWORD`), le paquet expose une API
REST classique dans `garmin_mcp/http_api.py`, pensée pour être appelée par un
backend applicatif (ex: Oltre) où **chaque utilisateur connecte son propre
compte Garmin**.

Lancer localement :

```bash
garmin-mcp-api
# ou : uvicorn garmin_mcp.http_api:app --host 0.0.0.0 --port 8000
```

C'est aussi le point d'entrée par défaut de l'image Docker (`garmin-mcp-api`).

| Endpoint | Description |
|---|---|
| `GET /health` | Vérifie que le service tourne |
| `POST /users/{user_id}/connect` | Body `{"email": ..., "password": ...}` — connecte le compte Garmin de cet utilisateur (mot de passe jamais stocké, seule la session est mise en cache disque) |
| `GET /users/{user_id}/status` | `{"connected": true/false}` |
| `DELETE /users/{user_id}/connect` | Déconnecte et supprime la session en cache |
| `GET /users/{user_id}/activities?since=YYYY-MM-DD&limit=50` | Activités récentes, filtrées depuis une date optionnelle |
| `GET /users/{user_id}/daily-summary?date=YYYY-MM-DD` | Résumé journalier (pas, calories, distance...) |

`user_id` est un identifiant libre choisi par le service appelant (ex: l'id
utilisateur Oltre) — ce service ne fait aucune vérification d'identité
lui-même, il doit donc rester sur un réseau privé, jamais exposé
directement sur internet.

## Sécurité

- Les identifiants Garmin ne transitent jamais vers un tiers autre que
  Garmin Connect lui-même.
- Le token de session mis en cache (`~/.garmin_mcp_tokens`) donne accès à ton
  compte Garmin : protège ce fichier comme un mot de passe.
