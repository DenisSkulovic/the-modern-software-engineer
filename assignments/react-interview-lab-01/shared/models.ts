export const statuses = ["New", "Triaged", "In Progress", "Resolved"] as const;
export const priorities = ["Low", "Medium", "High", "Urgent"] as const;
export type Status = (typeof statuses)[number];
export type Priority = (typeof priorities)[number];
export interface Team {
  id: string;
  name: string;
}
export interface Operator {
  id: string;
  name: string;
  teamId: string;
}
export interface Activity {
  id: string;
  at: string;
  text: string;
}
export interface Ticket {
  id: string;
  title: string;
  customer: string;
  teamId: string;
  status: Status;
  priority: Priority;
  assigneeId: string | null;
  createdAt: string;
  updatedAt: string;
  description: string;
  note: string;
  tags: string[];
}
export interface Query {
  teamId: string;
  q: string;
  status: string;
  priority: string;
  sort: string;
  page: number;
  pageSize: number;
}
export interface Page {
  items: Ticket[];
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
}
export interface Summary {
  open: number;
  urgent: number;
  mine: number;
  resolved: number;
}
export const defaultQuery: Query = {
  teamId: "platform",
  q: "",
  status: "",
  priority: "",
  sort: "updated",
  page: 1,
  pageSize: 10,
};
