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
  must_change_password: boolean;
}

interface SetupStatusResponse {
  setup_required: boolean;
}

interface SetupInitResponse {
  setup_token: string;
  mfa_secret: string;
  provisioning_uri: string;
}

interface MfaResetInitResponse {
  reset_token: string;
  mfa_secret: string;
  provisioning_uri: string;
}

const ACCESS_TOKEN_KEY = 'hris_access_token';
const MUST_CHANGE_PASSWORD_KEY = 'hris_must_change_password';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);

  private readonly accessTokenSignal = signal<string | null>(
    sessionStorage.getItem(ACCESS_TOKEN_KEY)
  );
  private readonly currentUserSignal = signal<User | null>(null);
  private readonly mustChangePasswordSignal = signal<boolean>(
    sessionStorage.getItem(MUST_CHANGE_PASSWORD_KEY) === 'true'
  );
  private mfaPendingToken: string | null = null;

  readonly isAuthenticated = computed(() => this.accessTokenSignal() !== null);
  readonly currentUser = this.currentUserSignal.asReadonly();
  readonly mustChangePassword = this.mustChangePasswordSignal.asReadonly();

  get accessToken(): string | null {
    return this.accessTokenSignal();
  }

  /** No auth required — used to decide whether to show the setup wizard or the login screen. */
  async checkSetupRequired(): Promise<boolean> {
    const res = await firstValueFrom(
      this.http.get<SetupStatusResponse>(`${environment.apiBaseUrl}/auth/setup-status`)
    );
    return res.setup_required;
  }

  async initSetup(username: string, email: string, password: string): Promise<SetupInitResponse> {
    return firstValueFrom(
      this.http.post<SetupInitResponse>(`${environment.apiBaseUrl}/auth/setup/init`, {
        username,
        email,
        password,
      })
    );
  }

  async confirmSetup(setupToken: string, code: string): Promise<void> {
    await firstValueFrom(
      this.http.post(`${environment.apiBaseUrl}/auth/setup/confirm`, {
        setup_token: setupToken,
        code,
      })
    );
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
    this.setMustChangePassword(res.must_change_password);
    if (!res.must_change_password) {
      await this.loadCurrentUser();
    }
  }

  /** For an account whose enrolled authenticator stopped working — requires
   * the same pending MFA challenge the normal verify step uses, nothing weaker. */
  async initMfaReset(): Promise<MfaResetInitResponse> {
    if (!this.mfaPendingToken) {
      throw new Error('No pending MFA challenge — log in again.');
    }
    return firstValueFrom(
      this.http.post<MfaResetInitResponse>(`${environment.apiBaseUrl}/auth/mfa/reset/init`, {
        mfa_pending_token: this.mfaPendingToken,
      })
    );
  }

  async confirmMfaReset(resetToken: string, code: string): Promise<void> {
    const res = await firstValueFrom(
      this.http.post<TokenResponse>(`${environment.apiBaseUrl}/auth/mfa/reset/confirm`, {
        reset_token: resetToken,
        code,
      })
    );
    this.mfaPendingToken = null;
    this.setAccessToken(res.access_token);
    this.setMustChangePassword(res.must_change_password);
    if (!res.must_change_password) {
      await this.loadCurrentUser();
    }
  }

  async loadCurrentUser(): Promise<void> {
    const user = await firstValueFrom(
      this.http.get<User>(`${environment.apiBaseUrl}/auth/me`)
    );
    this.currentUserSignal.set(user);
  }

  /** Server-side enforcement is the real boundary (backend app/auth/deps.py) —
   * this only clears the client-side flag once the backend confirms success. */
  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    await firstValueFrom(
      this.http.post(`${environment.apiBaseUrl}/auth/change-password`, {
        current_password: currentPassword,
        new_password: newPassword,
      })
    );
    this.setMustChangePassword(false);
    await this.loadCurrentUser();
  }

  logout(): void {
    this.setAccessToken(null);
    this.setMustChangePassword(false);
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

  private setMustChangePassword(required: boolean): void {
    this.mustChangePasswordSignal.set(required);
    if (required) {
      sessionStorage.setItem(MUST_CHANGE_PASSWORD_KEY, 'true');
    } else {
      sessionStorage.removeItem(MUST_CHANGE_PASSWORD_KEY);
    }
  }
}
