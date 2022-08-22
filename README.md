Notification d'appel sur freebox
================================

Ce projet utilise [l'API v4 de FreeboxOS](https://dev.freebox.fr/sdk/os/#=).

Quand un appel entrant est détecté sur la ligne fixe, une notification est envoyée à un des services de notification enregistré dans [Apprise](https://github.com/caronc/apprise).


Utilisation
-----------

```bash
$ python -m venv env
$ source env/bin/activate
$ pip install -r requirements.txt
# Ajouté votre service de notification au fichier notify_config.yml
$ python main.py
```

Autoriser l'association sur le panneau avant de la freebox [comme pour l'application officielle](https://assistance.free.fr/articles/associer-lapplication-freebox-a-ma-freebox-premiere-utilisation-513).

Suivez la documentation de [Apprise](https://github.com/caronc/apprise) pour ajouter votre service de notification. Modifier le fichier ```notify_config.yml```. Certains services demande l'installation de dépendances supplémentaires (comme dbus).

Les autorisations peuvent être gérées sur la freebox sur [la page dédiée](http://192.168.1.254/#Fbx.os.app.settings.Accounts).

TODO
----
* Async requests
* packaging

