export interface Department {
  id: string;
  name: string;
}

export interface Position {
  id: string;
  title: string;
  department_id: string;
  department_name: string;
  reports_to_position_id: string | null;
  reports_to_title: string | null;
}

export interface HeadcountEntry {
  department_id: string;
  department_name: string;
  position_id: string;
  position_title: string;
  headcount: number;
}
