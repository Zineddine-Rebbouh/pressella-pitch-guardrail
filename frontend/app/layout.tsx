import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Pressella — Pitch Compliance Review Console",
  description:
    "System compliance and evaluation console for PR pitch generation and guardrail verification.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col font-sans bg-bg-base text-text-primary">
        {children}
      </body>
    </html>
  );
}
