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

/** Personal-info/employment fields added 2026-09-16 (05_data_model.md) —
 * grounded in standard Philippine 201-file/HR recordkeeping conventions. */
interface EmployeePersonalInfo {
  middle_name?: string | null;
  suffix?: string | null;
  nickname?: string | null;
  maiden_name?: string | null;
  gender?: string | null;
  birthdate?: string | null;
  birth_place?: string | null;
  civil_status?: string | null;
  spouse_name?: string | null;
  is_solo_parent?: boolean;
  is_minimum_wage_earner?: boolean;
  religion?: string | null;
  nationality?: string | null;
  corporate_email?: string | null;
  personal_email?: string | null;
  permanent_address?: string | null;
  current_address?: string | null;
  regularization_date?: string | null;
  position_title?: string | null;
}

export interface EmployeeDetail extends EmployeePersonalInfo {
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

export interface EmployeeCreate extends EmployeePersonalInfo {
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

export interface EmployeeUpdate extends EmployeePersonalInfo {
  first_name?: string;
  last_name?: string;
  contact_info?: string;
  employment_status?: EmploymentStatus;
  position_id?: string;
}
