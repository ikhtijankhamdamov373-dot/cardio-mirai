import { Card } from "@/components/ui/Card";

export const metadata = { title: "Contact | Cardio MIRAI" };

const CHANNELS = [
  { label: "Email", value: "info@cardiomirai.com", href: "mailto:info@cardiomirai.com" },
  { label: "Website", value: "cardiomirai.com", href: "https://cardiomirai.com" },
  { label: "Institution", value: "Institute of Science Tokyo", href: undefined },
  { label: "GitHub", value: "Cardio MIRAI on GitHub", href: "https://github.com/ikhtijankhamdamov373-dot/cardio-mirai" },
];

export default function ContactPage() {
  return (
    <section className="mx-auto max-w-3xl px-5 py-16">
      <h1 className="text-3xl font-black text-navy">Contact</h1>
      <p className="mt-3 text-muted">
        For collaboration, research inquiries, or feedback on Cardio MIRAI.
      </p>

      <Card className="mt-8">
        <p className="font-bold text-navy">Send a message</p>
        <p className="mt-1 text-xs text-muted">
          Opens your email client — no message data is sent to or stored by
          this website.
        </p>
        {/* mailto form: composes an email locally, no server submission,
            no backend endpoint exists for contact yet. */}
        <form
          action="mailto:info@cardiomirai.com"
          method="get"
          encType="text/plain"
          className="mt-4 grid gap-4"
        >
          <label className="text-sm font-semibold text-ink">
            Name
            <input
              name="name"
              required
              className="mt-1 w-full rounded-card border border-line px-3 py-2 text-sm"
            />
          </label>
          <label className="text-sm font-semibold text-ink">
            Your email
            <input
              type="email"
              name="reply_to"
              required
              className="mt-1 w-full rounded-card border border-line px-3 py-2 text-sm"
            />
          </label>
          <label className="text-sm font-semibold text-ink">
            Institution
            <input
              name="institution"
              className="mt-1 w-full rounded-card border border-line px-3 py-2 text-sm"
            />
          </label>
          <label className="text-sm font-semibold text-ink">
            Message
            <textarea
              name="body"
              required
              rows={5}
              className="mt-1 w-full rounded-card border border-line px-3 py-2 text-sm"
            />
          </label>
          <button
            type="submit"
            className="justify-self-start rounded-card bg-red px-5 py-3 text-sm font-bold text-white shadow-cta hover:brightness-110"
          >
            Open in email client
          </button>
        </form>
      </Card>

      <div className="mt-8 grid gap-3 sm:grid-cols-2">
        {CHANNELS.map((c) => (
          <Card key={c.label}>
            <p className="text-xs font-bold uppercase tracking-wide text-muted">{c.label}</p>
            {c.href ? (
              <a href={c.href} className="mt-1 block text-sm font-semibold text-blue">
                {c.value}
              </a>
            ) : (
              <p className="mt-1 text-sm font-semibold text-ink">{c.value}</p>
            )}
          </Card>
        ))}
      </div>
    </section>
  );
}
