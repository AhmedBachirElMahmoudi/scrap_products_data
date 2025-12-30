# 🚀 WORKFLOW MASTER - Guide d'utilisation

## 📋 Description

Le **Workflow Master** est un système d'automatisation complet qui orchestre tous les processus de scraping, comparaison et synchronisation de la plateforme DIX.

## 🎯 Fonctionnalités

### Exécution automatique de toutes les phases :

1. **Phase 1** : Scraping Disty & Disway (en parallèle)
2. **Phase 2** : Comparaison et calcul des prix DIX avec augmentation progressive
3. **Phase 3** : Scraping des 7 sites concurrents (en parallèle)
4. **Phase 4** : Fusion des données (DIX + 7 concurrents)
5. **Phase 5** : Synchronisation vers dix_temp
6. **Phase 6** : Synchronisation WordPress (produits)
7. **Phase 7** : Synchronisation des attributs
8. **Phase 8** : Mise à jour des catégories

### Avantages :

- ✅ **Parallélisation** : Disty/Disway en même temps, puis les 7 sites en même temps
- ✅ **Logs détaillés** : Sauvegarde automatique des logs avec timestamp
- ✅ **Gestion d'erreurs** : Continue même si un scraper échoue
- ✅ **Résumés** : Statistiques après chaque phase
- ✅ **Temps d'exécution** : Suivi du temps pour chaque étape

## 🚀 Utilisation

### Méthode 1 : Lancement manuel

```bash
python workflow_master.py
```

Le script vous demandera confirmation avant de démarrer.

### Méthode 2 : Lancement via batch (Windows)

Double-cliquez sur `workflow_daily.bat` ou exécutez :

```bash
workflow_daily.bat
```

### Méthode 3 : Automatisation quotidienne

#### Windows (Task Scheduler)

1. Ouvrir le **Planificateur de tâches**
2. Créer une nouvelle tâche
3. **Déclencheur** : Tous les jours à 2h00 du matin
4. **Action** : Démarrer un programme
   - Programme : `C:\Users\dell\Documents\GitHub\scrap_products_data\workflow_daily.bat`
5. **Conditions** : 
   - ☑ Démarrer uniquement si l'ordinateur est sur secteur
   - ☑ Réveiller l'ordinateur pour exécuter cette tâche

#### Linux/Mac (Cron)

Ajouter au crontab :

```bash
crontab -e
```

Ajouter la ligne :

```bash
0 2 * * * cd /path/to/scrap_products_data && python3 workflow_master.py >> workflow_cron.log 2>&1
```

## 📊 Logs

Chaque exécution génère un fichier de log :

```
workflow_log_YYYYMMDD_HHMMSS.txt
```

Exemple : `workflow_log_20251229_020000.txt`

Le log contient :
- Timestamp de chaque étape
- Statut (SUCCESS/ERROR/WARNING)
- Temps d'exécution de chaque script
- Résumés par phase
- Résumé final

## 🔧 Configuration

### Modifier les scripts exécutés

Éditez `workflow_master.py` et modifiez les listes de scripts dans chaque phase.

### Ajouter un nouveau site concurrent

1. Ajoutez le script dans `phase3_scripts` :

```python
phase3_scripts = [
    ("crenova_scrap.py", "Scraping CRENOVA"),
    ("duga_scrap.py", "Scraping DUGA"),
    # ... autres sites ...
    ("nouveau_site_scrap.py", "Scraping NOUVEAU SITE"),  # ← Ajouter ici
]
```

### Désactiver une phase

Commentez la section de la phase dans `run_full_workflow()` :

```python
# ========================================
# PHASE 8: Mise à jour des catégories (DÉSACTIVÉE)
# ========================================
# success8a = self.run_script_sequential(
#     "update_categories.py",
#     "PHASE 8a - Mise à jour des catégories"
# )
```

## ⚠️ Points d'attention

### Avant le premier lancement :

1. **Vérifier les connexions DB**
   ```bash
   python database.py
   ```

2. **Tester un scraper individuellement**
   ```bash
   python disty_script.py
   ```

3. **Vérifier que test.py est en mode main()**
   
   Dans `test.py` ligne 1215, assurez-vous que :
   ```python
   if __name__ == "__main__":
       main()  # ← Décommenté
       # test_single_product("...") # ← Commenté
   ```

### Pendant l'exécution :

- **Ne pas interrompre** pendant les phases de synchronisation WordPress
- **Surveiller les logs** pour détecter les erreurs
- **Vérifier l'espace disque** (les logs peuvent être volumineux)

### Après l'exécution :

- **Vérifier le site WordPress** : produits, prix, attributs
- **Consulter les logs** pour les erreurs
- **Vérifier l'interface web** de comparaison

## 📈 Temps d'exécution estimé

| Phase | Durée estimée |
|-------|---------------|
| Phase 1 (Disty/Disway) | 10-20 min |
| Phase 2 (Comparaison) | 2-5 min |
| Phase 3 (7 sites) | 15-30 min |
| Phase 4 (Fusion) | 2-5 min |
| Phase 5 (Sync temp) | 1-2 min |
| Phase 6 (WordPress) | 20-40 min |
| Phase 7 (Attributs) | 10-15 min |
| Phase 8 (Catégories) | 2-5 min |
| **TOTAL** | **60-120 min** |

*Les durées varient selon le nombre de produits et la vitesse réseau*

## 🐛 Dépannage

### Le workflow s'arrête à la Phase 1

**Problème** : Erreur de connexion à la base de données

**Solution** :
```bash
python database.py  # Tester les connexions
```

### Un scraper échoue systématiquement

**Problème** : Le site a changé sa structure HTML

**Solution** :
1. Tester le scraper individuellement
2. Vérifier les sélecteurs CSS/XPath
3. Mettre à jour le scraper

### La synchronisation WordPress est lente

**Problème** : Trop de produits à synchroniser

**Solution** :
1. Augmenter le `connection_timeout` dans `database.py`
2. Optimiser les requêtes SQL dans `test.py`
3. Activer le mode batch

### Les logs sont trop volumineux

**Problème** : Accumulation de fichiers de logs

**Solution** :
```bash
# Supprimer les logs de plus de 30 jours
find . -name "workflow_log_*.txt" -mtime +30 -delete
```

## 📞 Support

Pour toute question ou problème :

1. Consulter les logs détaillés
2. Vérifier les scripts individuellement
3. Tester les connexions DB
4. Vérifier les dépendances Python

## 🔄 Mises à jour

### Version 1.0 (2025-12-29)
- ✅ Lancement initial
- ✅ Parallélisation Disty/Disway
- ✅ Parallélisation des 7 sites
- ✅ Logs détaillés
- ✅ Gestion d'erreurs

### Prochaines améliorations
- [ ] Notifications par email
- [ ] Dashboard de monitoring
- [ ] Retry automatique en cas d'erreur
- [ ] Backup automatique avant synchronisation
- [ ] Mode "dry-run" (simulation)

---

**Auteur** : DIX Platform Team  
**Dernière mise à jour** : 29 décembre 2025
