# Interface de Comparaison de Prix

Interface web pour comparer les prix de DIX avec 7 sites concurrents.

## 📁 Structure

```
web_interface/
├── index.html          # Interface principale
├── api.py              # API Flask
├── static/
│   ├── css/           # Fichiers CSS (si séparés)
│   └── js/            # Fichiers JavaScript (si séparés)
└── README.md          # Ce fichier
```

## 🚀 Installation

1. **Installer les dépendances Python** :
   ```bash
   pip install Flask Flask-CORS mysql-connector-python
   ```

2. **Vérifier la configuration de la base de données** :
   - L'API utilise le module `database.py` du projet
   - Base de données : `dix_scraper`
   - Table : `ps_products_comparison_v2`

## 📊 Lancement

### 1. Démarrer l'API

```bash
cd web_interface
python api.py
```

L'API sera accessible sur : `http://localhost:5000`

### 2. Ouvrir l'interface

Ouvrir le fichier `index.html` dans un navigateur web.

## 🎯 Fonctionnalités

### Statistiques
- **Total de produits** avec prix DIX
- **Nombre de produits** où DIX est moins cher
- **Taux de compétitivité** de DIX

### Filtres
1. **Tous** - Affiche tous les produits
2. **DIX Moins Cher** - Produits où DIX a le meilleur prix
3. **DIX Plus Cher** - Produits où DIX est plus cher que la concurrence

### Recherche
- Recherche en temps réel par **référence** ou **titre**
- Résultats instantanés

### Tableau de Comparaison
Affiche pour chaque produit :
- **Référence** et **Titre**
- **Prix DIX** (mis en évidence)
- **Prix des 7 concurrents** :
  - Crenova
  - Duga
  - LinkSolutions
  - Tabtel
  - Mies
  - Rightech
  - Joutech
- **Écart de prix** avec le moins cher (%)
- **Badge de statut** :
  - 🟢 **Meilleur Prix** - DIX a le prix le plus bas
  - 🟡 **Compétitif** - DIX à ±5% du prix minimum
  - 🔴 **Cher** - DIX >10% plus cher

## 🔌 Endpoints API

### `GET /api/products`
Récupère tous les produits avec leurs prix

### `GET /api/products/search?q={query}`
Recherche produits par référence ou titre

### `GET /api/products/cheaper`
Produits où DIX est moins cher que tous les concurrents

### `GET /api/products/expensive`
Produits où DIX est plus cher que le minimum concurrent

### `GET /api/stats`
Statistiques globales de comparaison

## 🎨 Design

- **Design moderne** avec gradients
- **Codes couleur** pour identification rapide
- **Responsive** - fonctionne sur mobile et desktop
- **Animations fluides**

## 🔧 Personnalisation

### Modifier les couleurs
Éditer les variables CSS dans `index.html` :
- `#667eea` - Couleur primaire (violet)
- `#764ba2` - Couleur secondaire
- `#10b981` - Vert (succès)
- `#ef4444` - Rouge (alerte)

### Ajouter un site concurrent
1. Ajouter la colonne dans `api.py` (requêtes SQL)
2. Ajouter la colonne dans `index.html` (tableau)
3. Mettre à jour la logique de comparaison

## ⚠️ Prérequis

- Python 3.7+
- MySQL/MariaDB
- Navigateur moderne (Chrome, Firefox, Edge)
- Données de prix dans la base `ps_products_comparison_v2`

## 📝 Notes

- L'API doit être lancée avant d'ouvrir l'interface
- Les prix NULL sont affichés comme "N/A"
- Le calcul du statut se base sur le prix minimum concurrent
- Les statistiques se mettent à jour automatiquement
