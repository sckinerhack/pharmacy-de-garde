export interface JourGarde {
  date: string;
  type: 'GARDE_24H' | 'WEEKEND' | 'JOUR_FERIE';
  pharmacies: string[];
}

export interface GardeResponse {
  date: string;
  gardes: JourGarde[];
  total_pharmacies: number;
  is_today: boolean;
}

export interface TrimestreInfo {
  debut: string;
  fin: string;
  jours_restants: number;
  alerte: boolean;
  alerte_message: string | null;
  donnees_disponibles: boolean;
  upload_date: string | null;
}

export interface PharmacieDetail {
  nom: string;
  adresse?: string;
  telephone?: string;
  lat?: number;
  lng?: number;
  has_detail: boolean;
}

export interface ImportResult {
  success: boolean;
  message: string;
  jours_importes: number;
  periode: { debut: string; fin: string };
  nouvelles_pharmacies: number;
}
