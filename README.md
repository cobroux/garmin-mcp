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

> **PowerShell (Windows)** : `\` n'est pas un caractère de continuation de
> ligne comme en bash (chaque ligne serait exécutée séparément). Utilise le
> backtick `` ` `` à la place, ou mets la commande sur une seule ligne. Si ton
> mot de passe contient un `$` (ex. `$xBlackStar!21.`), utilise des guillemets
> **simples** `'...'` pour éviter que PowerShell l'interprète comme une
> variable :
>
> ```powershell
> docker run --rm -i `
>   -e GARMIN_EMAIL="ton-email@example.com" `
>   -e GARMIN_PASSWORD='ton-mot-de-passe' `
>   -v garmin-mcp-data:/data `
>   garmin-mcp
> ```

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

## Sécurité

- Les identifiants Garmin ne transitent jamais vers un tiers autre que
  Garmin Connect lui-même.
- Le token de session mis en cache (`~/.garmin_mcp_tokens`) donne accès à ton
  compte Garmin : protège ce fichier comme un mot de passe.
