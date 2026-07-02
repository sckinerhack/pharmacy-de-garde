import { Routes } from '@angular/router';
import { HomeComponent } from './features/home/home.component';
import { PharmacieDetailComponent } from './features/pharmacie-detail/pharmacie-detail.component';
import { AdminComponent } from './features/admin/admin.component';
import { LoginComponent } from './features/auth/login/login.component';
import { adminGuard } from './core/guards/admin.guard';

export const routes: Routes = [
  // Pages publiques — accès libre sans login
  { path: '', component: HomeComponent },
  { path: 'login', component: LoginComponent },
  { path: 'pharmacie/:nom', component: PharmacieDetailComponent },

  // Admin protégé par guard — redirige vers /login si non connecté,
  // vers / si connecté mais pas admin
  { path: 'admin', component: AdminComponent, canActivate: [adminGuard] },

  { path: '**', redirectTo: '' }
];
