# SelfStart Data Directory

Ce répertoire contient toutes les données persistantes de SelfStart v0.3.

## Structure

```
data/
├── backups/          # Sauvegardes automatiques
├── logs/             # Logs applicatifs
├── metrics/          # Métriques historiques
├── webhooks.db       # Base SQLite pour webhooks
├── autoshutdown.db   # Base SQLite pour auto-shutdown
├── plugins.db        # Base SQLite pour plugins
└── celerybeat-schedule # Planning Celery
```

## Permissions

Assurez-vous que ce répertoire est accessible en écriture par l'utilisateur Docker (PUID/PGID).

## Sauvegarde

Ce répertoire doit être inclus dans vos sauvegardes régulières.
