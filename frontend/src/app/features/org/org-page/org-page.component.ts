import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import {
  ButtonDirective,
  CardBodyComponent,
  CardComponent,
  ColComponent,
  ContainerComponent,
  FormControlDirective,
  FormLabelDirective,
  FormSelectDirective,
  RowComponent,
} from '@coreui/angular';

import { Department, HeadcountEntry, Position } from '../../../core/models/org.model';
import { OrgService } from '../org.service';

@Component({
  selector: 'app-org-page',
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
    FormLabelDirective,
    FormSelectDirective,
    RowComponent,
  ],
  templateUrl: './org-page.component.html',
})
export class OrgPageComponent implements OnInit {
  private readonly org = inject(OrgService);

  readonly departments = signal<Department[]>([]);
  readonly positions = signal<Position[]>([]);
  readonly headcount = signal<HeadcountEntry[]>([]);
  readonly errorMessage = signal<string | null>(null);

  newDepartmentName = '';
  newPositionTitle = '';
  newPositionDepartmentId = '';
  newPositionReportsTo = '';

  async ngOnInit(): Promise<void> {
    await this.refresh();
  }

  private async refresh(): Promise<void> {
    const [departments, positions, headcount] = await Promise.all([
      this.org.listDepartments(),
      this.org.listPositions(),
      this.org.getHeadcount(),
    ]);
    this.departments.set(departments);
    this.positions.set(positions);
    this.headcount.set(headcount);
  }

  async onAddDepartment(): Promise<void> {
    this.errorMessage.set(null);
    try {
      await this.org.createDepartment(this.newDepartmentName);
      this.newDepartmentName = '';
      await this.refresh();
    } catch {
      this.errorMessage.set('Could not create department.');
    }
  }

  async onAddPosition(): Promise<void> {
    this.errorMessage.set(null);
    try {
      await this.org.createPosition(
        this.newPositionTitle,
        this.newPositionDepartmentId,
        this.newPositionReportsTo || null
      );
      this.newPositionTitle = '';
      this.newPositionReportsTo = '';
      await this.refresh();
    } catch {
      this.errorMessage.set('Could not create position.');
    }
  }
}
