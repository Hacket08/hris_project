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

type WizardStep = 'account' | 'mfa';

@Component({
  selector: 'app-setup',
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
  templateUrl: './setup.component.html',
})
export class SetupComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  readonly step = signal<WizardStep>('account');
  readonly submitting = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly qrDataUrl = signal<string | null>(null);
  readonly provisioningUri = signal<string | null>(null);

  username = '';
  email = '';
  password = '';
  confirmPassword = '';
  code = '';

  private setupToken: string | null = null;

  async onSubmitAccount(): Promise<void> {
    this.errorMessage.set(null);
    if (this.password !== this.confirmPassword) {
      this.errorMessage.set('Password and confirmation do not match.');
      return;
    }

    this.submitting.set(true);
    try {
      const res = await this.auth.initSetup(this.username, this.email, this.password);
      this.setupToken = res.setup_token;
      this.provisioningUri.set(res.provisioning_uri);
      this.qrDataUrl.set(await QRCode.toDataURL(res.provisioning_uri));
      this.step.set('mfa');
    } catch (err: unknown) {
      this.errorMessage.set(this.extractErrorDetail(err, 'Could not start setup.'));
    } finally {
      this.submitting.set(false);
    }
  }

  async onSubmitCode(): Promise<void> {
    this.errorMessage.set(null);
    if (!this.setupToken) {
      this.errorMessage.set('Setup session lost — start again.');
      this.step.set('account');
      return;
    }

    this.submitting.set(true);
    try {
      await this.auth.confirmSetup(this.setupToken, this.code);
      await this.router.navigateByUrl('/login');
    } catch (err: unknown) {
      this.errorMessage.set(this.extractErrorDetail(err, 'Invalid or expired code.'));
    } finally {
      this.submitting.set(false);
    }
  }

  private extractErrorDetail(err: unknown, fallback: string): string {
    return (err as { error?: { detail?: string } })?.error?.detail ?? fallback;
  }
}
