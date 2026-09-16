import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { environment } from '../../../environments/environment';
import { Department, HeadcountEntry, Position } from '../../core/models/org.model';

@Injectable({ providedIn: 'root' })
export class OrgService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiBaseUrl}/org`;

  listDepartments(): Promise<Department[]> {
    return firstValueFrom(this.http.get<Department[]>(`${this.base}/departments`));
  }

  createDepartment(name: string): Promise<Department> {
    return firstValueFrom(this.http.post<Department>(`${this.base}/departments`, { name }));
  }

  listPositions(): Promise<Position[]> {
    return firstValueFrom(this.http.get<Position[]>(`${this.base}/positions`));
  }

  createPosition(
    title: string,
    departmentId: string,
    reportsToPositionId: string | null
  ): Promise<Position> {
    return firstValueFrom(
      this.http.post<Position>(`${this.base}/positions`, {
        title,
        department_id: departmentId,
        reports_to_position_id: reportsToPositionId,
      })
    );
  }

  getHeadcount(): Promise<HeadcountEntry[]> {
    return firstValueFrom(this.http.get<HeadcountEntry[]>(`${this.base}/headcount`));
  }
}
