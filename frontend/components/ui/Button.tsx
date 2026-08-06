import Link from "next/link";
import { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost";

const variantClasses: Record<Variant, string> = {
  primary:
    "bg-red text-white shadow-cta hover:brightness-110 focus-visible:outline-white",
  secondary:
    "bg-white text-navy border border-line hover:border-blue hover:text-blue",
  ghost: "bg-transparent text-blue hover:bg-blue-soft",
};

const base =
  "inline-flex items-center justify-center gap-2 rounded-card px-5 py-3 font-bold text-sm transition-colors duration-150 disabled:opacity-50 disabled:cursor-not-allowed";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  href?: string;
  children: ReactNode;
}

/** Renders as a Link when `href` is given, otherwise a native button. */
export function Button({
  variant = "primary",
  href,
  className = "",
  children,
  ...rest
}: ButtonProps) {
  const classes = `${base} ${variantClasses[variant]} ${className}`;

  if (href) {
    return (
      <Link href={href} className={classes}>
        {children}
      </Link>
    );
  }
  return (
    <button className={classes} {...rest}>
      {children}
    </button>
  );
}
