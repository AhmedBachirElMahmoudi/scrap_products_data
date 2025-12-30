# 🚀 ROADMAP DE LANCEMENT - Plateforme DIX

**Date de création** : 29 décembre 2025  
**Version** : 1.0

---

## 📊 Vue d'ensemble du projet

Plateforme complète de **scraping, comparaison de prix et synchronisation WooCommerce** qui :
- Scrape Disty & Disway (sources principales)
- Calcule les prix DIX avec augmentation progressive
- Scrape 7 sites concurrents (Crenova, Duga, LinkSolutions, Tabtel, Mies, Rightech, Joutech)
- Compare les prix DIX avec la concurrence
- Synchronise automatiquement vers WordPress/WooCommerce
- Gère les attributs produits (RAM, processeur, stockage, OS, etc.)
- Fournit une interface web de comparaison

---

## 🎯 PHASE 1 : PRÉPARATION (Jour 1)

### ✅ 1.1 Vérification de l'infrastructure

**Actions :**
```bash
python database.py
```

**Vérifications :**
- [ ] Connexion à `dix_scraper` (local)
- [ ] Connexion à `dix_wp_ozar0` (distant)
- [ ] Connexion à `dix_logicom` (distant)
- [ ] Connexion à `dix_temp` (distant)

**Critères de succès :**
- ✅ Toutes les connexions fonctionnent
- ✅ Pas d'erreurs de timeout

---

### ✅ 1.2 Vérification de test.py

**Actions :**
- [ ] Ouvrir `test.py` ligne 1215
- [ ] Vérifier que `main()` est décommenté pour la synchronisation complète

```python
if __name__ == "__main__":
    main()  # ← Décommenter pour synchronisation complète
    # test_single_product("...") # ← Commenter
```

**Critères de succès :**
- ✅ Configuration correcte pour synchronisation automatique

---

## 🔄 PHASE 2 : SCRAPING DISTY & DISWAY (Semaine 1)

### ✅ 2.1 Scraping des sources principales (EN PARALLÈLE)

**Méthode 1 : Automatique avec workflow_master.py**
```bash
python workflow_master.py
# Le script lance automatiquement Disty et Disway en parallèle
```

**Méthode 2 : Manuel avec app.py**
```bash
python app.py
# Choisir option 1 (parallèle)
```

**Méthode 3 : Individuel**
```bash
python disty_script.py
python disway_script.py
```

**Vérifications :**
- [ ] Nombre de produits scrapés (Disty)
- [ ] Nombre de produits scrapés (Disway)
- [ ] Données dans `dix_disty_*` et `dix_disway_*`
- [ ] Prix, stocks, attributs bruts extraits

**Critères de succès :**
- ✅ Scraping Disty complet
- ✅ Scraping Disway complet
- ✅ Données sauvegardées dans `dix_scraper`
- ✅ Taux de succès > 90%

---

## 💰 PHASE 3 : COMPARAISON ET CALCUL DES PRIX DIX (Semaine 1)

### ✅ 3.1 Calcul des prix DIX avec augmentation progressive

**Actions :**
```bash
python comparaison.py
```

**Ce que fait le script :**
- Lit les données depuis `dix_disty_*` et `dix_disway_*`
- Applique l'augmentation progressive :
  - 0-500 DH : +20%
  - 500-1000 DH : +18%
  - 1000-2000 DH : +16%
  - 2000-5000 DH : +14%
  - 5000-10000 DH : +12%
  - 10000+ DH : +10%
- Calcule les réductions (wholesale_price - price)
- Sauvegarde dans `ps_products_comparison` et `ps_products_comparison_v2`

**Vérifications :**
- [ ] Table `ps_products_comparison` remplie
- [ ] Table `ps_products_comparison_v2` remplie
- [ ] Prix DIX = prix source × multiplicateur
- [ ] Réductions calculées correctement

**Critères de succès :**
- ✅ Prix DIX calculés avec augmentation progressive
- ✅ Tables remplies correctement

---

## 🔍 PHASE 4 : SCRAPING DES 7 SITES CONCURRENTS (Semaine 2)

### ✅ 4.1 Scraping des concurrents (EN PARALLÈLE)

**Méthode 1 : Automatique avec workflow_master.py**
```bash
python workflow_master.py
# Le script lance automatiquement les 7 sites en parallèle
```

**Méthode 2 : Individuel**
```bash
python crenova_scrap.py
python duga_scrap.py
python linksolutions_scrap.py
python tabtel_scrap.py
python mies_scrap.py
python rightech_scrap.py
python joutech_scrap.py
```

**Vérifications :**
- [ ] Données dans les tables respectives
- [ ] Prix extraits pour chaque site
- [ ] Stocks extraits
- [ ] Attributs extraits

**Critères de succès :**
- ✅ Tous les sites scrapés
- ✅ Données dans `dix_scraper`
- ✅ Taux de succès > 90%

---

## 🔀 PHASE 5 : FUSION DES DONNÉES (Semaine 2)

### ✅ 5.1 Fusion de toutes les données (DIX + 7 concurrents)

**Actions :**
```bash
python merge_scraped_data.py
```

**Ce que fait le script :**
- Fusionne les données de Disty, Disway et des 7 sites concurrents
- Regroupe les produits par référence
- Compare les prix DIX (déjà calculés) avec les prix concurrents
- Met à jour `ps_products_comparison_v2` avec tous les prix

**Vérifications :**
- [ ] Produits regroupés par référence
- [ ] Correspondances entre sites vérifiées
- [ ] Prix concurrents ajoutés à la table
- [ ] Meilleur prix identifié pour chaque produit

**Critères de succès :**
- ✅ Données fusionnées correctement
- ✅ Table `ps_products_comparison_v2` complète avec 8 colonnes de prix

---

## 🛒 PHASE 6 : SYNCHRONISATION WORDPRESS (Semaine 3)

### ✅ 6.1 Synchronisation vers dix_temp

**Actions :**
```bash
python sync_to_temp.py
```

**Vérifications :**
- [ ] Données copiées dans `dix_temp.ps_products_comparison`

**Critères de succès :**
- ✅ Données dans `dix_temp`

---

### ✅ 6.2 Test avec UN produit (RECOMMANDÉ)

**Actions :**
- [ ] Modifier `test.py` ligne 1215
```python
test_single_product("REFERENCE_TEST")  # Remplacer par une vraie référence
```
- [ ] Exécuter
```bash
python test.py
```

**Vérifications dans WordPress :**
- [ ] Produit créé/mis à jour
- [ ] Prix DIX correct (avec augmentation)
- [ ] Stock correct
- [ ] Catégorie assignée
- [ ] Marque assignée
- [ ] Attributs bruts présents

**Critères de succès :**
- ✅ Produit test synchronisé correctement
- ✅ Tous les champs remplis

---

### ✅ 6.3 Synchronisation complète

**Actions :**
- [ ] Modifier `test.py` pour activer `main()`
```python
if __name__ == "__main__":
    main()  # Décommenter
    # test_single_product("...") # Commenter
```
- [ ] Lancer
```bash
python test.py
```

**Surveillance :**
- Suivre les logs en temps réel
- Noter les erreurs
- Vérifier le nombre de produits :
  - Nouveaux (insertions)
  - Mis à jour (updates)
  - En erreur

**Critères de succès :**
- ✅ Tous les produits synchronisés
- ✅ Taux d'erreur < 5%
- ✅ Produits visibles sur WordPress

---

### ✅ 6.4 Peupler les attributs manquants

**Actions :**
```bash
python populate_attributes.py
```

**Vérifications :**
- [ ] Attributs extraits depuis les descriptions
- [ ] Attributs ajoutés à la base de données

**Critères de succès :**
- ✅ Attributs extraits pour > 90% des produits

---

### ✅ 6.5 Synchroniser les attributs vers WooCommerce

**Actions :**
```bash
python sync_attributes.py
```

**Vérifications :**
- [ ] Attributs apparaissent dans WordPress
- [ ] Taxonomies créées (`pa_ram`, `pa_processeur`, `pa_stockage`, etc.)
- [ ] Termes créés pour chaque valeur d'attribut

**Critères de succès :**
- ✅ Attributs synchronisés
- ✅ Taxonomies créées

---

### ✅ 6.6 Gestion des catégories

**Actions :**
```bash
python update_categories.py
python check_categories_dix.py  # Vérification
```

**Critères de succès :**
- ✅ Produits dans les bonnes catégories
- ✅ Hiérarchie respectée

---

### ✅ 6.7 Gestion des marques

**Actions :**
```bash
python check_brands_dix.py
python check_brand_link.py
```

**Critères de succès :**
- ✅ Toutes les marques assignées
- ✅ Filtres par marque fonctionnels

---

## 🌐 PHASE 7 : INTERFACE WEB DE COMPARAISON (Semaine 4)

### ✅ 7.1 Installation des dépendances

**Actions :**
```bash
pip install -r requirements_api.txt
```

**Critères de succès :**
- ✅ Flask, Flask-CORS, mysql-connector-python installés

---

### ✅ 7.2 Déploiement de l'API

**Actions :**
```bash
cd web_interface
python api.py
```

**Vérifications :**
- [ ] API accessible sur http://localhost:5000
- [ ] Test des endpoints :
  - `GET /api/products`
  - `GET /api/products/search?q=test`
  - `GET /api/products/cheaper`
  - `GET /api/products/expensive`
  - `GET /api/stats`

**Critères de succès :**
- ✅ API accessible
- ✅ Tous les endpoints répondent

---

### ✅ 7.3 Test de l'interface web

**Actions :**
- [ ] Ouvrir `web_interface/index.html` dans un navigateur
- [ ] Tester :
  - Statistiques globales
  - Filtres (Tous / DIX moins cher / DIX plus cher)
  - Recherche par référence/titre
  - Affichage des 8 colonnes de prix
  - Badges de statut

**Critères de succès :**
- ✅ Interface fonctionnelle
- ✅ Comparaison visible entre DIX et les 7 concurrents
- ✅ Interface responsive

---

## 🧹 PHASE 8 : NETTOYAGE ET NORMALISATION (Semaine 5) ⚠️ **À LA FIN**

### ✅ 8.1 Analyse des doublons

**Actions :**
```bash
python debug/check_i9_duplicates.py
python debug/check_os_attribute.py
python debug/compare_category_attributes.py
```

**Critères de succès :**
- ✅ Liste complète des doublons identifiés

---

### ✅ 8.2 Normalisation des attributs

**Actions :**
```bash
python normalize_attributes.py
```

**Exemples de normalisation :**
- "Intel Core i9" et "Intel® Core™ i9" → "Intel Core i9"
- "16 Go RAM" et "16 Go" → "16 Go"
- "Windows 11 Pro" et "Windows 11 Professionnel" → "Windows 11 Pro"

**Critères de succès :**
- ✅ Attributs normalisés
- ✅ Pas de doublons

---

### ✅ 8.3 Fusion des termes dupliqués

**Actions :**
```bash
python debug/merge_i9_duplicates.py
python cleanup_duplicate_terms.py
```

**Critères de succès :**
- ✅ Termes fusionnés dans WooCommerce

---

### ✅ 8.4 Recalcul des compteurs et reconstruction

**Actions :**
```bash
python sync_attributes.py
```

**Ce que fait le script :**
- Exécute `recalculate_term_counts()`
- Exécute `fix_lookup_table()`

**Vérifications :**
- [ ] Compteurs dans `wp_term_taxonomy` corrects
- [ ] Table `wp_wc_product_attributes_lookup` reconstruite
- [ ] Filtres visibles sur le site

**Critères de succès :**
- ✅ Compteurs corrects
- ✅ Table lookup reconstruite
- ✅ Filtres visibles et fonctionnels

---

### ✅ 8.5 Corrections finales

**Actions :**
```bash
python fix_attributes_after_normalize.py
python fix_wc_tables.py
```

**Critères de succès :**
- ✅ Pas d'incohérences dans les données

---

## 🔧 PHASE 9 : GESTION DES STOCKS (Semaine 5)

### ✅ 9.1 Gestion des produits orphelins

**Actions :**
```bash
python set_out_of_stock_orphans.py
```

**Critères de succès :**
- ✅ Produits orphelins marqués "out of stock"

---

## 🚀 PHASE 10 : AUTOMATISATION (Semaine 6)

### ✅ 10.1 Utilisation du Workflow Master

**Actions :**
```bash
python workflow_master.py
```

**Ce que fait le script :**
- Lance automatiquement toutes les phases dans le bon ordre
- Parallélise Disty/Disway
- Parallélise les 7 sites concurrents
- Génère des logs détaillés
- Affiche des résumés par phase

**Critères de succès :**
- ✅ Workflow complet sans intervention manuelle

---

### ✅ 10.2 Automatisation quotidienne (Windows)

**Actions :**
1. Ouvrir le **Planificateur de tâches**
2. Créer une nouvelle tâche
3. **Déclencheur** : Tous les jours à 2h00
4. **Action** : `C:\Users\dell\Documents\GitHub\scrap_products_data\workflow_daily.bat`
5. **Conditions** : Réveiller l'ordinateur

**Critères de succès :**
- ✅ Scraping automatique quotidien

---

### ✅ 10.3 Monitoring et alertes

**Actions :**
- [ ] Consulter les logs quotidiens
- [ ] Mettre en place des alertes email (optionnel)
- [ ] Surveiller les métriques clés

**Critères de succès :**
- ✅ Logs automatiques
- ✅ Surveillance active

---

## 📊 WORKFLOW COMPLET RÉSUMÉ

```
1. Scraping Disty & Disway (PARALLÈLE)
   ↓
2. Comparaison.py (calcul prix DIX avec augmentation progressive)
   ↓
3. Scraping des 7 sites concurrents (PARALLÈLE)
   ↓
4. Merge (fusion DIX + 7 concurrents)
   ↓
5. Sync vers dix_temp
   ↓
6. Synchronisation WordPress (test.py)
   ↓
7. Populate & Sync attributs
   ↓
8. Mise à jour catégories et marques
   ↓
9. Interface web de comparaison
   ↓
10. Nettoyage et normalisation (À LA FIN)
    ↓
11. Automatisation quotidienne
```

---

## 🎯 INDICATEURS DE SUCCÈS

### Métriques clés :
- ✅ **Taux de scraping** : > 95% des produits scrapés
- ✅ **Taux de synchronisation** : > 95% des produits dans WordPress
- ✅ **Attributs complets** : > 90% des produits avec tous les attributs
- ✅ **Compétitivité** : % de produits où DIX est compétitif
- ✅ **Uptime** : > 99% de disponibilité

---

## 🚨 POINTS D'ATTENTION

### Problèmes connus :
1. **Doublons d'attributs** → `normalize_attributes.py` + `merge_i9_duplicates.py`
2. **Filtres invisibles** → `recalculate_term_counts()` + `fix_lookup_table()`
3. **Catégories manquantes** → `update_categories.py`
4. **Marques non assignées** → Vérifier `test.py`
5. **Timeout de scraping** → Augmenter `connection_timeout` dans `database.py`

---

## 📞 PROCHAINES ÉTAPES IMMÉDIATES

**À faire MAINTENANT :**

1. **Vérifier l'infrastructure**
   ```bash
   python database.py
   ```

2. **Lancer le workflow complet**
   ```bash
   python workflow_master.py
   ```

3. **Vérifier le site WordPress**
   - Filtres visibles ?
   - Attributs affichés ?
   - Prix corrects ?

4. **Tester l'interface web**
   ```bash
   cd web_interface
   python api.py
   # Ouvrir index.html
   ```

---

**Dernière mise à jour** : 29 décembre 2025  
**Version** : 1.0
