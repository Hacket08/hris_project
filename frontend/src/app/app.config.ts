import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { ApplicationConfig, provideZoneChangeDetection } from '@angular/core';
import { provideRouter } from '@angular/router';

import { authInterceptor } from './core/auth/auth.interceptor';
import { routes } from './app.routes';

// No icon set registered yet: @coreui/icons-angular@5.2.25 (the Angular
// 18-compatible release) uses IconSetService.icons = {...}, not a
// provideIcons()-style function (that API landed in a later CoreUI major).
// Phase 0's auth screens don't render any <svg cIcon> yet, so there's
// nothing to register — add IconSetService wiring here when a Phase 1+
// screen actually needs an icon.
export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(routes),
    provideHttpClient(withInterceptors([authInterceptor])),
  ],
};
