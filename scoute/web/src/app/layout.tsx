import type { Metadata, Viewport } from "next";
import "@fontsource/public-sans/400.css";
import "@fontsource/public-sans/500.css";
import "@fontsource/public-sans/600.css";
import "@fontsource/public-sans/700.css";
import "@fontsource/public-sans/800.css";
import "./globals.css";
import { AuthProvider } from "@/components/AuthProvider";

export const metadata: Metadata = {
  title: {
    default: "Scoute — products that still make money after 2026 tariffs",
    template: "%s · Scoute",
  },
  description:
    "Real profit after tariffs, fees, ads and returns. The most you can pay your supplier. An alert the moment it changes.",
  metadataBase: new URL("https://scoute.app"),
  openGraph: {
    title: "Scoute — products that still make money after 2026 tariffs",
    description:
      "Real profit after tariffs, fees, ads and returns. The most you can pay your supplier. An alert the moment it changes.",
    siteName: "Scoute",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Scoute — products that still make money after 2026 tariffs",
    description:
      "Real profit after tariffs, fees, ads and returns. The most you can pay your supplier. An alert the moment it changes.",
  },
  icons: {
    icon: "/favicon.ico",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#EEF1F3",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="font-sans">
      <body className="min-h-screen bg-paper text-ink antialiased">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}