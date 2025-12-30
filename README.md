# 🚀 DIX Platform - Scraping & Comparaison de Prix

Plateforme complète de scraping, comparaison de prix et synchronisation WooCommerce pour DIX.

---

## 📋 Vue d'ensemble

Cette plateforme automatise :
- ✅ Scraping de **Disty & Disway** (sources principales)
- ✅ Calcul des **prix DIX** avec augmentation progressive
- ✅ Scraping de **7 sites concurrents** (Crenova, Duga, LinkSolutions, Tabtel, Mies, Rightech, Joutech)
- ✅ **Comparaison** des prix DIX vs concurrence
- ✅ **Synchronisation** automatique vers WordPress/WooCommerce
- ✅ Gestion des **attributs produits** (RAM, processeur, stockage, OS, etc.)
- ✅ **Interface web** de comparaison de prix

---

## 🎯 Démarrage rapide

### 1. Vérifier les connexions
```bash
python database.py
```

### 2. Lancer le workflow complet
```bash
python workflow_master.py
```

### 3. Accéder à l'interface web
```bash
cd web_interface
python api.py
# Ouvrir index.html dans le navigateur
```

📖 **Guide complet** : Voir [QUICK_START.md](QUICK_START.md)

---

## 📁 Structure du projet

```
scrap_products_data/
├── workflow_master.py          # 🚀 Script principal d'automatisation
├── workflow_daily.bat          # 🔄 Lancement quotidien (Windows)
│
├── disty_script.py             # Scraper Disty
├── disway_script.py            # Scraper Disway
├── comparaison.py              # Comparaison et calcul prix DIX
│
├── crenova_scrap.py            # Scraper Crenova
├── duga_scrap.py               # Scraper Duga
├── linksolutions_scrap.py      # Scraper LinkSolutions
├── tabtel_scrap.py             # Scraper Tabtel
├── mies_scrap.py               # Scraper Mies
├── rightech_scrap.py           # Scraper Rightech
├── joutech_scrap.py            # Scraper Joutech
│
├── merge_scraped_data.py       # Fusion des données
├── sync_to_temp.py             # Sync vers dix_temp
├── test.py                     # Synchronisation WordPress
│
├── populate_attributes.py      # Extraction attributs
├── sync_attributes.py          # Sync attributs vers WooCommerce
├── normalize_attributes.py     # Normalisation attributs
│
├── update_categories.py        # Mise à jour catégories
├── check_brands_dix.py         # Vérification marques
│
├── database.py                 # Connecteur bases de données
├── utils.py                    # Fonctions utilitaires
│
├── web_interface/              # Interface web de comparaison
│   ├── api.py                  # API Flask
│   ├── index.html              # Interface utilisateur
│   └── README.md               # Documentation interface
│
├── debug/                      # Scripts de débogage
│   ├── check_i9_duplicates.py
│   ├── check_os_attribute.py
│   └── ...
│
├── ROADMAP.md                  # 📋 Roadmap complète
├── WORKFLOW_GUIDE.md           # 📖 Guide workflow master
├── QUICK_START.md              # ⚡ Démarrage rapide
└── requirements_api.txt        # Dépendances Python
```

---

## 🔄 Workflow automatique

Le script `workflow_master.py` exécute automatiquement :

```
1. Scraping Disty & Disway (PARALLÈLE)
   ↓
2. Comparaison (calcul prix DIX)
   ↓
3. Scraping 7 sites concurrents (PARALLÈLE)
   ↓
4. Fusion des données
   ↓
5. Synchronisation WordPress
   ↓
6. Synchronisation attributs
   ↓
7. Mise à jour catégories
```

**Durée totale : 60-120 minutes**

---

## 💰 Calcul des prix DIX

Augmentation progressive selon les tranches :

| Tranche (DH) | Augmentation |
|--------------|--------------|
| 0 - 500 | +20% |
| 500 - 1000 | +18% |
| 1000 - 2000 | +16% |
| 2000 - 5000 | +14% |
| 5000 - 10000 | +12% |
| 10000+ | +10% |

---

## 🗄️ Bases de données

Le projet utilise 4 bases de données :

1. **dix_scraper** (local) : Données scrapées
2. **dix_wp_ozar0** (distant) : WordPress/WooCommerce
3. **dix_logicom** (distant) : Données Logicom
4. **dix_temp** (distant) : Synchronisation temporaire

Configuration dans `database.py`

---

## 🌐 Interface web

L'interface web permet de :
- 📊 Voir les statistiques globales
- 🔍 Rechercher des produits
- 🎯 Filtrer (DIX moins cher / DIX plus cher)
- 📈 Comparer les prix DIX vs 7 concurrents
- 🏷️ Voir les badges de statut (Meilleur Prix / Compétitif / Cher)

**Lancement :**
```bash
cd web_interface
python api.py
# Ouvrir index.html
```

---

## 🔧 Installation

### Prérequis
- Python 3.7+
- MySQL/MariaDB
- Accès aux bases de données configurées

### Dépendances
```bash
pip install -r requirements_api.txt
```

Contient :
- Flask
- Flask-CORS
- mysql-connector-python
- BeautifulSoup4 (pour les scrapers)
- requests

---

## 🤖 Automatisation quotidienne

### Windows
1. Double-cliquer sur `workflow_daily.bat`
2. Ou configurer dans le Planificateur de tâches

### Linux/Mac
```bash
crontab -e
# Ajouter :
0 2 * * * cd /path/to/project && python3 workflow_master.py
```

---

## 🧹 Nettoyage et normalisation

⚠️ **À faire À LA FIN, après plusieurs jours de fonctionnement**

```bash
# 1. Analyser les doublons
python debug/check_i9_duplicates.py

# 2. Normaliser les attributs
python normalize_attributes.py

# 3. Fusionner les doublons
python cleanup_duplicate_terms.py

# 4. Recalculer les compteurs
python sync_attributes.py
```

---

## 📊 Logs

Chaque exécution de `workflow_master.py` génère un log :
```
workflow_log_YYYYMMDD_HHMMSS.txt
```

Contient :
- Timestamp de chaque étape
- Statut (SUCCESS/ERROR/WARNING)
- Temps d'exécution
- Résumés par phase

---

## 🐛 Dépannage

### Problème de connexion
```bash
python database.py
```

### Un scraper échoue
```bash
# Tester individuellement
python disty_script.py
```

### Les filtres ne s'affichent pas
```bash
python sync_attributes.py
```

### Voir les logs détaillés
```bash
# Consulter le dernier log
ls -lt workflow_log_*.txt | head -1
```

---

## 📚 Documentation

- **[QUICK_START.md](QUICK_START.md)** : Démarrage rapide en 3 étapes
- **[ROADMAP.md](ROADMAP.md)** : Roadmap complète phase par phase
- **[WORKFLOW_GUIDE.md](WORKFLOW_GUIDE.md)** : Guide détaillé du workflow master
- **[web_interface/README.md](web_interface/README.md)** : Documentation de l'interface web

---

## 🎯 Indicateurs de succès

- ✅ **Taux de scraping** : > 95%
- ✅ **Taux de synchronisation** : > 95%
- ✅ **Attributs complets** : > 90%
- ✅ **Uptime** : > 99%

---

## 🔐 Sécurité

⚠️ **Important** : Ne jamais commiter `database.py` avec les vrais mots de passe !

Utiliser des variables d'environnement ou un fichier `.env` (non versionné).

---

## 📝 Changelog

### Version 1.0 (2025-12-29)
- ✅ Workflow master avec parallélisation
- ✅ Scraping Disty/Disway + 7 concurrents
- ✅ Comparaison de prix avec augmentation progressive
- ✅ Synchronisation WordPress complète
- ✅ Interface web de comparaison
- ✅ Gestion des attributs et catégories
- ✅ Automatisation quotidienne

---

## 🤝 Support

Pour toute question :
1. Consulter la documentation
2. Vérifier les logs
3. Tester les connexions DB
4. Vérifier les dépendances

---

## 📄 Licence

Propriétaire - DIX Platform

---

**Prêt à lancer ?**
```bash
python workflow_master.py
```

🚀 **Bon lancement !**
