import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
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

@Component({
  selector: 'app-change-password',
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
  templateUrl: './change-password.component.html',
})
export class ChangePasswordComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  currentPassword = '';
  newPassword = '';
  confirmPassword = '';
  readonly submitting = signal(false);
  readonly errorMessage = signal<string | null>(null);

  async onSubmit(): Promise<void> {
    this.errorMessage.set(null);

    if (this.newPassword !== this.confirmPassword) {
      this.errorMessage.set('New password and confirmation do not match.');
      return;
    }

    this.submitting.set(true);
    try {
      await this.auth.changePassword(this.currentPassword, this.newPassword);
      await this.router.navigateByUrl('/');
    } catch (err: unknown) {
      const detail =
        (err as { error?: { detail?: string } })?.error?.detail ?? 'Could not change password.';
      this.errorMessage.set(detail);
    } finally {
      this.submitting.set(false);
    }
  }
}
