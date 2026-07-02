# Modifications Angular — Frontend v2

## Fichiers à modifier / créer

### 1. Supprimer l'ancienne API Node.js
```
SUPPRIMER le dossier :
pharmacie-garde-tanger/pharmacie-garde-tanger-api/
(server.js + package.json)
```

### 2. Nouveaux fichiers à créer

```
src/app/shared/models/api.models.ts          ← Interfaces TypeScript des réponses API
src/app/features/admin/admin.component.ts    ← Page admin : import PDF, alertes
src/app/features/admin/admin.component.html  ← Template admin
src/app/features/admin/admin.component.scss  ← Styles admin
```

### 3. Fichiers à remplacer entièrement

| Fichier | Changement principal |
|---------|---------------------|
| `src/app/app.config.ts` | Ajoute `provideHttpClient(withFetch())` |
| `src/app/app.routes.ts` | Ajoute la route `/admin` |
| `src/app/core/services/pharmacie.service.ts` | Remplace données hardcodées → appels HTTP vers `localhost:3000/api` |
| `src/app/features/home/home.component.ts` | Utilise le service HTTP, gère loading/erreur/alerte |
| `src/app/features/home/home.component.html` | Ajoute bannières alerte, spinner, état "données indisponibles" |

### 4. `home.component.scss`
Ajouter le contenu de `home.component.additions.scss` **à la fin** du fichier existant.

---

## Ce que font les nouveaux composants

### `pharmacie.service.ts`
- Tous les appels HTTP pointent vers `http://localhost:3000/api`
- Méthode `getGardesToday()` — inclut le statut trimestre dans la réponse
- Méthode `getTrimestreInfo()` — infos + alertes du trimestre
- Méthode `importPdfTrimestre(file)` — upload PDF admin

### `home.component`
- Charge les gardes via l'API au démarrage
- Affiche un **spinner** pendant le chargement
- Affiche une **bannière orange** si le trimestre se termine bientôt
- Affiche une **bannière rouge** si les données sont expirées ou indisponibles
- La stat "Planning" affiche maintenant les **jours restants** du trimestre
- Bouton ⚙️ Admin dans le footer → navigue vers `/admin`

### `admin.component`
- Affiche le statut du trimestre (✅ actif / ⚠️ fin proche / 🚫 expiré)
- Zone de dépôt pour uploader le PDF du prochain trimestre
- Confirmation visuelle après import réussi
- Guide en 3 étapes pour expliquer le processus

---

## Démarrage

```bash
# Backend
cd pharmacie-garde-tanger-api
docker-compose up --build

# Frontend
cd pharmacie-garde-tanger
npm install
ng serve
```

L'app sera sur `http://localhost:4200`, elle appelle `http://localhost:3000/api`.
