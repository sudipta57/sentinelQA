export type ContactCategory = "Friend" | "Work" | "Family";

export interface Contact {
  id: number;
  name: string;
  email: string;
  phone: string;
  category: ContactCategory;
}
