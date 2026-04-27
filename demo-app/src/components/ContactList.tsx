import type { Contact } from "../types";
import { ContactCard } from "./ContactCard";

interface ContactListProps {
  contacts: Contact[];
  onEdit: (contact: Contact) => void;
  onDelete: (indexToDelete: number) => void;
}

export function ContactList({ contacts, onEdit, onDelete }: ContactListProps): JSX.Element {
  if (contacts.length === 0) {
    return (
      <section className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-slate-500">
        No contacts found.
      </section>
    );
  }

  return (
    <section className="grid grid-cols-1 gap-4">
      {contacts.map((contact, index) => (
        <ContactCard
          key={contact.id}
          contact={contact}
          onEdit={() => onEdit(contact)}
          onDelete={() => onDelete(index + 1)}
        />
      ))}
    </section>
  );
}
