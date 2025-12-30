# 🚀 LANCEMENT RAPIDE - DIX Platform

## ⚡ Démarrage en 3 étapes

### 1️⃣ Vérifier les connexions
```bash
python database.py
```
✅ Toutes les connexions doivent être vertes

---

### 2️⃣ Lancer le workflow complet
```bash
python workflow_master.py
```
✅ Confirmer avec 'o' quand demandé

---

### 3️⃣ Vérifier les résultats

**Sur WordPress :**
- Produits synchronisés ✅
- Prix corrects ✅
- Attributs visibles ✅
- Filtres fonctionnels ✅

**Interface web :**
```bash
cd web_interface
python api.py
# Ouvrir index.html dans le navigateur
```

---

## 📋 Ce que fait workflow_master.py

1. **Scrape Disty & Disway** (en parallèle) → 10-20 min
2. **Calcule les prix DIX** (augmentation progressive) → 2-5 min
3. **Scrape 7 sites concurrents** (en parallèle) → 15-30 min
4. **Fusionne toutes les données** → 2-5 min
5. **Synchronise vers WordPress** → 20-40 min
6. **Synchronise les attributs** → 10-15 min
7. **Met à jour les catégories** → 2-5 min

**Durée totale : 60-120 minutes**

---

## 🔄 Automatisation quotidienne

### Windows
Double-cliquer sur `workflow_daily.bat`

Ou configurer dans le Planificateur de tâches :
- Tous les jours à 2h00
- Action : `workflow_daily.bat`

### Linux/Mac
```bash
crontab -e
# Ajouter :
0 2 * * * cd /path/to/project && python3 workflow_master.py
```

---

## 📊 Ordre des opérations

```
Disty + Disway (parallèle)
    ↓
Comparaison (prix DIX)
    ↓
7 sites concurrents (parallèle)
    ↓
Fusion des données
    ↓
Synchronisation WordPress
    ↓
Attributs + Catégories
    ↓
✅ TERMINÉ
```

---

## 🧹 Nettoyage (À LA FIN, après plusieurs jours)

```bash
# 1. Analyser les doublons
python debug/check_i9_duplicates.py

# 2. Normaliser
python normalize_attributes.py

# 3. Fusionner les doublons
python cleanup_duplicate_terms.py

# 4. Recalculer
python sync_attributes.py
```

---

## 📚 Documentation complète

- **ROADMAP.md** : Roadmap détaillée phase par phase
- **WORKFLOW_GUIDE.md** : Guide complet du workflow master
- **web_interface/README.md** : Documentation de l'interface web

---

## 🆘 Problèmes courants

### Le workflow ne démarre pas
```bash
python database.py  # Vérifier les connexions
```

### Un scraper échoue
```bash
# Tester individuellement
python disty_script.py
```

### Les filtres ne s'affichent pas
```bash
# Recalculer les compteurs
python sync_attributes.py
```

---

## 📞 Support

Consulter les logs :
```
workflow_log_YYYYMMDD_HHMMSS.txt
```

---

**Prêt à lancer ? Exécutez :**
```bash
python workflow_master.py
```

🚀 **Bon lancement !**
