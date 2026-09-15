"use client";

import Link from "next/link";
import { useState } from "react";

const NAV_LINKS = [
  { href: "/", label: "Home" },
  { href: "/ecg-ai", label: "ECG AI" },
  { href: "/acs", label: "Emergency Cardiology" },
  { href: "/calculators", label: "Clinical Calculators" },
  { href: "/knowledge", label: "Knowledge Center" },
  { href: "/research", label: "Research Hub" },
  { href: "/ai-assistant", label: "AI Assistant" },
  { href: "/about", label: "About" },
  { href: "/contact", label: "Contact" },
];

export function Navbar() {
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-20 border-b border-line bg-white/95 backdrop-blur">
      <nav
        aria-label="Primary navigation"
        className="mx-auto flex max-w-6xl items-center gap-4 px-5 py-3"
      >
        <Link href="/" className="flex min-w-max items-center gap-2.5 text-navy">
          <span className="grid h-9 w-9 place-items-center rounded-[10px] bg-gradient-to-br from-red to-blue text-sm font-black text-white shadow-cta">
            CM
          </span>
          <span className="leading-tight">
            <strong className="block text-sm">Cardio MIRAI</strong>
            <span className="block text-[11px] text-muted -mt-0.5">
              AI Platform for Precision Cardiovascular Medicine
            </span>
          </span>
        </Link>

        <button
          className="ml-auto rounded-card border border-line p-2 md:hidden"
          aria-expanded={open}
          aria-controls="primary-menu"
          aria-label={open ? "Close menu" : "Open menu"}
          onClick={() => setOpen((v) => !v)}
        >
          <span className="block h-0.5 w-5 bg-navy" />
          <span className="mt-1 block h-0.5 w-5 bg-navy" />
          <span className="mt-1 block h-0.5 w-5 bg-navy" />
        </button>

        <ul
          id="primary-menu"
          className="hidden items-center gap-5 md:ml-auto md:flex"
        >
          {NAV_LINKS.map((link) => (
            <li key={link.href}>
              <Link
                href={link.href}
                className="text-sm font-semibold text-muted hover:text-blue"
              >
                {link.label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>

      {open && (
        <ul id="primary-menu-mobile" className="border-t border-line px-5 py-3 md:hidden">
          {NAV_LINKS.map((link) => (
            <li key={link.href} className="py-2">
              <Link
                href={link.href}
                onClick={() => setOpen(false)}
                className="text-sm font-semibold text-ink"
              >
                {link.label}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </header>
  );
}
