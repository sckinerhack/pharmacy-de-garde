import { Injectable, PLATFORM_ID, Inject } from '@angular/core';
import { HttpClient, HttpParams, HttpHeaders } from '@angular/common/http';
import { isPlatformBrowser } from '@angular/common';
import { Observable } from 'rxjs';
import { GardeResponse, TrimestreInfo, PharmacieDetail, ImportResult } from '../../shared/models/api.models';

const API_URL = 'http://localhost:3000/api';

@Injectable({ providedIn: 'root' })
export class PharmacieService {
  private isBrowser: boolean;

  constructor(
    private http: HttpClient,
    @Inject(PLATFORM_ID) platformId: Object
  ) {
    this.isBrowser = isPlatformBrowser(platformId);
  }

  private getAuthHeaders(): HttpHeaders {
    const token = localStorage.getItem('pharma_token');
    return new HttpHeaders(token ? { Authorization: `Bearer ${token}` } : {});
  }

  private formatDate(date: Date): string {
    const d = String(date.getDate()).padStart(2, '0');
    const m = String(date.getMonth() + 1).padStart(2, '0');
    return `${d}/${m}/${date.getFullYear()}`;
  }

  getGardesForDate(date: Date, recherche?: string): Observable<GardeResponse> {
    let params = new HttpParams().set('date', this.formatDate(date));
    if (recherche) params = params.set('recherche', recherche);
    return this.http.get<GardeResponse>(`${API_URL}/gardes`, { params });
  }

  getGardesToday(): Observable<any> {
    return this.http.get<any>(`${API_URL}/gardes/today`);
  }

  getAllDates(): Observable<{ dates: string[]; total: number }> {
    return this.http.get<{ dates: string[]; total: number }>(`${API_URL}/gardes/dates`);
  }

  getTrimestreInfo(): Observable<TrimestreInfo> {
    return this.http.get<TrimestreInfo>(`${API_URL}/trimestre`);
  }

  /** Charge les détails d'une pharmacie depuis l'API (pas le fichier statique) */
  getPharmacieDetail(nom: string): Observable<PharmacieDetail> {
    return this.http.get<PharmacieDetail>(`${API_URL}/pharmacies/${encodeURIComponent(nom)}`);
  }

  /** Toutes les pharmacies depuis l'API (inclut les nouvelles du PDF) */
  getAllPharmacies(recherche?: string): Observable<PharmacieDetail[]> {
    let params = new HttpParams();
    if (recherche) params = params.set('recherche', recherche);
    return this.http.get<PharmacieDetail[]>(`${API_URL}/pharmacies`, { params });
  }

  getStats(): Observable<any> {
    return this.http.get<any>(`${API_URL}/stats`);
  }

  importPdfTrimestre(file: File): Observable<ImportResult> {
    const formData = new FormData();
    formData.append('file', file, file.name);
    return this.http.post<ImportResult>(
      `${API_URL}/admin/trimestre/import`,
      formData,
      { headers: this.getAuthHeaders() }
    );
  }
}
