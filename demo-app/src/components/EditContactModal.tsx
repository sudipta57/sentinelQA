import { useEffect, useState } from "react";
import type { Contact, ContactCategory } from "../types";

interface EditContactModalProps {
  isOpen: boolean;
  contact: Contact | null;
  contacts: Contact[];
  onClose: () => void;
  onSave: (contact: Contact) => void;
}

export function EditContactModal({
  isOpen,
  contact,
  contacts,
  onClose,
  onSave,
}: EditContactModalProps): JSX.Element | null {
  const [formData, setFormData] = useState<Contact | null>(contact);

  useEffect(() => {
    setFormData(contact);
  }, [contact]);

  if (!isOpen || !formData) {
    return null;
  }

  const handleSave = (event: React.FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    onSave({ ...formData, id: contacts[0].id });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/55 px-4">
      <div className="w-full max-w-md rounded-xl bg-white p-5 shadow-xl">
        <h2 className="mb-4 text-xl font-semibold text-slate-900">Edit Contact</h2>

        <form onSubmit={handleSave} className="space-y-3">
          <input
            type="text"
            value={formData.name}
            onChange={(event) => setFormData((prev) => (prev ? { ...prev, name: event.target.value } : prev))}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none ring-blue-500 transition focus:ring"
          />
          <input
            type="email"
            value={formData.email}
            onChange={(event) =>
              setFormData((prev) => (prev ? { ...prev, email: event.target.value } : prev))
            }
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none ring-blue-500 transition focus:ring"
          />
          <input
            type="tel"
            value={formData.phone}
            onChange={(event) => setFormData((prev) => (prev ? { ...prev, phone: event.target.value } : prev))}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none ring-blue-500 transition focus:ring"
          />
          <select
            value={formData.category}
            onChange={(event) =>
              setFormData((prev) =>
                prev ? { ...prev, category: event.target.value as ContactCategory } : prev,
              )
            }
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none ring-blue-500 transition focus:ring"
          >
            <option value="Friend">Friend</option>
            <option value="Work">Work</option>
            <option value="Family">Family</option>
          </select>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              Save
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
