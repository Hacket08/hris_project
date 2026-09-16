import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
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
  FormSelectDirective,
  RowComponent,
} from '@coreui/angular';

import { EmploymentStatus } from '../../../core/models/employee.model';
import { Position } from '../../../core/models/org.model';
import { OrgService } from '../../org/org.service';
import { EmployeesService } from '../employees.service';

@Component({
  selector: 'app-employee-form',
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
    FormSelectDirective,
    RowComponent,
  ],
  templateUrl: './employee-form.component.html',
})
export class EmployeeFormComponent implements OnInit {
  private readonly employees = inject(EmployeesService);
  private readonly org = inject(OrgService);
  private readonly router = inject(Router);

  readonly positions = signal<Position[]>([]);
  readonly submitting = signal(false);
  readonly errorMessage = signal<string | null>(null);

  firstName = '';
  lastName = '';
  contactInfo = '';
  employmentStatus: EmploymentStatus = 'probationary';
  hireDate = '';
  positionId = '';
  sssNumber = '';
  philhealthNumber = '';
  pagibigNumber = '';
  tin = '';

  // Personal-info/employment fields added 2026-09-16 (05_data_model.md).
  middleName = '';
  suffix = '';
  nickname = '';
  maidenName = '';
  gender = '';
  birthdate = '';
  birthPlace = '';
  civilStatus = '';
  spouseName = '';
  isSoloParent = false;
  isMinimumWageEarner = false;
  religion = '';
  nationality = '';
  corporateEmail = '';
  personalEmail = '';
  permanentAddress = '';
  currentAddress = '';
  regularizationDate = '';
  positionTitle = '';

  async ngOnInit(): Promise<void> {
    this.positions.set(await this.org.listPositions());
  }

  async onSubmit(): Promise<void> {
    this.errorMessage.set(null);
    this.submitting.set(true);
    try {
      const created = await this.employees.create({
        first_name: this.firstName,
        last_name: this.lastName,
        contact_info: this.contactInfo || undefined,
        employment_status: this.employmentStatus,
        hire_date: this.hireDate,
        position_id: this.positionId,
        sss_number: this.sssNumber || undefined,
        philhealth_number: this.philhealthNumber || undefined,
        pagibig_number: this.pagibigNumber || undefined,
        tin: this.tin || undefined,
        middle_name: this.middleName || undefined,
        suffix: this.suffix || undefined,
        nickname: this.nickname || undefined,
        maiden_name: this.maidenName || undefined,
        gender: this.gender || undefined,
        birthdate: this.birthdate || undefined,
        birth_place: this.birthPlace || undefined,
        civil_status: this.civilStatus || undefined,
        spouse_name: this.spouseName || undefined,
        is_solo_parent: this.isSoloParent,
        is_minimum_wage_earner: this.isMinimumWageEarner,
        religion: this.religion || undefined,
        nationality: this.nationality || undefined,
        corporate_email: this.corporateEmail || undefined,
        personal_email: this.personalEmail || undefined,
        permanent_address: this.permanentAddress || undefined,
        current_address: this.currentAddress || undefined,
        regularization_date: this.regularizationDate || undefined,
        position_title: this.positionTitle || undefined,
      });
      await this.router.navigate(['/employees', created.id]);
    } catch (err: unknown) {
      this.errorMessage.set(
        (err as { error?: { detail?: string } })?.error?.detail ?? 'Could not create employee.'
      );
    } finally {
      this.submitting.set(false);
    }
  }
}
