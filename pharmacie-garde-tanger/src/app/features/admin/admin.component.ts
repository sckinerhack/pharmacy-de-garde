import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { PharmacieService } from '../../core/services/pharmacie.service';
import { AuthService } from '../auth/auth.service';
import { TrimestreInfo, ImportResult } from '../../shared/models/api.models';

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './admin.component.html',
  styleUrl: './admin.component.scss'
})
export class AdminComponent implements OnInit {

  // ── Trimestre ──────────────────────────────────────────────────────────────
  trimestreInfo  = signal<TrimestreInfo | null>(null);
  isLoadingInfo  = signal(true);
  selectedFile   = signal<File | null>(null);
  isImporting    = signal(false);
  importResult   = signal<ImportResult | null>(null);
  importError    = signal<string | null>(null);

  // ── Profil Admin ───────────────────────────────────────────────────────────
  showProfile    = signal(false);
  profNom        = '';
  profEmail      = '';
  profCurrentPw  = '';
  profNewPw      = '';
  profNewPwConf  = '';
  profLoading    = signal(false);
  profSuccess    = signal('');
  profError      = signal('');

  // ── Reset mot de passe ─────────────────────────────────────────────────────
  showReset      = signal(false);
  resetEmail     = '';
  resetToken     = '';
  resetNewPw     = '';
  resetStep      = signal<1 | 2>(1);   // 1 = demande token, 2 = nouveau mdp
  resetLoading   = signal(false);
  resetSuccess   = signal('');
  resetError     = signal('');

  constructor(
    private pharmService: PharmacieService,
    public auth: AuthService,
    private router: Router
  ) {}

  ngOnInit() {
    this.loadTrimestreInfo();
    // Pré-remplir le profil avec les données actuelles
    const u = this.auth.currentUser;
    if (u) { this.profNom = u.nom; this.profEmail = u.email; }
  }

  // ── Trimestre ──────────────────────────────────────────────────────────────
  loadTrimestreInfo() {
    this.isLoadingInfo.set(true);
    this.pharmService.getTrimestreInfo().subscribe({
      next: (info) => { this.trimestreInfo.set(info); this.isLoadingInfo.set(false); },
      error: ()    => { this.isLoadingInfo.set(false); }
    });
  }

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (!input.files?.length) return;
    const file = input.files[0];
    if (!file.name.endsWith('.pdf')) {
      this.importError.set('Seuls les fichiers PDF sont acceptés.');
      this.selectedFile.set(null);
      return;
    }
    this.selectedFile.set(file);
    this.importError.set(null);
    this.importResult.set(null);
  }

  importerPdf() {
    const file = this.selectedFile();
    if (!file) return;
    this.isImporting.set(true);
    this.importError.set(null);
    this.importResult.set(null);

    this.pharmService.importPdfTrimestre(file).subscribe({
      next: (result) => {
        this.importResult.set(result);
        this.isImporting.set(false);
        this.selectedFile.set(null);
        this.loadTrimestreInfo();
      },
      error: (err) => {
        const msg = err.error?.detail || err.message || 'Erreur lors de l\'import.';
        this.importError.set(msg);
        this.isImporting.set(false);
      }
    });
  }

  // ── Profil ─────────────────────────────────────────────────────────────────
  toggleProfile() {
    this.showProfile.set(!this.showProfile());
    this.profSuccess.set('');
    this.profError.set('');
    this.profCurrentPw = '';
    this.profNewPw = '';
    this.profNewPwConf = '';
  }

  saveProfile() {
    if (!this.profCurrentPw) {
      this.profError.set('Mot de passe actuel requis pour confirmer les modifications.');
      return;
    }
    if (this.profNewPw && this.profNewPw !== this.profNewPwConf) {
      this.profError.set('Les nouveaux mots de passe ne correspondent pas.');
      return;
    }
    if (this.profNewPw && this.profNewPw.length < 6) {
      this.profError.set('Le nouveau mot de passe doit contenir au moins 6 caractères.');
      return;
    }
    this.profLoading.set(true);
    this.profError.set('');
    this.profSuccess.set('');

    this.auth.updateProfile({
      nom: this.profNom,
      email: this.profEmail,
      current_password: this.profCurrentPw,
      new_password: this.profNewPw || undefined
    }).subscribe({
      next: (res) => {
        this.profLoading.set(false);
        this.profSuccess.set('✅ Profil mis à jour avec succès !');
        this.profCurrentPw = '';
        this.profNewPw = '';
        this.profNewPwConf = '';
      },
      error: (err) => {
        this.profLoading.set(false);
        this.profError.set(err.error?.detail || 'Erreur lors de la mise à jour.');
      }
    });
  }

  // ── Reset mot de passe ─────────────────────────────────────────────────────
  toggleReset() {
    this.showReset.set(!this.showReset());
    this.resetStep.set(1);
    this.resetEmail = '';
    this.resetToken = '';
    this.resetNewPw = '';
    this.resetSuccess.set('');
    this.resetError.set('');
  }

  requestReset() {
    if (!this.resetEmail) { this.resetError.set('Email requis.'); return; }
    this.resetLoading.set(true);
    this.resetError.set('');

    this.auth.forgotPassword(this.resetEmail).subscribe({
      next: (res) => {
        this.resetLoading.set(false);
        if (res.reset_token) {
          this.resetToken = res.reset_token;
          this.resetStep.set(2);
          this.resetSuccess.set(`Token généré (dev): ${res.reset_token}`);
        } else {
          this.resetSuccess.set(res.message);
        }
      },
      error: (err) => {
        this.resetLoading.set(false);
        this.resetError.set(err.error?.detail || 'Erreur lors de la demande.');
      }
    });
  }

  confirmReset() {
    if (!this.resetToken || !this.resetNewPw) {
      this.resetError.set('Token et nouveau mot de passe requis.'); return;
    }
    if (this.resetNewPw.length < 6) {
      this.resetError.set('Mot de passe trop court (min 6 caractères).'); return;
    }
    this.resetLoading.set(true);
    this.resetError.set('');

    this.auth.resetPassword(this.resetToken, this.resetNewPw).subscribe({
      next: (res) => {
        this.resetLoading.set(false);
        this.resetSuccess.set(res.message);
        setTimeout(() => { this.showReset.set(false); this.auth.logout(); }, 2000);
      },
      error: (err) => {
        this.resetLoading.set(false);
        this.resetError.set(err.error?.detail || 'Erreur lors de la réinitialisation.');
      }
    });
  }

  // ── Helpers ────────────────────────────────────────────────────────────────
  retourAccueil() { this.router.navigate(['/']); }
  logout() { this.auth.logout(); }

  get statutClass(): string {
    const i = this.trimestreInfo();
    if (!i || !i.donnees_disponibles) return 'statut-danger';
    if (i.alerte) return 'statut-warning';
    return 'statut-ok';
  }
  get statutLabel(): string {
    const i = this.trimestreInfo();
    if (!i || !i.donnees_disponibles) return 'Données non disponibles';
    if (i.alerte) return `Fin proche — ${i.jours_restants} jours restants`;
    return `Planning actif — ${i.jours_restants} jours restants`;
  }
  get statutIcon(): string {
    const i = this.trimestreInfo();
    if (!i || !i.donnees_disponibles) return '🚫';
    if (i.alerte) return '⚠️';
    return '✅';
  }
}
