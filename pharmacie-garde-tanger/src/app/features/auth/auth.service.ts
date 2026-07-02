import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, BehaviorSubject, tap } from 'rxjs';
import { Router } from '@angular/router';

export interface User {
  id: number;
  email: string;
  nom: string;
  role: 'admin' | 'user';
}

export interface AuthResponse {
  token: string;
  user: User;
}

const API = 'http://localhost:3000/api/auth';
const ADMIN_API = 'http://localhost:3000/api/admin';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private userSubject = new BehaviorSubject<User | null>(this.getUserFromStorage());
  currentUser$ = this.userSubject.asObservable();

  constructor(private http: HttpClient, private router: Router) {}

  private getUserFromStorage(): User | null {
    try {
      const u = localStorage.getItem('pharma_user');
      return u ? JSON.parse(u) : null;
    } catch { return null; }
  }

  private getAuthHeaders(): HttpHeaders {
    const token = localStorage.getItem('pharma_token');
    return new HttpHeaders(token ? { Authorization: `Bearer ${token}` } : {});
  }

  get currentUser(): User | null { return this.userSubject.value; }
  get isLoggedIn(): boolean { return !!this.currentUser && !!localStorage.getItem('pharma_token'); }
  get isAdmin(): boolean { return this.currentUser?.role === 'admin'; }
  get token(): string | null { return localStorage.getItem('pharma_token'); }

  private saveSession(res: AuthResponse) {
    localStorage.setItem('pharma_token', res.token);
    localStorage.setItem('pharma_user', JSON.stringify(res.user));
    this.userSubject.next(res.user);
  }

  login(email: string, password: string): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${API}/login`, { email, password })
      .pipe(tap(res => this.saveSession(res)));
  }

  logout() {
    localStorage.removeItem('pharma_token');
    localStorage.removeItem('pharma_user');
    this.userSubject.next(null);
    this.router.navigate(['/login']);
  }

  /** Modifier email / nom / mot de passe */
  updateProfile(data: {
    nom?: string;
    email?: string;
    current_password: string;
    new_password?: string;
  }): Observable<{ message: string; token: string; user: User }> {
    return this.http.put<{ message: string; token: string; user: User }>(
      `${ADMIN_API}/profile`, data, { headers: this.getAuthHeaders() }
    ).pipe(tap(res => {
      // Mettre à jour le token et les infos utilisateur
      localStorage.setItem('pharma_token', res.token);
      localStorage.setItem('pharma_user', JSON.stringify(res.user));
      this.userSubject.next(res.user);
    }));
  }

  /** Demander un token de réinitialisation */
  forgotPassword(email: string): Observable<{ message: string; reset_token?: string }> {
    return this.http.post<{ message: string; reset_token?: string }>(
      `${API}/forgot-password`, { email, password: '' }
    );
  }

  /** Utiliser un token pour réinitialiser le mot de passe */
  resetPassword(token: string, newPassword: string): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(
      `${API}/reset-password`, { reset_token: token, new_password: newPassword }
    );
  }
}
