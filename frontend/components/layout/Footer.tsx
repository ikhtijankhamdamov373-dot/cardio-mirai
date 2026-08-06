import Link from "next/link";

export function Footer() {
  return (
    <footer className="border-t border-line bg-navy text-white/80">
      <div className="mx-auto max-w-6xl px-5 py-10 grid gap-8 md:grid-cols-3">
        <div>
          <p className="text-white font-bold">Cardio MIRAI</p>
          <p className="mt-1 text-sm">AI Platform for Precision Cardiovascular Medicine</p>
          <p className="mt-4 text-xs text-white/60">
            Research prototype. Not a medical device. Not intended for
            diagnosis or treatment decisions.
          </p>
        </div>

        <div>
          <p className="text-white font-bold text-sm">Platform</p>
          <ul className="mt-3 space-y-2 text-sm">
            <li><Link href="/ecg-ai" className="hover:text-white">ECG AI</Link></li>
            <li><Link href="/calculators" className="hover:text-white">Clinical Calculators</Link></li>
            <li><Link href="/knowledge" className="hover:text-white">Knowledge Center</Link></li>
            <li><Link href="/research" className="hover:text-white">Research Hub</Link></li>
          </ul>
        </div>

        <div>
          <p className="text-white font-bold text-sm">Contact</p>
          <ul className="mt-3 space-y-2 text-sm">
            <li>
              <a href="mailto:info@cardiomirai.com" className="hover:text-white">
                info@cardiomirai.com
              </a>
            </li>
            <li>
              <a href="https://cardiomirai.com" className="hover:text-white">
                cardiomirai.com
              </a>
            </li>
            <li><Link href="/about" className="hover:text-white">About</Link></li>
            <li><Link href="/contact" className="hover:text-white">Contact form</Link></li>
          </ul>
        </div>
      </div>

      <div className="border-t border-white/10 px-5 py-4 text-center text-xs text-white/50">
        © {new Date().getFullYear()} Cardio MIRAI. All rights reserved.
      </div>
    </footer>
  );
}
