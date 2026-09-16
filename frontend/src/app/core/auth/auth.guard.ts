import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AuthService } from './auth.service';

/**
 * UX convenience only — the real security boundary is the FastAPI RBAC
 * dependency (backend/app/auth/deps.py::require_role), per dev plan §5.2.
 * Never rely on this guard alone.
 */
export const authGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (auth.isAuthenticated()) {
    return true;
  }
  return router.createUrlTree(['/login']);
};
