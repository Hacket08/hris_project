import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ButtonDirective, CardBodyComponent, CardComponent, ContainerComponent } from '@coreui/angular';

import { EmployeeListItem } from '../../../core/models/employee.model';
import { EmployeesService } from '../employees.service';

@Component({
  selector: 'app-employee-list',
  standalone: true,
  imports: [CommonModule, RouterLink, ButtonDirective, CardBodyComponent, CardComponent, ContainerComponent],
  templateUrl: './employee-list.component.html',
})
export class EmployeeListComponent implements OnInit {
  private readonly employees = inject(EmployeesService);

  readonly items = signal<EmployeeListItem[]>([]);
  readonly loading = signal(true);
  readonly errorMessage = signal<string | null>(null);

  async ngOnInit(): Promise<void> {
    try {
      this.items.set(await this.employees.list());
    } catch {
      this.errorMessage.set('Could not load employees.');
    } finally {
      this.loading.set(false);
    }
  }
}
