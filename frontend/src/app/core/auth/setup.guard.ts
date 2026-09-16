import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AuthService } from './auth.service';

/** Shows the setup wizard instead of the login screen when no account exists yet. */
export const redirectToSetupIfRequiredGuard: CanActivateFn = async () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  const setupRequired = await auth.checkSetupRequired();
  return setupRequired ? router.createUrlTree(['/setup']) : true;
};

/** The setup wizard is a one-time, first-run-only screen — send everyone
 * else to login once an account exists (matches the backend's 404/410 on
 * the setup endpoints once setup is complete). */
export const setupNotYetCompleteGuard: CanActivateFn = async () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  const setupRequired = await auth.checkSetupRequired();
  return setupRequired ? true : router.createUrlTree(['/login']);
};
