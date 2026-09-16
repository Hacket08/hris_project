import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import {
  ButtonDirective,
  CardBodyComponent,
  CardComponent,
  ColComponent,
  ContainerComponent,
  FormLabelDirective,
  FormSelectDirective,
  RowComponent,
} from '@coreui/angular';

import { EmployeeDetail } from '../../../core/models/employee.model';
import { Position } from '../../../core/models/org.model';
import { OrgService } from '../../org/org.service';
import { EmployeesService } from '../employees.service';

@Component({
  selector: 'app-employee-detail',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ButtonDirective,
    CardBodyComponent,
    CardComponent,
    ColComponent,
    ContainerComponent,
    FormLabelDirective,
    FormSelectDirective,
    RowComponent,
  ],
  templateUrl: './employee-detail.component.html',
})
export class EmployeeDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly employees = inject(EmployeesService);
  private readonly org = inject(OrgService);

  readonly employee = signal<EmployeeDetail | null>(null);
  readonly positions = signal<Position[]>([]);
  readonly loading = signal(true);
  readonly errorMessage = signal<string | null>(null);
  readonly saving = signal(false);

  selectedPositionId = '';

  async ngOnInit(): Promise<void> {
    const id = this.route.snapshot.paramMap.get('id')!;
    try {
      const [employee, positions] = await Promise.all([this.employees.get(id), this.org.listPositions()]);
      this.employee.set(employee);
      this.positions.set(positions);
      this.selectedPositionId = employee.position_id;
    } catch {
      this.errorMessage.set('Could not load employee.');
    } finally {
      this.loading.set(false);
    }
  }

  positionTitle(id: string): string {
    return this.positions().find((p) => p.id === id)?.title ?? id;
  }

  async onChangePosition(): Promise<void> {
    const current = this.employee();
    if (!current || this.selectedPositionId === current.position_id) return;

    this.saving.set(true);
    this.errorMessage.set(null);
    try {
      this.employee.set(await this.employees.update(current.id, { position_id: this.selectedPositionId }));
    } catch {
      this.errorMessage.set('Could not update position.');
    } finally {
      this.saving.set(false);
    }
  }
}
