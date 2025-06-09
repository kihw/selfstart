# SelfStart Plugins Directory

Ce répertoire contient les plugins installés pour SelfStart v0.3.

## Structure d'un plugin

```
plugins/
└── nom-du-plugin/
    ├── manifest.json      # Métadonnées du plugin
    ├── plugin.py          # Code principal
    ├── config.json        # Configuration
    └── requirements.txt   # Dépendances (optionnel)
```

## Plugins par défaut inclus

- `prometheus-metrics/` - Export de métriques Prometheus
- `slack-notifications/` - Notifications Slack
- `discord-webhooks/` - Webhooks Discord

Voir le guide de développement dans la documentation pour créer vos propres plugins.
