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

## Utilisation avec Claude Desktop / Claude Code

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
