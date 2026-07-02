import { Component, OnInit, OnDestroy, signal, computed, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { PharmacieService } from '../../core/services/pharmacie.service';
import { JourGarde, TrimestreInfo, PharmacieDetail } from '../../shared/models/api.models';
import { ChatbotComponent } from '../chatbot/chatbot.component';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule, FormsModule, ChatbotComponent],
  templateUrl: './home.component.html',
  styleUrl: './home.component.scss'
})
export class HomeComponent implements OnInit, OnDestroy, AfterViewInit {
  selectedDate   = signal(new Date());
  recherche      = signal('');
  gardes         = signal<JourGarde[]>([]);
  showMap        = signal(false);
  darkMode       = signal(false);
  isLoading      = signal(false);
  apiError       = signal<string | null>(null);
  trimestreInfo  = signal<TrimestreInfo | null>(null);
  // ← Pharmacies chargées depuis l'API (pas le fichier statique)
  pharmaciesDetails = signal<PharmacieDetail[]>([]);

  private map: any = null;

  urgences = [
    { nom: 'SAMU',        numero: '15',            icon: '🚑', couleur: '#ef4444' },
    { nom: 'Police',      numero: '19',            icon: '🚔', couleur: '#3b82f6' },
    { nom: 'Pompiers',    numero: '15',            icon: '🚒', couleur: '#f97316' },
    { nom: 'Gendarmerie', numero: '177',           icon: '🛡️', couleur: '#8b5cf6' },
    { nom: 'CHU Tanger',  numero: '0539-31-21-32', icon: '🏥', couleur: '#06b6d4' },
    { nom: 'Anti-Poison', numero: '0801-000-180',  icon: '☠️', couleur: '#84cc16' },
  ];

  conseils = [
    { icon: '💊', titre: 'Ordonnance',       texte: 'Munissez-vous de votre ordonnance pour tout médicament prescrit.' },
    { icon: '🌡️', titre: 'Urgence médicale', texte: 'En cas d\'urgence, appelez le SAMU au 15 avant de vous déplacer.' },
    { icon: '🕐', titre: 'Garde 24h',         texte: 'Les pharmacies de garde sont ouvertes toute la nuit et les jours fériés.' },
    { icon: '📍', titre: 'Localisation',      texte: 'Utilisez la carte pour trouver la pharmacie la plus proche de chez vous.' },
  ];

  pharmaciesFiltrees = computed(() => {
    const q = this.recherche().toLowerCase();
    return this.gardes().map(g => ({
      ...g, pharmacies: q ? g.pharmacies.filter(p => p.toLowerCase().includes(q)) : g.pharmacies
    })).filter(g => g.pharmacies.length > 0);
  });

  constructor(private pharmService: PharmacieService, private router: Router) {}

  ngOnInit() {
    this.loadGardes();
    this.loadPharmaciesDetails();  // ← Charge depuis l'API maintenant
    const saved = localStorage.getItem('darkMode');
    if (saved === 'true') this.setDark(true);
  }

  ngAfterViewInit() {}

  /** Charge toutes les pharmacies depuis l'API backend */
  loadPharmaciesDetails() {
    this.pharmService.getAllPharmacies().subscribe({
      next: (details) => this.pharmaciesDetails.set(details),
      error: () => {}   // silencieux, la carte sera sans marqueurs
    });
  }

  loadGardes() {
    this.isLoading.set(true);
    this.apiError.set(null);
    this.pharmService.getGardesToday().subscribe({
      next: (data) => {
        this.gardes.set(data.gardes || []);
        if (data.trimestre) this.trimestreInfo.set(data.trimestre);
        this.isLoading.set(false);
        if (this.showMap()) setTimeout(() => this.initMap(), 300);
      },
      error: () => {
        this.isLoading.set(false);
        this.apiError.set('Impossible de joindre le serveur. Vérifiez que le backend est démarré.');
      }
    });
  }

  loadGardesForDate(date: Date) {
    this.isLoading.set(true);
    this.apiError.set(null);
    this.pharmService.getGardesForDate(date).subscribe({
      next: (data) => {
        this.gardes.set(data.gardes || []);
        this.isLoading.set(false);
        if (this.showMap()) setTimeout(() => this.initMap(), 300);
      },
      error: () => {
        this.isLoading.set(false);
        this.apiError.set('Erreur lors du chargement des gardes.');
      }
    });
  }

  changerDate(delta: number) {
    const d = new Date(this.selectedDate());
    d.setDate(d.getDate() + delta);
    this.selectedDate.set(d);
    if (this.isToday) this.loadGardes();
    else this.loadGardesForDate(d);
  }

  toggleDark() { this.setDark(!this.darkMode()); }

  setDark(val: boolean) {
    this.darkMode.set(val);
    localStorage.setItem('darkMode', String(val));
    if (val) document.documentElement.setAttribute('data-theme', 'dark');
    else     document.documentElement.removeAttribute('data-theme');
  }

  toggleMap() {
    this.showMap.set(!this.showMap());
    if (this.showMap()) setTimeout(() => this.initMap(), 300);
    else if (this.map) { this.map.remove(); this.map = null; }
  }

  /** Carte : utilise pharmaciesDetails chargées depuis l'API */
  initMap() {
    const L = (window as any).L;
    if (!L) return;
    if (this.map) { this.map.remove(); this.map = null; }
    const el = document.getElementById('home-map');
    if (!el) return;
    this.map = L.map('home-map').setView([35.7767, -5.8039], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
      { attribution: '© OpenStreetMap' }).addTo(this.map);

    const noms = this.pharmaciesFiltrees().flatMap(g => g.pharmacies);
    noms.forEach(nom => {
      const detail = this.pharmaciesDetails().find(d => d.nom === nom);
      if (detail?.lat && detail?.lng) {
        const icon = L.divIcon({
          html: `<div style="background:linear-gradient(135deg,#006233,#00843d);color:white;width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:16px;box-shadow:0 4px 12px rgba(0,98,51,0.4);border:2px solid white;">＋</div>`,
          className: '', iconSize: [32,32], iconAnchor: [16,16]
        });
        L.marker([detail.lat, detail.lng], { icon }).addTo(this.map)
          .bindPopup(`<div style="min-width:160px;font-family:Inter,sans-serif">
            <b style="color:#006233">＋ ${detail.nom}</b><br/>
            ${detail.adresse ? `<small>📍 ${detail.adresse}</small><br/>` : ''}
            ${detail.telephone ? `<small>📞 ${detail.telephone}</small>` : ''}
          </div>`);
      }
    });
  }

  hasDetail(nom: string): boolean {
    const d = this.pharmaciesDetails().find(p => p.nom === nom);
    return !!(d && d.has_detail);
  }

  goToDetail(nom: string) {
    if (this.hasDetail(nom)) this.router.navigate(['/pharmacie', encodeURIComponent(nom)]);
  }

  goToAdmin() { this.router.navigate(['/admin']); }

  ngOnDestroy() {
    if (this.map) { this.map.remove(); this.map = null; }
  }

  get dateLabel(): string {
    return this.selectedDate().toLocaleDateString('fr-MA',
      { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
  }
  get isToday(): boolean {
    return new Date().toDateString() === this.selectedDate().toDateString();
  }
  get totalPharmacies(): number {
    return this.pharmaciesFiltrees().reduce((acc, g) => acc + g.pharmacies.length, 0);
  }
  get salutation(): string {
    const h = new Date().getHours();
    if (h >= 5  && h < 12) return 'Bonjour';
    if (h >= 12 && h < 18) return 'Bon après-midi';
    return 'Bonsoir';
  }
  get donneesDispo(): boolean { return this.trimestreInfo()?.donnees_disponibles !== false; }
  get alerteTrimestre(): boolean { return this.trimestreInfo()?.alerte === true; }
  get alerteMessage(): string | null { return this.trimestreInfo()?.alerte_message ?? null; }
}
