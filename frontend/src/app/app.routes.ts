import { Routes } from '@angular/router';

import { authGuard } from './core/auth/auth.guard';
import { redirectToSetupIfRequiredGuard, setupNotYetCompleteGuard } from './core/auth/setup.guard';

export const routes: Routes = [
  {
    path: 'setup',
    loadComponent: () => import('./features/auth/setup/setup.component').then((m) => m.SetupComponent),
    canActivate: [setupNotYetCompleteGuard],
  },
  {
    path: 'login',
    loadComponent: () =>
      import('./features/auth/login/login.component').then((m) => m.LoginComponent),
    canActivate: [redirectToSetupIfRequiredGuard],
  },
  {
    path: 'mfa-verify',
    loadComponent: () =>
      import('./features/auth/mfa-verify/mfa-verify.component').then((m) => m.MfaVerifyComponent),
  },
  {
    path: 'change-password',
    loadComponent: () =>
      import('./features/auth/change-password/change-password.component').then(
        (m) => m.ChangePasswordComponent
      ),
    canActivate: [authGuard],
  },
  {
    path: '',
    loadComponent: () => import('./features/home/home.component').then((m) => m.HomeComponent),
    canActivate: [authGuard],
  },
];
