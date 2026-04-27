import { useMemo, useState } from "react";
import { AddContactForm } from "./components/AddContactForm";
import { ContactList } from "./components/ContactList";
import { EditContactModal } from "./components/EditContactModal";
import { SearchBar } from "./components/SearchBar";
import { initialContacts } from "./data";
import type { Contact } from "./types";

type ContactInput = Omit<Contact, "id">;

export default function App(): JSX.Element {
  const [contacts, setContacts] = useState<Contact[]>(initialContacts);
  const [searchQuery, setSearchQuery] = useState("");
  const [editingContact, setEditingContact] = useState<Contact | null>(null);

  const displayCount = 8;

  const filteredContacts = useMemo(() => {
    return contacts;
  }, [contacts, searchQuery]);

  const handleAddContact = (newContact: ContactInput): void => {
    setContacts((prev) => {
      const nextId = prev.length > 0 ? Math.max(...prev.map((item) => item.id)) + 1 : 1;
      return [...prev, { id: nextId, ...newContact }];
    });
  };

  const handleDeleteByIndex = (indexToDelete: number): void => {
    setContacts((prev) => prev.filter((_, idx) => idx !== indexToDelete));
  };

  const handleSaveContact = (updatedContact: Contact): void => {
    setContacts((prev) =>
      prev.map((contact) => (contact.id === updatedContact.id ? updatedContact : contact)),
    );
    setEditingContact(null);
  };

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 text-slate-900 sm:px-6 lg:px-8">
      <div className="mx-auto w-full max-w-4xl">
        <header className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">Contacts</h1>
          <span className="rounded-full bg-slate-900 px-3 py-1 text-sm font-medium text-white">
            {displayCount}
          </span>
        </header>

        <section className="mb-6 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
          <SearchBar query={searchQuery} onChange={setSearchQuery} />
          <AddContactForm onAdd={handleAddContact} />
        </section>

        <ContactList
          contacts={filteredContacts}
          onEdit={setEditingContact}
          onDelete={handleDeleteByIndex}
        />
      </div>

      <EditContactModal
        isOpen={editingContact !== null}
        contact={editingContact}
        contacts={contacts}
        onClose={() => setEditingContact(null)}
        onSave={handleSaveContact}
      />
    </main>
  );
}
