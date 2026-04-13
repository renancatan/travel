import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Travel Project",
  description: "Travel content copilot for albums, uploads, and visual review.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

