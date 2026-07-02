import { Component, OnInit, signal } from '@angular/core';
import { CommonModule, DecimalPipe } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { PharmacieService } from '../../core/services/pharmacie.service';
import { PharmacieDetail } from '../../shared/models/api.models';

@Component({
  selector: 'app-pharmacie-detail',
  standalone: true,
  imports: [CommonModule, DecimalPipe],
  templateUrl: './pharmacie-detail.component.html',
  styleUrl: './pharmacie-detail.component.scss'
})
export class PharmacieDetailComponent implements OnInit {
  pharmacie  = signal<PharmacieDetail | null>(null);
  notFound   = signal(false);
  isLoading  = signal(true);

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private pharmService: PharmacieService
  ) {}

  ngOnInit() {
    const nom = decodeURIComponent(this.route.snapshot.paramMap.get('nom') || '');
    this.pharmService.getPharmacieDetail(nom).subscribe({
      next: (detail) => {
        this.isLoading.set(false);
        if (detail && (detail.adresse || detail.telephone || detail.lat)) {
          this.pharmacie.set(detail);
          if (detail.lat && detail.lng) {
            setTimeout(() => this.initMap(detail.lat!, detail.lng!, detail.nom), 400);
          }
        } else {
          this.notFound.set(true);
        }
      },
      error: () => {
        this.isLoading.set(false);
        this.notFound.set(true);
      }
    });
  }

  initMap(lat: number, lng: number, nom: string) {
    const L = (window as any).L;
    if (!L) return;
    const map = L.map('detail-map').setView([lat, lng], 16);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
      { attribution: '© OpenStreetMap' }).addTo(map);

    const icon = L.divIcon({
      html: `<div style="
        background: linear-gradient(135deg,#006233,#00843d);
        color:white; width:36px;height:36px; border-radius:50%;
        display:flex;align-items:center;justify-content:center;
        font-size:18px; box-shadow:0 4px 12px rgba(0,98,51,0.4);
        border:2px solid white;">＋</div>`,
      className: '', iconSize: [36, 36], iconAnchor: [18, 18]
    });

    L.marker([lat, lng], { icon }).addTo(map)
      .bindPopup(`<b style="color:#006233">Pharmacie ${nom}</b>`)
      .openPopup();
  }

  appeler() {
    const p = this.pharmacie();
    if (p?.telephone) window.location.href = 'tel:' + p.telephone;
  }

  ouvrirMaps() {
    const p = this.pharmacie();
    if (p?.lat && p?.lng) {
      window.open(`https://www.google.com/maps?q=${p.lat},${p.lng}`, '_blank');
    }
  }

  goBack() { this.router.navigate(['/']); }
}
