import "./globals.css"
import { Metadata } from "next"

export const metadata: Metadata = {
  title: "CognitBotz Voice AI Consultant",
  description: "Enterprise AI Knowledge Assistant with Voice",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="bg-dark-bg text-dark-text">
        {children}
      </body>
    </html>
  )
}
