import type { Contact } from "../types";

interface ContactCardProps {
  contact: Contact;
  onEdit: () => void;
  onDelete: () => void;
}

const categoryStyles: Record<Contact["category"], string> = {
  Work: "bg-blue-100 text-blue-700",
  Friend: "bg-green-100 text-green-700",
  Family: "bg-purple-100 text-purple-700",
};

export function ContactCard({ contact, onEdit, onDelete }: ContactCardProps): JSX.Element {
  return (
    <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">{contact.name || "Untitled Contact"}</h3>
          <p className="mt-1 text-sm text-slate-600">{contact.email || "No email provided"}</p>
          <p className="mt-1 text-sm text-slate-600">{contact.phone || "No phone provided"}</p>
        </div>
        <span
          className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${categoryStyles[contact.category]}`}
        >
          {contact.category}
        </span>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={onEdit}
          className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-blue-700"
        >
          Edit
        </button>
        <button
          type="button"
          onClick={onDelete}
          className="rounded-md bg-red-600 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-red-700"
        >
          Delete
        </button>
      </div>
    </article>
  );
}
