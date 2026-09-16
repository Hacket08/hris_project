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

  code = '';
  readonly submitting = signal(false);
  readonly errorMessage = signal<string | null>(null);

  async onSubmit(): Promise<void> {
    this.errorMessage.set(null);
    this.submitting.set(true);
    try {
      await this.auth.verifyMfa(this.code);
      await this.router.navigateByUrl('/');
    } catch {
      this.errorMessage.set('Invalid or expired code.');
    } finally {
      this.submitting.set(false);
    }
  }
}
