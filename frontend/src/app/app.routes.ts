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
    path: 'employees',
    loadComponent: () =>
      import('./features/employees/employee-list/employee-list.component').then(
        (m) => m.EmployeeListComponent
      ),
    canActivate: [authGuard],
  },
  {
    path: 'employees/new',
    loadComponent: () =>
      import('./features/employees/employee-form/employee-form.component').then(
        (m) => m.EmployeeFormComponent
      ),
    canActivate: [authGuard],
  },
  {
    path: 'employees/:id',
    loadComponent: () =>
      import('./features/employees/employee-detail/employee-detail.component').then(
        (m) => m.EmployeeDetailComponent
      ),
    canActivate: [authGuard],
  },
  {
    path: 'org',
    loadComponent: () =>
      import('./features/org/org-page/org-page.component').then((m) => m.OrgPageComponent),
    canActivate: [authGuard],
  },
  {
    path: '',
    loadComponent: () => import('./features/home/home.component').then((m) => m.HomeComponent),
    canActivate: [authGuard],
  },
];
