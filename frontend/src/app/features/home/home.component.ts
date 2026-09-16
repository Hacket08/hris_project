import { CommonModule } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import {
  ButtonDirective,
  CardBodyComponent,
  CardComponent,
  ColComponent,
  ContainerComponent,
  RowComponent,
} from '@coreui/angular';

import { AuthService } from '../../core/auth/auth.service';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    ButtonDirective,
    CardBodyComponent,
    CardComponent,
    ColComponent,
    ContainerComponent,
    RowComponent,
  ],
  template: `
    <c-container class="py-5">
      <c-row class="justify-content-center">
        <c-col lg="6" md="8">
          <c-card class="p-4 text-center">
            <c-card-body class="d-flex flex-column gap-3">
              <h2 class="h5 mb-0">HRIS System</h2>
              @if (auth.currentUser(); as user) {
                <p class="mb-0">Signed in as {{ user.username }} ({{ user.role }})</p>
              }
              <div class="d-flex justify-content-center gap-2">
                <a cButton color="primary" routerLink="/employees">Employees</a>
                <a cButton color="primary" routerLink="/org">Org chart</a>
              </div>
              <button cButton color="secondary" (click)="auth.logout()">Sign out</button>
            </c-card-body>
          </c-card>
        </c-col>
      </c-row>
    </c-container>
  `,
})
export class HomeComponent implements OnInit {
  readonly auth = inject(AuthService);

  ngOnInit(): void {
    if (!this.auth.currentUser()) {
      this.auth.loadCurrentUser();
    }
  }
}
