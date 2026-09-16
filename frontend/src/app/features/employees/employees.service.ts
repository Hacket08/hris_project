import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { environment } from '../../../environments/environment';
import { EmployeeCreate, EmployeeDetail, EmployeeListItem, EmployeeUpdate } from '../../core/models/employee.model';

@Injectable({ providedIn: 'root' })
export class EmployeesService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiBaseUrl}/employees`;

  list(): Promise<EmployeeListItem[]> {
    return firstValueFrom(this.http.get<EmployeeListItem[]>(this.base));
  }

  get(id: string): Promise<EmployeeDetail> {
    return firstValueFrom(this.http.get<EmployeeDetail>(`${this.base}/${id}`));
  }

  create(payload: EmployeeCreate): Promise<EmployeeDetail> {
    return firstValueFrom(this.http.post<EmployeeDetail>(this.base, payload));
  }

  update(id: string, payload: EmployeeUpdate): Promise<EmployeeDetail> {
    return firstValueFrom(this.http.patch<EmployeeDetail>(`${this.base}/${id}`, payload));
  }
}
