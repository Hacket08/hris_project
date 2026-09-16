export type EmploymentStatus = 'probationary' | 'regular' | 'separated';
export type EmploymentChangeType = 'hire' | 'transfer' | 'promotion' | 'status_change';

export interface EmployeeListItem {
  id: string;
  first_name: string;
  last_name: string;
  employment_status: EmploymentStatus;
  hire_date: string;
  position_id: string;
}

export interface EmploymentHistoryEntry {
  id: string;
  change_type: EmploymentChangeType;
  old_value: string | null;
  new_value: string | null;
  effective_date: string;
  created_at: string;
}

export interface EmployeeDetail {
  id: string;
  first_name: string;
  last_name: string;
  contact_info: string | null;
  employment_status: EmploymentStatus;
  hire_date: string;
  position_id: string;
  sss_number: string | null;
  philhealth_number: string | null;
  pagibig_number: string | null;
  tin: string | null;
  history: EmploymentHistoryEntry[];
}

export interface EmployeeCreate {
  first_name: string;
  last_name: string;
  contact_info?: string;
  employment_status: EmploymentStatus;
  hire_date: string;
  position_id: string;
  sss_number?: string;
  philhealth_number?: string;
  pagibig_number?: string;
  tin?: string;
}

export interface EmployeeUpdate {
  first_name?: string;
  last_name?: string;
  contact_info?: string;
  employment_status?: EmploymentStatus;
  position_id?: string;
}
