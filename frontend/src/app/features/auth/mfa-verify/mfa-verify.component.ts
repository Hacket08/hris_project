import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import * as QRCode from 'qrcode';
import {
  ButtonDirective,
  CardBodyComponent,
  CardComponent,
  ColComponent,
  ContainerComponent,
  FormControlDirective,
  FormDirective,
  FormLabelDirective,
  RowComponent,
} from '@coreui/angular';

import { AuthService } from '../../../core/auth/auth.service';

type ScreenMode = 'verify' | 'reset-qr';

@Component({
  selector: 'app-mfa-verify',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ButtonDirective,
    CardBodyComponent,
    CardComponent,
    ColComponent,
    ContainerComponent,
    FormControlDirective,
    FormDirective,
    FormLabelDirective,
    RowComponent,
  ],
  host: { class: 'bg-body-tertiary min-vh-100 d-flex flex-row align-items-center' },
  templateUrl: './mfa-verify.component.html',
})
export class MfaVerifyComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  readonly mode = signal<ScreenMode>('verify');
  code = '';
  readonly submitting = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly qrDataUrl = signal<string | null>(null);
  readonly provisioningUri = signal<string | null>(null);

  private resetToken: string | null = null;

  async onSubmit(): Promise<void> {
    this.errorMessage.set(null);
    this.submitting.set(true);
    try {
      if (this.mode() === 'verify') {
        await this.auth.verifyMfa(this.code);
      } else {
        if (!this.resetToken) {
          this.errorMessage.set('Reset session lost — start again.');
          this.mode.set('verify');
          return;
        }
        await this.auth.confirmMfaReset(this.resetToken, this.code);
      }
      await this.router.navigateByUrl(this.auth.mustChangePassword() ? '/change-password' : '/');
    } catch (err: unknown) {
      this.errorMessage.set(this.extractErrorDetail(err, 'Invalid or expired code.'));
    } finally {
      this.submitting.set(false);
    }
  }

  async startMfaReset(): Promise<void> {
    this.errorMessage.set(null);
    this.submitting.set(true);
    try {
      const res = await this.auth.initMfaReset();
      this.resetToken = res.reset_token;
      this.provisioningUri.set(res.provisioning_uri);
      this.qrDataUrl.set(await QRCode.toDataURL(res.provisioning_uri));
      this.code = '';
      this.mode.set('reset-qr');
    } catch (err: unknown) {
      this.errorMessage.set(this.extractErrorDetail(err, 'Could not start MFA reset.'));
    } finally {
      this.submitting.set(false);
    }
  }

  cancelReset(): void {
    this.resetToken = null;
    this.qrDataUrl.set(null);
    this.provisioningUri.set(null);
    this.code = '';
    this.errorMessage.set(null);
    this.mode.set('verify');
  }

  private extractErrorDetail(err: unknown, fallback: string): string {
    // Fixed 2026-09-16: this used to always show the generic fallback, which
    // once masked a real server error (a decryption key mismatch) as if it
    // were an ordinary wrong code — read the actual backend detail when
    // there is one.
    return (err as { error?: { detail?: string } })?.error?.detail ?? fallback;
  }
}
