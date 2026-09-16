import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { environment } from '../../../environments/environment';
import { User } from '../models/user.model';

interface LoginResponse {
  mfa_pending_token: string;
}

interface TokenResponse {
  access_token: string;
  token_type: string;
}

const ACCESS_TOKEN_KEY = 'hris_access_token';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);

  private readonly accessTokenSignal = signal<string | null>(
    sessionStorage.getItem(ACCESS_TOKEN_KEY)
  );
  private readonly currentUserSignal = signal<User | null>(null);
  private mfaPendingToken: string | null = null;

  readonly isAuthenticated = computed(() => this.accessTokenSignal() !== null);
  readonly currentUser = this.currentUserSignal.asReadonly();

  get accessToken(): string | null {
    return this.accessTokenSignal();
  }

  async login(username: string, password: string): Promise<void> {
    const res = await firstValueFrom(
      this.http.post<LoginResponse>(`${environment.apiBaseUrl}/auth/login`, {
        username,
        password,
      })
    );
    this.mfaPendingToken = res.mfa_pending_token;
  }

  async verifyMfa(code: string): Promise<void> {
    if (!this.mfaPendingToken) {
      throw new Error('No pending MFA challenge — log in again.');
    }
    const res = await firstValueFrom(
      this.http.post<TokenResponse>(`${environment.apiBaseUrl}/auth/mfa/verify`, {
        mfa_pending_token: this.mfaPendingToken,
        code,
      })
    );
    this.mfaPendingToken = null;
    this.setAccessToken(res.access_token);
    await this.loadCurrentUser();
  }

  async loadCurrentUser(): Promise<void> {
    const user = await firstValueFrom(
      this.http.get<User>(`${environment.apiBaseUrl}/auth/me`)
    );
    this.currentUserSignal.set(user);
  }

  logout(): void {
    this.setAccessToken(null);
    this.currentUserSignal.set(null);
    this.router.navigateByUrl('/login');
  }

  private setAccessToken(token: string | null): void {
    this.accessTokenSignal.set(token);
    if (token) {
      sessionStorage.setItem(ACCESS_TOKEN_KEY, token);
    } else {
      sessionStorage.removeItem(ACCESS_TOKEN_KEY);
    }
  }
}
