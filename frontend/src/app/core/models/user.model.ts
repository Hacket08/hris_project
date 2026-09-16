export type UserRole = 'hr_admin' | 'hr_staff' | 'manager' | 'employee' | 'auditor_read';

export interface User {
  id: string;
  username: string;
  email: string;
  role: UserRole;
  is_active: boolean;
}
