# 📸 IA Vente Facile

> **Générez automatiquement des descriptions de vente optimisées avec l'intelligence artificielle GPT-4 Vision**

Une application web moderne qui analyse vos photos d'objets et génère des descriptions de vente professionnelles optimisées pour Vinted, eBay, Etsy et autres plateformes de vente en ligne.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4-orange.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ Fonctionnalités

- 🤖 **IA GPT-4 Vision** : Analyse intelligente des images
- 📱 **Interface responsive** : Optimisée desktop et mobile
- 🎯 **Multi-plateformes** : Descriptions adaptées pour Vinted, eBay, Etsy
- 📋 **6 variantes** : Plusieurs styles de descriptions par objet
- 🏷️ **Tags SEO** : Mots-clés optimisés pour la recherche
- 💰 **Estimation de prix** : Suggestions de prix automatiques
- 📊 **Historique** : Sauvegarde et suivi des générations
- 📤 **Export** : CSV et JSON pour vos données
- 🎨 **Interface moderne** : Design professionnel avec animations

## 🚀 Installation rapide

### Prérequis

- Python 3.8 ou supérieur
- Clé API OpenAI ([Obtenez la vôtre ici](https://platform.openai.com/api-keys))
- Git (optionnel)

### 1. Cloner le projet

```bash
git clone https://github.com/votre-username/ia-vente-facile.git
cd ia-vente-facile
```

Ou téléchargez et extrayez l'archive ZIP.

### 2. Créer un environnement virtuel

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configuration

1. Copiez le fichier de configuration :
   ```bash
   cp .env.example .env
   ```

2. Éditez le fichier `.env` avec votre éditeur préféré :
   ```bash
   nano .env
   ```

3. **OBLIGATOIRE** : Ajoutez votre clé API OpenAI :
   ```
   OPENAI_API_KEY=sk-votre-clé-api-ici
   ```

### 5. Lancer l'application

```bash
python main.py
```

🎉 **C'est tout !** Ouvrez votre navigateur sur `http://localhost:5000`

## 📖 Guide d'utilisation

### 1. Prendre des photos

- Prenez 2-4 photos de votre objet sous différents angles
- Formats supportés : JPG, PNG, GIF, WebP
- Taille maximum : 16MB par image

### 2. Choisir la plateforme

- **Vinted** : Style décontracté pour la mode
- **eBay** : Professionnel et détaillé
- **Etsy** : Créatif et artisanal
- **Général** : Polyvalent pour tous sites

### 3. Analyser et générer

- Glissez-déposez vos images ou cliquez pour sélectionner
- L'IA analyse automatiquement vos photos
- 6 descriptions différentes sont générées

### 4. Copier et utiliser

- Copiez les titres et descriptions qui vous plaisent
- Utilisez les tags suggérés pour optimiser votre référencement
- Adaptez les prix suggérés selon votre marché

## 🔧 Configuration avancée

### Variables d'environnement

Le fichier `.env` permet de configurer de nombreux aspects :

```bash
# Obligatoire
OPENAI_API_KEY=sk-your-key-here

# Base de données (optionnel)
DATABASE_URL=sqlite:///app.db

# Sécurité
SESSION_SECRET=your-secret-key

# Performance
MAX_CONTENT_LENGTH=16777216
OPENAI_TIMEOUT=60
```

### Base de données

Par défaut, l'application utilise SQLite (aucune configuration requise).

Pour PostgreSQL en production :
```bash
pip install psycopg2-binary
```
```
DATABASE_URL=postgresql://user:password@localhost:5432/database
```

### Déploiement en production

1. **Avec Gunicorn** :
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:8000 main:app
   ```

2. **Variables d'environnement production** :
   ```
   FLASK_ENV=production
   FLASK_DEBUG=False
   LOG_LEVEL=WARNING
   ```

3. **Proxy inverse** (recommandé avec Nginx) :
   ```nginx
   location / {
       proxy_pass http://localhost:8000;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
   }
   ```

## 📁 Structure du projet

```
ia-vente-facile/
├── main.py              # Application principale
├── requirements.txt     # Dépendances Python
├── .env.example        # Configuration exemple
├── README.md           # Ce fichier
├── templates/          # Templates HTML
│   ├── base.html
│   ├── index.html
│   ├── results.html
│   ├── history.html
│   ├── mobile_home.html
│   └── mobile_results.html
├── static/             # Fichiers statiques
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
└── uploads/            # Dossier des images (créé automatiquement)
```

## 💡 Conseils d'utilisation

### Pour de meilleures descriptions

- ✅ Prenez des photos nettes et bien éclairées
- ✅ Montrez l'objet sous plusieurs angles
- ✅ Incluez les détails importants (étiquettes, défauts, etc.)
- ✅ Évitez les arrière-plans encombrés

### Optimisation SEO

- 🏷️ Utilisez tous les tags suggérés pertinents
- 📝 Adaptez les descriptions selon votre audience
- 💰 Vérifiez les prix sur les plateformes avant de publier
- 📊 Consultez l'historique pour réutiliser les meilleures descriptions

## 🛠️ Développement

### Installation développement

```bash
# Cloner le repo
git clone https://github.com/votre-username/ia-vente-facile.git
cd ia-vente-facile

# Installer avec les dépendances de dev
pip install -r requirements.txt

# Activer le mode debug
export FLASK_DEBUG=True
python main.py
```

### Tests

```bash
# Installer pytest
pip install pytest pytest-flask

# Lancer les tests
pytest
```

### Contribution

1. Fork le projet
2. Créez votre branche (`git checkout -b feature/AmazingFeature`)
3. Commitez vos changements (`git commit -m 'Add some AmazingFeature'`)
4. Push sur la branche (`git push origin feature/AmazingFeature`)
5. Ouvrez une Pull Request

## ❓ FAQ

### Q: L'application ne démarre pas
**R:** Vérifiez que :
- Python 3.8+ est installé
- Toutes les dépendances sont installées (`pip install -r requirements.txt`)
- Votre clé API OpenAI est valide dans le fichier `.env`

### Q: Erreur "OPENAI_API_KEY non configurée"
**R:** Ajoutez votre clé API dans le fichier `.env` :
```
OPENAI_API_KEY=sk-votre-clé-ici
```

### Q: Les images ne s'uploadent pas
**R:** Vérifiez que :
- Les images font moins de 16MB chacune
- Le format est supporté (JPG, PNG, GIF, WebP)
- Vous avez sélectionné entre 2 et 4 images

### Q: Comment obtenir une clé API OpenAI ?
**R:** 
1. Créez un compte sur [OpenAI](https://platform.openai.com/)
2. Allez dans [API Keys](https://platform.openai.com/api-keys)
3. Cliquez sur "Create new secret key"
4. Copiez la clé dans votre fichier `.env`

### Q: Puis-je utiliser cette app commercialement ?
**R:** Oui, le code est sous licence MIT. Attention aux [conditions d'utilisation OpenAI](https://openai.com/policies/terms-of-use) pour l'API.

## 🔒 Sécurité

- 🔐 Toutes les clés API sont stockées localement
- 🗂️ Les images sont automatiquement supprimées après 24h
- 📊 Aucune donnée n'est partagée avec des tiers
- 🔒 Les communications avec OpenAI sont chiffrées (HTTPS)

## 📈 Roadmap

- [ ] Support de plus de langues
- [ ] Intégration directe avec les APIs de vente
- [ ] Mode hors-ligne avec IA locale
- [ ] Application mobile native
- [ ] Système de templates personnalisés
- [ ] Analytics avancés

## 🤝 Support

- 📧 **Email** : support@example.com
- 🐛 **Bugs** : [Issues GitHub](https://github.com/votre-username/ia-vente-facile/issues)
- 💬 **Discussions** : [GitHub Discussions](https://github.com/votre-username/ia-vente-facile/discussions)

## 📜 Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

## 🙏 Remerciements

- [OpenAI](https://openai.com) pour l'API GPT-4 Vision
- [Flask](https://flask.palletsprojects.com/) pour le framework web
- [Bootstrap](https://getbootstrap.com/) pour l'interface utilisateur
- [Font Awesome](https://fontawesome.com/) pour les icônes

---

**Fait avec ❤️ pour simplifier la vente en ligne**

*Si cette application vous a aidé, n'hésitez pas à ⭐ le projet !*